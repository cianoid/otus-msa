"""Saga recovery worker: detects and repairs sagas stuck mid-flight.

If app-order crashes (or is killed) after some saga steps were already executed
but before the order was finalized, the order stays in `pending` forever and
already-performed side effects (reserved stock, courier slot, withdrawn money)
are never compensated. This worker periodically picks up such orders and:

1. Resumes unfinished steps (`pending`/`in_progress`) re-calling participants
   with the ORIGINAL idempotency key — downstream idempotency makes the retry
   safe even if the original call actually succeeded.
2. Finalizes the saga atomically (order status + outbox entries in one
   transaction, same as the request handler): compensations for completed
   steps on failure, notification in both cases.

Since the original user JWT is not persisted, the worker mints a short-lived
service token with the same JWT secret (all participants validate JWT locally).
"""

from __future__ import annotations

import asyncio
import datetime as dt
from decimal import Decimal

import httpx

from src.core import metrics
from src.core.config import settings
from src.core.logger import log
from src.core.tracing import start_span
from src.crud import OrderCRUD, SagaStepCRUD
from src.models import OrderDB, SagaStepDB
from src.services.http_client import ServiceClient
from src.services.saga import STEP_ORDER, build_outbox_entries, mint_service_token


class SagaRecoveryWorker:
    def __init__(self, order_crud: OrderCRUD, saga_step_crud: SagaStepCRUD) -> None:
        self.order_crud = order_crud
        self.saga_step_crud = saga_step_crud
        self._stop_event = asyncio.Event()

    async def run(self) -> None:
        log.info("Saga recovery worker started")
        while not self._stop_event.is_set():
            try:
                await self._process_batch()
            except Exception:  # noqa: BLE001
                log.exception("saga recovery: batch processing failed")
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=settings.saga_recovery_poll_interval_seconds,
                )
            except TimeoutError:
                pass
        log.info("Saga recovery worker stopped")

    async def stop(self) -> None:
        self._stop_event.set()

    async def _process_batch(self) -> None:
        stuck_before = dt.datetime.now(dt.UTC) - dt.timedelta(seconds=settings.saga_stuck_threshold_seconds)
        orders = await self.order_crud.get_stuck_pending_orders(stuck_before, limit=settings.saga_recovery_batch_size)
        if not orders:
            return

        log.info("saga recovery: found %d stuck orders", len(orders))
        for order in orders:
            if self._stop_event.is_set():
                return
            try:
                await self._recover_order(order)
            except Exception:  # noqa: BLE001
                metrics.saga_recovery_total.labels(result="error").inc()
                log.exception("saga recovery: failed to recover order %s, will retry next cycle", order.id)

    async def _execute_step(self, client: ServiceClient, order: OrderDB, step: SagaStepDB, token: str) -> dict:
        """Re-execute one saga step with the original idempotency key."""
        payload = step.request_payload
        key = order.idempotency_key
        if step.step_name == "warehouse_reserve":
            return await client.reserve_warehouse(
                str(order.id), payload["product_id"], payload["quantity"], token, idempotency_key=key
            )
        if step.step_name == "delivery_reserve":
            return await client.reserve_delivery(str(order.id), payload["slot_id"], token, idempotency_key=key)
        if step.step_name == "billing_withdraw":
            return await client.withdraw_from_billing(
                order.username, Decimal(payload["amount"]), token, idempotency_key=key
            )
        raise ValueError(f"unknown saga step: {step.step_name}")

    async def _recover_order(self, order: OrderDB) -> None:
        with start_span("saga.recover", attributes={"order.id": str(order.id), "order.username": order.username}):
            token = mint_service_token(order.username)
            error = ""

            steps = await self.saga_step_crud.get_steps(order.id)
            by_name = {step.step_name: step for step in steps}

            async with ServiceClient() as client:
                # Resume unfinished steps in saga order.
                for name in STEP_ORDER:
                    step = by_name.get(name)
                    if step is None or step.status == "completed":
                        continue
                    await self.saga_step_crud.update_step(step.id, status="in_progress")
                    try:
                        result = await self._execute_step(client, order, step, token)
                    except Exception as exc:  # noqa: BLE001
                        error = f"saga recovery: {name} failed for order {order.id}: {exc!s}"
                        log.exception("saga recovery: %s failed for order %s", name, order.id)
                        await self.saga_step_crud.update_step(step.id, status="failed", error=error)
                        break
                    if name == "billing_withdraw" and not result.get("success", False):
                        error = f"saga recovery: billing withdraw returned success=false for order {order.id}"
                        log.error(error)
                        await self.saga_step_crud.update_step(step.id, status="failed", error=error)
                        break
                    await self.saga_step_crud.update_step(
                        step.id,
                        status="completed",
                        result_payload=result,
                        reservation_id=result.get("reservation_id"),
                    )

                # Best-effort email for the notification.
                email: str | None = None
                try:
                    profile = await client.get_user_profile(token, idempotency_key=order.idempotency_key)
                    email = profile.get("email")
                except (httpx.HTTPStatusError, httpx.RequestError):
                    log.exception("saga recovery: failed to fetch user profile for order %s", order.id)

            steps = await self.saga_step_crud.get_steps(order.id)
            success = all(step.status == "completed" for step in steps) and not error

            entries = build_outbox_entries(
                order=order,
                steps=steps,
                success=success,
                email=email,
                token=token,
                error=error,
            )
            finalized_order, _, finalized = await self.order_crud.finalize_order_with_outbox(
                order.id,
                status="paid" if success else "failed",
                error=error or None,
                entries=entries,
            )
            if finalized:
                metrics.saga_recovery_total.labels(result="paid" if success else "failed").inc()
                metrics.orders_total.labels(status="paid" if success else "failed").inc()
                log.info("saga recovery: order %s recovered as %s", order.id, finalized_order.status)
            else:
                log.info("saga recovery: order %s already finalized, skipping", order.id)
