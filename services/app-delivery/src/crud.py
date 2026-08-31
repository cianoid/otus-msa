from uuid import uuid4

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert as postgres_upsert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.tracing import start_span
from src.db import AsyncSessionLocal
from src.models import CourierReservationDB, IdempotencyKeyDB, SlotDB

RESERVATION_STATUS_ACTIVE = "active"
RESERVATION_STATUS_CANCELLED = "cancelled"


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


class DeliveryCRUD(BaseCRUD):
    async def get_slots(self) -> list[SlotDB]:
        with start_span("db.delivery.list_slots"):
            async with self.session() as session:
                stmt = select(SlotDB).order_by(SlotDB.id)
                result = await session.execute(stmt)
                return list(result.scalars().all())

    async def create_slot(self, time_slot: str, capacity: int) -> SlotDB:
        with start_span("db.delivery.create_slot", attributes={"slot.time_slot": time_slot, "slot.capacity": capacity}):
            async with self.session() as session:
                slot = SlotDB(time_slot=time_slot, capacity=capacity, reserved=0)
                session.add(slot)
                await session.commit()
                await session.refresh(slot)
                return slot

    async def _reserve_in_session(
        self, session: AsyncSession, order_id: str, slot_id: int
    ) -> CourierReservationDB | None:
        """Core reservation logic executed inside an existing session/transaction."""
        stmt = (
            update(SlotDB)
            .where(SlotDB.id == slot_id, SlotDB.reserved < SlotDB.capacity)
            .values(reserved=SlotDB.reserved + 1)
            .returning(SlotDB)
        )
        result = await session.execute(stmt)
        slot = result.scalar_one_or_none()
        if slot is None:
            return None

        reservation = CourierReservationDB(
            id=str(uuid4()),
            order_id=order_id,
            slot_id=slot.id,
            status=RESERVATION_STATUS_ACTIVE,
        )
        session.add(reservation)
        await session.flush()
        return reservation

    async def reserve(self, order_id: str, slot_id: int) -> CourierReservationDB | None:
        """Atomically reserve a courier on the slot if it has free capacity.

        Returns the created reservation on success, or None if the slot
        does not exist or is fully booked.
        """
        with start_span(
            "db.delivery.reserve",
            attributes={"order.id": order_id, "slot.id": slot_id},
        ):
            async with self.session() as session:
                reservation = await self._reserve_in_session(session, order_id, slot_id)
                await session.commit()
                await session.refresh(reservation) if reservation is not None else None
                return reservation

    async def idempotent_reserve(
        self,
        idempotency_key: str | None,
        order_id: str,
        slot_id: int,
    ) -> dict:
        """Reserve with idempotency: same key/kind always returns the stored result."""
        if not idempotency_key:
            reservation = await self.reserve(order_id, slot_id)
            return {"success": reservation is not None, "reservation_id": reservation.id if reservation else None}

        with start_span(
            "db.delivery.idempotent_reserve",
            attributes={"order.id": order_id, "slot.id": slot_id, "idempotency_key": idempotency_key},
        ):
            async with self.session() as session:
                insert_stmt = (
                    postgres_upsert(IdempotencyKeyDB)
                    .values(idempotency_key=idempotency_key, kind="reserve", payload={})
                    .on_conflict_do_nothing(index_elements=[IdempotencyKeyDB.idempotency_key, IdempotencyKeyDB.kind])
                    .returning(IdempotencyKeyDB)
                )
                result = await session.execute(insert_stmt)
                row = result.scalar_one_or_none()

                if row is None:
                    existing = await session.execute(
                        select(IdempotencyKeyDB).where(
                            IdempotencyKeyDB.idempotency_key == idempotency_key,
                            IdempotencyKeyDB.kind == "reserve",
                        )
                    )
                    await session.commit()
                    return existing.scalar_one().payload

                reservation = await self._reserve_in_session(session, order_id, slot_id)
                payload = {
                    "success": reservation is not None,
                    "reservation_id": reservation.id if reservation else None,
                }
                row.payload = payload
                await session.commit()
                return payload

    async def _cancel_in_session(self, session: AsyncSession, reservation_id: str) -> bool:
        """Core cancel logic executed inside an existing session/transaction."""
        reservation = await session.get(CourierReservationDB, reservation_id)
        if reservation is None:
            return False

        if reservation.status == RESERVATION_STATUS_CANCELLED:
            return True

        stmt = (
            update(SlotDB)
            .where(SlotDB.id == reservation.slot_id, SlotDB.reserved > 0)
            .values(reserved=SlotDB.reserved - 1)
        )
        await session.execute(stmt)
        reservation.status = RESERVATION_STATUS_CANCELLED
        return True

    async def cancel(self, reservation_id: str) -> bool:
        """Compensating transaction: cancel a reservation and free the slot.

        Idempotent: cancelling an already cancelled reservation succeeds.
        Returns False only if the reservation does not exist.
        """
        with start_span("db.delivery.cancel", attributes={"reservation.id": reservation_id}):
            async with self.session() as session:
                success = await self._cancel_in_session(session, reservation_id)
                await session.commit()
                return success

    async def idempotent_cancel(self, idempotency_key: str | None, reservation_id: str) -> dict:
        """Cancel with idempotency: same key/kind always returns the stored result."""
        if not idempotency_key:
            success = await self.cancel(reservation_id)
            return {"success": success}

        with start_span(
            "db.delivery.idempotent_cancel",
            attributes={"reservation.id": reservation_id, "idempotency_key": idempotency_key},
        ):
            async with self.session() as session:
                insert_stmt = (
                    postgres_upsert(IdempotencyKeyDB)
                    .values(idempotency_key=idempotency_key, kind="cancel", payload={})
                    .on_conflict_do_nothing(index_elements=[IdempotencyKeyDB.idempotency_key, IdempotencyKeyDB.kind])
                    .returning(IdempotencyKeyDB)
                )
                result = await session.execute(insert_stmt)
                row = result.scalar_one_or_none()

                if row is None:
                    existing = await session.execute(
                        select(IdempotencyKeyDB).where(
                            IdempotencyKeyDB.idempotency_key == idempotency_key,
                            IdempotencyKeyDB.kind == "cancel",
                        )
                    )
                    await session.commit()
                    return existing.scalar_one().payload

                success = await self._cancel_in_session(session, reservation_id)
                payload = {"success": success}
                row.payload = payload
                await session.commit()
                return payload


def get_delivery_crud() -> DeliveryCRUD:
    return DeliveryCRUD(AsyncSessionLocal)
