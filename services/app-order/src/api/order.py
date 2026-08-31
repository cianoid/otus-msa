from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, Header, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_409_CONFLICT

from src.core import metrics
from src.core.logger import log
from src.core.tracing import set_span_error, start_span
from src.crud import (
    OrderCRUD,
    SagaStepCRUD,
    get_order_crud,
    get_saga_step_crud,
)
from src.models import SagaStepDB
from src.schemes import Order, OrderCreate
from src.services.http_client import ServiceClient
from src.services.saga import build_outbox_entries
from src.services.verify import VerifyBearer

router = APIRouter(prefix="/api/v1/order", tags=["order"])
security = VerifyBearer()


def _extract_token(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1]
    return ""


@router.get("", response_model=list[Order], status_code=HTTP_200_OK)
async def list_orders(
    payload: dict = Depends(security),
    order_crud: OrderCRUD = Depends(get_order_crud),
):
    orders = await order_crud.list_orders(payload.get("sub", ""))
    return [Order.model_validate(o) for o in orders]


@router.post("", response_model=Order, status_code=HTTP_201_CREATED)
async def create_order(
    request: OrderCreate,
    req: Request,
    idempotency_key: str = Header(...),
    payload: dict = Depends(security),
    order_crud: OrderCRUD = Depends(get_order_crud),
    saga_step_crud: SagaStepCRUD = Depends(get_saga_step_crud),
):
    username = payload.get("sub", "")
    token = _extract_token(req)
    http_client = ServiceClient()

    # Idempotency: replay stored response for an already-processed key.
    existing = await order_crud.get_by_idempotency_key(username, idempotency_key)
    if existing is not None:
        log.info("idempotency: replay for key %s, order %s", idempotency_key, existing.id)
        return JSONResponse(
            status_code=HTTP_201_CREATED if existing.status == "paid" else HTTP_409_CONFLICT,
            content=jsonable_encoder(Order.model_validate(existing)),
        )

    order_id = uuid4()
    success = False
    billing_result: dict = {}
    error = ""
    steps_by_name: dict[str, SagaStepDB] = {}

    try:
        with start_span(
            "saga.create_order",
            attributes={
                "order.id": str(order_id),
                "order.username": username,
                "order.price": str(request.price),
                "order.product_id": request.product_id,
                "order.quantity": request.quantity,
                "order.slot_id": request.slot_id,
            },
        ):
            # Initialize persistent saga state.
            with start_span("saga.init"):
                try:
                    order = await order_crud.create_pending_order(
                        username=username,
                        price=request.price,
                        order_id=order_id,
                        product_id=request.product_id,
                        quantity=request.quantity,
                        slot_id=request.slot_id,
                        idempotency_key=idempotency_key,
                    )
                    metrics.orders_total.labels(status="created").inc()
                except IntegrityError:
                    log.info("idempotency: concurrent duplicate for key %s", idempotency_key)
                    order = await order_crud.get_by_idempotency_key(username, idempotency_key)
                    if order is None:
                        raise
                    return JSONResponse(
                        status_code=HTTP_201_CREATED if order.status == "paid" else HTTP_409_CONFLICT,
                        content=jsonable_encoder(Order.model_validate(order)),
                    )

                saga_steps = await saga_step_crud.get_steps(order_id)
                steps_by_name = {step.step_name: step for step in saga_steps}

            # Helper to execute one saga step with persistent state.
            async def _run_step(name: str, call):
                nonlocal error
                step = steps_by_name.get(name)
                if step is None:
                    raise RuntimeError(f"missing saga step {name}")
                await saga_step_crud.update_step(step.id, status="in_progress")
                try:
                    result = await call()
                    await saga_step_crud.update_step(
                        step.id,
                        status="completed",
                        result_payload=result,
                        reservation_id=result.get("reservation_id"),
                    )
                    return result
                except Exception as exc:
                    msg = f"saga: {name} failed for order {order_id}"
                    log.exception(msg)
                    set_span_error(msg)
                    error = f"{msg}: {exc!s}"
                    await saga_step_crud.update_step(step.id, status="failed", error=error)
                    raise SagaStepFailed(error) from exc

            try:
                # 1. Reserve product in warehouse.
                await _run_step(
                    "warehouse_reserve",
                    lambda: http_client.reserve_warehouse(
                        str(order_id),
                        request.product_id,
                        request.quantity,
                        token,
                        idempotency_key=idempotency_key,
                    ),
                )

                # 2. Reserve courier slot in delivery.
                await _run_step(
                    "delivery_reserve",
                    lambda: http_client.reserve_delivery(
                        str(order_id),
                        request.slot_id,
                        token,
                        idempotency_key=idempotency_key,
                    ),
                )

                # 3. Withdraw money in billing.
                billing_result = await _run_step(
                    "billing_withdraw",
                    lambda: http_client.withdraw_from_billing(
                        username,
                        request.price,
                        token,
                        idempotency_key=idempotency_key,
                    ),
                )
                success = billing_result.get("success", False)
                if not success:
                    msg = f"saga: billing withdraw returned success=false for order {order_id}"
                    log.error(msg)
                    set_span_error(msg)
                    error = msg
                    step = steps_by_name["billing_withdraw"]
                    await saga_step_crud.update_step(step.id, status="failed", error=error)
                    raise SagaStepFailed(error)

            except SagaStepFailed:
                pass

            # Refresh steps after execution.
            saga_steps = await saga_step_crud.get_steps(order_id)

            # Fetch user profile for email (best-effort during request).
            email: str | None = None
            try:
                with start_span("saga.fetch_user_profile"):
                    profile = await http_client.get_user_profile(token, idempotency_key=idempotency_key)
                    email = profile.get("email")
            except (httpx.HTTPStatusError, httpx.RequestError):
                log.exception("saga: failed to fetch user profile for order %s", order_id)

            # Finalize atomically: order status + outbox entries (compensations and
            # notification) are committed in ONE transaction. If the process crashes
            # before this point, the saga recovery worker finalizes the stuck saga.
            outbox_entries = build_outbox_entries(
                order=order,
                steps=saga_steps,
                success=success,
                email=email,
                token=token,
                error=error,
            )
            with start_span("saga.finalize"):
                order, inserted_kinds, finalized = await order_crud.finalize_order_with_outbox(
                    order_id,
                    status="paid" if success else "failed",
                    error=error or None,
                    entries=outbox_entries,
                )
                if finalized:
                    metrics.orders_total.labels(status="paid" if success else "failed").inc()
                    for kind in inserted_kinds:
                        if kind.startswith("compensation_"):
                            metrics.order_compensations_total.labels(kind=kind).inc()
                else:
                    log.warning("saga: order %s was already finalized (recovery race)", order_id)

    finally:
        await http_client.close()

    order = await order_crud.get_order(order_id)
    return JSONResponse(
        status_code=HTTP_201_CREATED if success else HTTP_409_CONFLICT,
        content=jsonable_encoder(Order.model_validate(order)),
    )


class SagaStepFailed(Exception):
    """Raised when a saga step fails after retries; triggers compensations."""
