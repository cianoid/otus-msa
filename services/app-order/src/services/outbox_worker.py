"""Background outbox worker: guaranteed delivery of compensations and notifications."""

from __future__ import annotations

import asyncio
import datetime as dt
import traceback
from decimal import Decimal

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from src.core import metrics
from src.core.config import settings
from src.core.logger import log
from src.core.tracing import start_span
from src.crud import OutboxCRUD
from src.kafka import KafkaClient
from src.models import OutboxDB
from src.services.http_client import ServiceClient
from src.services.saga import mint_service_token


class OutboxWorker:
    def __init__(self, outbox_crud: OutboxCRUD, kafka: KafkaClient) -> None:
        self.outbox_crud = outbox_crud
        self.kafka = kafka
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def run(self) -> None:
        log.info("Outbox worker started")
        while not self._stop_event.is_set():
            try:
                await self._process_batch()
            except Exception:  # noqa: BLE001
                log.exception("outbox worker: batch processing failed")
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=settings.outbox_poll_interval_seconds,
                )
            except TimeoutError:
                pass
        log.info("Outbox worker stopped")

    async def stop(self) -> None:
        self._stop_event.set()

    async def _process_batch(self) -> None:
        now = dt.datetime.now(dt.UTC)
        rows = await self.outbox_crud.poll_pending(now, limit=settings.outbox_batch_size)
        if not rows:
            return

        log.info("outbox worker: processing %d entries", len(rows))
        for row in rows:
            if self._stop_event.is_set():
                return
            await self._process_entry(row)

    async def _process_entry(self, row: OutboxDB) -> None:
        with start_span("outbox.process", attributes={"outbox.id": str(row.id), "outbox.kind": row.kind}):
            try:
                if row.kind.startswith("compensation_"):
                    await self._process_compensation(row)
                elif row.kind == "notification":
                    await self._process_notification(row)
                else:
                    raise ValueError(f"unknown outbox kind: {row.kind}")
                await self.outbox_crud.mark_processed(row.id)
                metrics.outbox_messages_total.labels(kind=row.kind, status="processed").inc()
                metrics.outbox_pending_messages.labels(kind=row.kind).dec()
                log.info("outbox worker: %s %s processed", row.kind, row.id)
            except Exception as exc:  # noqa: BLE001
                error = f"{exc!s}\n{traceback.format_exc()}"
                attempts = row.attempts + 1
                metrics.outbox_messages_total.labels(kind=row.kind, status="failed").inc()
                if attempts < settings.outbox_max_attempts:
                    scheduled_at = self._next_retry_time(attempts)
                    await self.outbox_crud.mark_failed(row.id, error, attempts=attempts, scheduled_at=scheduled_at)
                    log.warning(
                        "outbox worker: %s %s failed (attempt %d/%d), retry at %s",
                        row.kind,
                        row.id,
                        attempts,
                        settings.outbox_max_attempts,
                        scheduled_at,
                    )
                else:
                    await self.outbox_crud.mark_failed(row.id, error, attempts=attempts)
                    metrics.outbox_dlq_messages_total.labels(kind=row.kind).inc()
                    metrics.outbox_pending_messages.labels(kind=row.kind).dec()
                    log.error(
                        "outbox worker: %s %s exhausted all %d attempts",
                        row.kind,
                        row.id,
                        settings.outbox_max_attempts,
                    )

    @retry(
        wait=wait_exponential_jitter(
            initial=settings.outbox_retry_min_seconds,
            max=settings.outbox_retry_max_seconds,
        ),
        stop=stop_after_attempt(settings.saga_retry_max_attempts),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _process_compensation(self, row: OutboxDB) -> None:
        payload = row.payload
        idempotency_key = payload.get("idempotency_key")

        # Mint a fresh service token per attempt: the user JWT captured at saga
        # finalization expires (access TTL is minutes) long before the outbox
        # retry budget runs out. Fall back to the stored token for legacy rows
        # that have no username in the payload.
        username = payload.get("username")
        token = mint_service_token(username) if username else payload["token"]

        async with ServiceClient() as client:
            if row.kind == "compensation_delivery":
                await client.cancel_delivery_reservation(
                    payload["reservation_id"], token, idempotency_key=idempotency_key
                )
            elif row.kind == "compensation_warehouse":
                await client.cancel_warehouse_reservation(
                    payload["reservation_id"], token, idempotency_key=idempotency_key
                )
            elif row.kind == "compensation_billing":
                await client.refund_billing(
                    payload["username"],
                    Decimal(payload["amount"]),
                    token,
                    idempotency_key=idempotency_key,
                )

    async def _process_notification(self, row: OutboxDB) -> None:
        payload = row.payload
        await self.kafka.send_notification(
            notification_id=payload["notification_id"],
            message_type=payload["message_type"],
            username=payload["username"],
            email=payload.get("email"),
            data=payload["data"],
        )

    @staticmethod
    def _next_retry_time(attempts: int) -> dt.datetime:
        delay = min(
            settings.outbox_retry_min_seconds * (2 ** (attempts - 1)),
            settings.outbox_retry_max_seconds,
        )
        return dt.datetime.now(dt.UTC) + dt.timedelta(seconds=delay)
