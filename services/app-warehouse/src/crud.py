import uuid

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.db import AsyncSessionLocal
from src.models import RESERVATION_STATUS_ACTIVE, RESERVATION_STATUS_CANCELLED, ProductDB, ReservationDB


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


class WarehouseCRUD(BaseCRUD):
    async def list_products(self) -> list[ProductDB]:
        async with self.session() as session:
            stmt = select(ProductDB).order_by(ProductDB.id)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def create_product(self, name: str, stock: int) -> ProductDB:
        async with self.session() as session:
            product = ProductDB(name=name, stock=stock)
            session.add(product)
            await session.commit()
            await session.refresh(product)
            return product

    async def get_product(self, product_id: int) -> ProductDB | None:
        async with self.session() as session:
            return await session.get(ProductDB, product_id)

    async def reserve(self, order_id: str, product_id: int, quantity: int) -> tuple[ReservationDB | None, int]:
        """Atomically reserve `quantity` items of a product.

        Returns (reservation, remaining stock) on success, or (None, current
        stock) if the product does not exist or stock is insufficient.
        """
        async with self.session() as session:
            stmt = (
                update(ProductDB)
                .where(ProductDB.id == product_id, ProductDB.stock >= quantity)
                .values(stock=ProductDB.stock - quantity)
                .returning(ProductDB)
            )
            result = await session.execute(stmt)
            product = result.scalar_one_or_none()

            if product is None:
                existing = await session.get(ProductDB, product_id)
                await session.commit()
                return None, existing.stock if existing is not None else 0

            reservation = ReservationDB(
                id=str(uuid.uuid4()),
                order_id=order_id,
                product_id=product_id,
                quantity=quantity,
                status=RESERVATION_STATUS_ACTIVE,
            )
            session.add(reservation)
            await session.commit()
            return reservation, product.stock

    async def cancel(self, reservation_id: str) -> bool:
        """Compensate a reservation: return quantity to stock and mark it cancelled.

        Idempotent: cancelling an already-cancelled reservation is a no-op
        that still reports success.
        """
        async with self.session() as session:
            stmt = (
                update(ReservationDB)
                .where(ReservationDB.id == reservation_id, ReservationDB.status == RESERVATION_STATUS_ACTIVE)
                .values(status=RESERVATION_STATUS_CANCELLED)
                .returning(ReservationDB)
            )
            result = await session.execute(stmt)
            reservation = result.scalar_one_or_none()

            if reservation is None:
                # Either already cancelled (idempotent success) or unknown id.
                existing = await session.get(ReservationDB, reservation_id)
                await session.commit()
                return existing is not None

            await session.execute(
                update(ProductDB)
                .where(ProductDB.id == reservation.product_id)
                .values(stock=ProductDB.stock + reservation.quantity)
            )
            await session.commit()
            return True


def get_warehouse_crud() -> WarehouseCRUD:
    return WarehouseCRUD(AsyncSessionLocal)
