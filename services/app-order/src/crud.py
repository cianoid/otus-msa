from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.core.tracing import start_span
from src.db import AsyncSessionLocal
from src.models import OrderDB


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


def get_order_crud() -> OrderCRUD:
    return OrderCRUD(AsyncSessionLocal)
