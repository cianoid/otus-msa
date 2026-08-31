import datetime as dt
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core import metrics
from src.core.logger import log
from src.core.tracing import start_span
from src.db import AsyncSessionLocal
from src.models import OrderDB, OutboxDB, SagaStepDB


class BaseCRUD:
    session: async_sessionmaker[AsyncSession]

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self.session = sessionmaker

    def __call__(self):
        return self

    async def health(self):
        async with self.session() as db:
            stmt = text("SELECT 1")
            result = await db.execute(stmt)
            if result.scalars().one_or_none() is None:
                raise ConnectionError("No connection with PG DB")


class OrderCRUD(BaseCRUD):
    async def create_pending_order(
        self,
        username: str,
        price: Decimal,
        order_id: UUID,
        product_id: int,
        quantity: int,
        slot_id: int,
        idempotency_key: str,
    ) -> OrderDB:
        with start_span(
            "db.order.create_pending_order",
            attributes={
                "order.id": str(order_id),
                "order.username": username,
                "order.price": str(price),
            },
        ):
            async with self.session() as session:
                order = OrderDB(
                    id=order_id,
                    username=username,
                    price=price,
                    status="pending",
                    product_id=product_id,
                    quantity=quantity,
                    slot_id=slot_id,
                    idempotency_key=idempotency_key,
                    saga_state={
                        "product_id": product_id,
                        "quantity": quantity,
                        "slot_id": slot_id,
                    },
                )
                session.add(order)

                steps = [
                    SagaStepDB(
                        order_id=order_id,
                        step_name="warehouse_reserve",
                        status="pending",
                        request_payload={"product_id": product_id, "quantity": quantity},
                    ),
                    SagaStepDB(
                        order_id=order_id,
                        step_name="delivery_reserve",
                        status="pending",
                        request_payload={"slot_id": slot_id},
                    ),
                    SagaStepDB(
                        order_id=order_id,
                        step_name="billing_withdraw",
                        status="pending",
                        request_payload={"amount": str(price)},
                    ),
                ]
                session.add_all(steps)
                await session.commit()
                await session.refresh(order)
                return order

    async def create_order(
        self,
        username: str,
        price: Decimal,
        status: str,
        order_id: UUID | None = None,
        product_id: int | None = None,
        quantity: int | None = None,
        slot_id: int | None = None,
        error: str | None = None,
        idempotency_key: str | None = None,
    ) -> OrderDB:
        with start_span(
            "db.order.create_order",
            attributes={
                "order.username": username,
                "order.price": str(price),
                "order.status": status,
                "order.product_id": product_id,
                "order.quantity": quantity,
                "order.slot_id": slot_id,
            },
        ):
            async with self.session() as session:
                order = OrderDB(
                    username=username,
                    price=price,
                    status=status,
                    product_id=product_id,
                    quantity=quantity,
                    slot_id=slot_id,
                    error=error,
                    idempotency_key=idempotency_key,
                )
                if order_id is not None:
                    order.id = order_id
                session.add(order)
                await session.commit()
                await session.refresh(order)
                return order

    async def finalize_order_with_outbox(
        self,
        order_id: UUID,
        status: str,
        error: str | None,
        entries: list[dict],
    ) -> tuple[OrderDB | None, list[str], bool]:
        """Atomically finalize an order and enqueue outbox entries in one transaction.

        Returns (order, inserted_kinds, finalized). `finalized` is False when the order
        was already finalized by another actor (request handler vs. saga recovery race).
        Duplicate outbox entries are ignored via ON CONFLICT DO NOTHING on (order_id, kind).
        """
        with start_span(
            "db.order.finalize",
            attributes={"order.id": str(order_id), "order.status": status, "outbox.count": len(entries)},
        ):
            async with self.session() as session:
                order = await session.get(OrderDB, order_id, with_for_update=True)
                if order is None:
                    return None, [], False
                if order.status != "pending":
                    log.info("finalize: order %s already %s, skipping", order_id, order.status)
                    return order, [], False

                order.status = status
                if error:
                    order.error = error

                now = dt.datetime.now(dt.UTC)
                inserted_kinds: list[str] = []
                for entry in entries:
                    stmt = (
                        pg_insert(OutboxDB)
                        .values(
                            order_id=order_id,
                            kind=entry["kind"],
                            status="pending",
                            payload=entry["payload"],
                            scheduled_at=entry.get("scheduled_at") or now,
                        )
                        .on_conflict_do_nothing(constraint="uq_outbox_order_kind")
                        .returning(OutboxDB.id)
                    )
                    result = await session.execute(stmt)
                    if result.scalar_one_or_none() is not None:
                        inserted_kinds.append(entry["kind"])

                await session.commit()
                await session.refresh(order)
                for kind in inserted_kinds:
                    metrics.outbox_pending_messages.labels(kind=kind).inc()
                return order, inserted_kinds, True

    async def get_stuck_pending_orders(self, stuck_before: dt.datetime, limit: int) -> list[OrderDB]:
        """Return orders stuck in `pending` since before `stuck_before` (saga crashed mid-flight)."""
        with start_span("db.order.get_stuck_pending", attributes={"order.limit": limit}):
            async with self.session() as session:
                stmt = (
                    select(OrderDB)
                    .where(OrderDB.status == "pending", OrderDB.updated_at < stuck_before)
                    .order_by(OrderDB.updated_at)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
                result = await session.execute(stmt)
                return list(result.scalars().all())

    async def get_by_idempotency_key(self, username: str, idempotency_key: str) -> OrderDB | None:
        with start_span(
            "db.order.get_by_idempotency_key",
            attributes={"order.username": username, "order.idempotency_key": idempotency_key},
        ):
            async with self.session() as session:
                stmt = select(OrderDB).where(
                    OrderDB.username == username,
                    OrderDB.idempotency_key == idempotency_key,
                )
                result = await session.execute(stmt)
                return result.scalars().one_or_none()

    async def get_order(self, order_id: UUID) -> OrderDB | None:
        with start_span("db.order.get_order", attributes={"order.id": str(order_id)}):
            async with self.session() as session:
                return await session.get(OrderDB, order_id)

    async def list_orders(self, username: str) -> list[OrderDB]:
        with start_span("db.order.list_orders", attributes={"order.username": username}):
            async with self.session() as session:
                stmt = select(OrderDB).where(OrderDB.username == username).order_by(OrderDB.created_at.desc())
                result = await session.execute(stmt)
                return list(result.scalars().all())


class SagaStepCRUD(BaseCRUD):
    async def get_steps(self, order_id: UUID) -> list[SagaStepDB]:
        with start_span("db.saga.get_steps", attributes={"order.id": str(order_id)}):
            async with self.session() as session:
                stmt = select(SagaStepDB).where(SagaStepDB.order_id == order_id).order_by(SagaStepDB.created_at)
                result = await session.execute(stmt)
                return list(result.scalars().all())

    async def update_step(
        self,
        step_id: UUID,
        status: str,
        result_payload: dict | None = None,
        error: str | None = None,
        reservation_id: str | None = None,
    ) -> SagaStepDB | None:
        with start_span("db.saga.update_step", attributes={"saga_step.id": str(step_id), "saga_step.status": status}):
            async with self.session() as session:
                step = await session.get(SagaStepDB, step_id)
                if step is None:
                    return None
                step.status = status
                step.attempts += 1
                if result_payload is not None:
                    step.result_payload = result_payload
                if error is not None:
                    step.error = error
                if reservation_id is not None:
                    step.reservation_id = reservation_id
                await session.commit()
                await session.refresh(step)
                return step


class OutboxCRUD(BaseCRUD):
    async def poll_pending(self, now: dt.datetime, limit: int) -> list[OutboxDB]:
        with start_span("db.outbox.poll_pending", attributes={"outbox.limit": limit}):
            async with self.session() as session:
                stmt = (
                    select(OutboxDB)
                    .where(OutboxDB.status == "pending", OutboxDB.scheduled_at <= now)
                    .order_by(OutboxDB.scheduled_at)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
                result = await session.execute(stmt)
                rows = list(result.scalars().all())
                if rows:
                    for row in rows:
                        row.status = "processing"
                    await session.commit()
                return rows

    async def mark_processed(self, outbox_id: UUID) -> None:
        with start_span("db.outbox.mark_processed", attributes={"outbox.id": str(outbox_id)}):
            async with self.session() as session:
                row = await session.get(OutboxDB, outbox_id)
                if row is not None:
                    row.status = "processed"
                    row.attempts += 1
                    row.error = None
                    await session.commit()

    async def mark_failed(
        self,
        outbox_id: UUID,
        error: str,
        attempts: int,
        scheduled_at: dt.datetime | None = None,
    ) -> None:
        with start_span(
            "db.outbox.mark_failed",
            attributes={"outbox.id": str(outbox_id), "outbox.attempts": attempts},
        ):
            async with self.session() as session:
                row = await session.get(OutboxDB, outbox_id)
                if row is not None:
                    row.status = "pending" if scheduled_at is not None else "failed"
                    row.attempts = attempts
                    row.error = error
                    if scheduled_at is not None:
                        row.scheduled_at = scheduled_at
                    await session.commit()


def get_order_crud() -> OrderCRUD:
    return OrderCRUD(AsyncSessionLocal)


def get_saga_step_crud() -> SagaStepCRUD:
    return SagaStepCRUD(AsyncSessionLocal)


def get_outbox_crud() -> OutboxCRUD:
    return OutboxCRUD(AsyncSessionLocal)
