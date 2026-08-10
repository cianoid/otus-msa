from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from src.core.logger import log
from src.crud import OrderCRUD, get_order_crud
from src.kafka import KafkaClient, get_kafka
from src.schemes import Order, OrderCreate
from src.services.http_client import ServiceClient
from src.services.verify import VerifyBearer
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

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
    return [Order(**o.__dict__) for o in orders]


@router.post("", response_model=Order, status_code=HTTP_201_CREATED)
async def create_order(
    request: OrderCreate,
    req: Request,
    kafka: KafkaClient = Depends(get_kafka),
    payload: dict = Depends(security),
    order_crud: OrderCRUD = Depends(get_order_crud),
):
    username = payload.get("sub", "")
    token = _extract_token(req)
    http_client = ServiceClient()

    order_id = uuid4()
    success = False
    billing_result: dict = {}
    warehouse_reservation_id: str | None = None
    delivery_reservation_id: str | None = None

    try:
        # Saga: warehouse reserve -> delivery reserve -> billing withdraw.
        # Any failure (business or network/HTTP) rolls back previous steps.

        # 1. Reserve product in warehouse.
        try:
            warehouse_result = await http_client.reserve_warehouse(
                str(order_id), request.product_id, request.quantity, token
            )
            if warehouse_result.get("success"):
                warehouse_reservation_id = warehouse_result.get("reservation_id")
            else:
                log.info("saga: warehouse reserve failed for order %s", order_id)
        except Exception:
            log.exception("saga: warehouse reserve error for order %s", order_id)

        # 2. Reserve courier slot in delivery.
        if warehouse_reservation_id:
            try:
                delivery_result = await http_client.reserve_delivery(str(order_id), request.slot_id, token)
                if delivery_result.get("success"):
                    delivery_reservation_id = delivery_result.get("reservation_id")
                else:
                    log.info("saga: delivery reserve failed for order %s", order_id)
            except Exception:
                log.exception("saga: delivery reserve error for order %s", order_id)

        # 3. Withdraw money in billing.
        if delivery_reservation_id:
            try:
                billing_result = await http_client.withdraw_from_billing(username, request.price, token)
                success = billing_result.get("success", False)
                if not success:
                    log.info("saga: billing withdraw failed for order %s", order_id)
            except Exception:
                log.exception("saga: billing withdraw error for order %s", order_id)

        # Compensations (best-effort, in reverse order).
        if not success:
            if delivery_reservation_id:
                try:
                    await http_client.cancel_delivery_reservation(delivery_reservation_id, token)
                except Exception:
                    log.exception("saga: delivery compensation failed for order %s", order_id)
            if warehouse_reservation_id:
                try:
                    await http_client.cancel_warehouse_reservation(warehouse_reservation_id, token)
                except Exception:
                    log.exception("saga: warehouse compensation failed for order %s", order_id)

        # Persist order.
        status = "paid" if success else "failed"
        order = await order_crud.create_order(
            username,
            request.price,
            status,
            order_id=order_id,
            product_id=request.product_id,
            quantity=request.quantity,
            slot_id=request.slot_id,
        )

        # Fetch user profile for email.
        profile = await http_client.get_user_profile(token)
        email = profile.get("email")

        # Send notification event.
        message_type = "ORDER_SUCCESS" if success else "ORDER_FAILED"
        await kafka.send_notification(
            notification_id=str(order.id),
            message_type=message_type,
            username=username,
            email=email,
            data={
                "order_id": str(order.id),
                "price": str(request.price),
                "balance": str(billing_result.get("balance", "0.00")),
            },
        )
    finally:
        await http_client.close()

    return Order(**order.__dict__)
