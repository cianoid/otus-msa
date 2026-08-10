from uuid import uuid4

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.db import AsyncSessionLocal
from src.models import CourierReservationDB, SlotDB

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
        async with self.session() as session:
            stmt = select(SlotDB).order_by(SlotDB.id)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def create_slot(self, time_slot: str, capacity: int) -> SlotDB:
        async with self.session() as session:
            slot = SlotDB(time_slot=time_slot, capacity=capacity, reserved=0)
            session.add(slot)
            await session.commit()
            await session.refresh(slot)
            return slot

    async def reserve(self, order_id: str, slot_id: int) -> CourierReservationDB | None:
        """Atomically reserve a courier on the slot if it has free capacity.

        Returns the created reservation on success, or None if the slot
        does not exist or is fully booked.
        """
        async with self.session() as session:
            stmt = (
                update(SlotDB)
                .where(SlotDB.id == slot_id, SlotDB.reserved < SlotDB.capacity)
                .values(reserved=SlotDB.reserved + 1)
                .returning(SlotDB)
            )
            result = await session.execute(stmt)
            slot = result.scalar_one_or_none()
            if slot is None:
                await session.rollback()
                return None

            reservation = CourierReservationDB(
                id=str(uuid4()),
                order_id=order_id,
                slot_id=slot.id,
                status=RESERVATION_STATUS_ACTIVE,
            )
            session.add(reservation)
            await session.commit()
            await session.refresh(reservation)
            return reservation

    async def cancel(self, reservation_id: str) -> bool:
        """Compensating transaction: cancel a reservation and free the slot.

        Idempotent: cancelling an already cancelled reservation succeeds.
        Returns False only if the reservation does not exist.
        """
        async with self.session() as session:
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
            await session.commit()
            return True


def get_delivery_crud() -> DeliveryCRUD:
    return DeliveryCRUD(AsyncSessionLocal)
