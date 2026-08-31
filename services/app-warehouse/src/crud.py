import uuid

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert as postgres_upsert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.cache import CacheClient
from src.core.tracing import start_span
from src.db import AsyncSessionLocal
from src.models import (
    RESERVATION_STATUS_ACTIVE,
    RESERVATION_STATUS_CANCELLED,
    IdempotencyKeyDB,
    ProductDB,
    ReservationDB,
)


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
    PRODUCTS_LIST_CACHE_KEY = "warehouse:products:list"

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession], cache: CacheClient | None = None) -> None:
        super().__init__(sessionmaker)
        self.cache = cache

    @staticmethod
    def _product_cache_key(product_id: int) -> str:
        return f"warehouse:product:{product_id}"

    @staticmethod
    def _product_to_dict(product: ProductDB) -> dict:
        return {"id": product.id, "name": product.name, "stock": product.stock}

    async def _invalidate_product(self, product_id: int | None = None) -> None:
        if self.cache is None:
            return
        keys = [self.PRODUCTS_LIST_CACHE_KEY]
        if product_id is not None:
            keys.append(self._product_cache_key(product_id))
        await self.cache.delete(*keys)

    async def list_products(self) -> list[ProductDB]:
        if self.cache is not None:
            cached = await self.cache.get_json(self.PRODUCTS_LIST_CACHE_KEY)
            if cached is not None:
                return [ProductDB(**item) for item in cached]

        with start_span("db.warehouse.list_products"):
            async with self.session() as session:
                stmt = select(ProductDB).order_by(ProductDB.id)
                result = await session.execute(stmt)
                products = list(result.scalars().all())

        if self.cache is not None:
            await self.cache.set_json(self.PRODUCTS_LIST_CACHE_KEY, [self._product_to_dict(p) for p in products])
        return products

    async def create_product(self, name: str, stock: int) -> ProductDB:
        with start_span("db.warehouse.create_product", attributes={"product.name": name, "product.stock": stock}):
            async with self.session() as session:
                product = ProductDB(name=name, stock=stock)
                session.add(product)
                await session.commit()
                await session.refresh(product)

        await self._invalidate_product()
        return product

    async def get_product(self, product_id: int) -> ProductDB | None:
        cache_key = self._product_cache_key(product_id)
        if self.cache is not None:
            cached = await self.cache.get_json(cache_key)
            if cached is not None:
                return ProductDB(**cached)

        with start_span("db.warehouse.get_product", attributes={"product.id": product_id}):
            async with self.session() as session:
                product = await session.get(ProductDB, product_id)

        if self.cache is not None and product is not None:
            await self.cache.set_json(cache_key, self._product_to_dict(product))
        return product

    async def _reserve_in_session(
        self, session: AsyncSession, order_id: str, product_id: int, quantity: int
    ) -> tuple[ReservationDB | None, int]:
        """Core reservation logic executed inside an existing session/transaction."""
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
            return None, existing.stock if existing is not None else 0

        reservation = ReservationDB(
            id=str(uuid.uuid4()),
            order_id=order_id,
            product_id=product_id,
            quantity=quantity,
            status=RESERVATION_STATUS_ACTIVE,
        )
        session.add(reservation)
        await session.flush()
        return reservation, product.stock

    async def reserve(self, order_id: str, product_id: int, quantity: int) -> tuple[ReservationDB | None, int]:
        """Atomically reserve `quantity` items of a product.

        Returns (reservation, remaining stock) on success, or (None, current
        stock) if the product does not exist or stock is insufficient.
        """
        with start_span(
            "db.warehouse.reserve",
            attributes={"order.id": order_id, "product.id": product_id, "quantity": quantity},
        ):
            async with self.session() as session:
                reservation, stock = await self._reserve_in_session(session, order_id, product_id, quantity)
                await session.commit()

        if reservation is not None:
            await self._invalidate_product(product_id)
        return reservation, stock

    async def idempotent_reserve(
        self,
        idempotency_key: str | None,
        order_id: str,
        product_id: int,
        quantity: int,
    ) -> dict:
        """Reserve with idempotency: same key/kind always returns the stored result."""
        if not idempotency_key:
            reservation, stock = await self.reserve(order_id, product_id, quantity)
            return {
                "success": reservation is not None,
                "reservation_id": reservation.id if reservation is not None else None,
                "stock": stock,
            }

        with start_span(
            "db.warehouse.idempotent_reserve",
            attributes={"order.id": order_id, "product.id": product_id, "idempotency_key": idempotency_key},
        ):
            async with self.session() as session:
                # Atomically claim the idempotency slot.
                insert_stmt = (
                    postgres_upsert(IdempotencyKeyDB)
                    .values(idempotency_key=idempotency_key, kind="reserve", payload={})
                    .on_conflict_do_nothing(index_elements=[IdempotencyKeyDB.idempotency_key, IdempotencyKeyDB.kind])
                    .returning(IdempotencyKeyDB)
                )
                result = await session.execute(insert_stmt)
                row = result.scalar_one_or_none()

                if row is None:
                    # Already processed: return stored payload.
                    existing = await session.execute(
                        select(IdempotencyKeyDB).where(
                            IdempotencyKeyDB.idempotency_key == idempotency_key,
                            IdempotencyKeyDB.kind == "reserve",
                        )
                    )
                    await session.commit()
                    return existing.scalar_one().payload

                # First time: execute the reservation inside the same transaction.
                reservation, stock = await self._reserve_in_session(session, order_id, product_id, quantity)
                payload = {
                    "success": reservation is not None,
                    "reservation_id": reservation.id if reservation is not None else None,
                    "stock": stock,
                }
                row.payload = payload
                await session.commit()

        if reservation is not None:
            await self._invalidate_product(product_id)
        return payload

    async def _cancel_in_session(self, session: AsyncSession, reservation_id: str) -> tuple[bool, int | None]:
        """Core cancel logic executed inside an existing session/transaction.

        Returns (success, product_id); product_id is None when the reservation is unknown."""
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
            return existing is not None, existing.product_id if existing is not None else None

        await session.execute(
            update(ProductDB)
            .where(ProductDB.id == reservation.product_id)
            .values(stock=ProductDB.stock + reservation.quantity)
        )
        return True, reservation.product_id

    async def cancel(self, reservation_id: str) -> bool:
        """Compensate a reservation: return quantity to stock and mark it cancelled.

        Idempotent: cancelling an already-cancelled reservation is a no-op
        that still reports success.
        """
        with start_span("db.warehouse.cancel", attributes={"reservation.id": reservation_id}):
            async with self.session() as session:
                success, product_id = await self._cancel_in_session(session, reservation_id)
                await session.commit()

        if success:
            await self._invalidate_product(product_id)
        return success

    async def idempotent_cancel(self, idempotency_key: str | None, reservation_id: str) -> dict:
        """Cancel with idempotency: same key/kind always returns the stored result."""
        if not idempotency_key:
            success = await self.cancel(reservation_id)
            return {"success": success}

        with start_span(
            "db.warehouse.idempotent_cancel",
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

                success, product_id = await self._cancel_in_session(session, reservation_id)
                payload = {"success": success}
                row.payload = payload
                await session.commit()

        if success:
            await self._invalidate_product(product_id)
        return payload


def get_warehouse_crud() -> WarehouseCRUD:
    return WarehouseCRUD(AsyncSessionLocal)
