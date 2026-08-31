from decimal import Decimal

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert as postgres_upsert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.tracing import start_span
from src.db import AsyncSessionLocal
from src.models import AccountDB, IdempotencyKeyDB


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


class AccountCRUD(BaseCRUD):
    async def create_account(self, username: str) -> AccountDB:
        """Idempotently create a billing account with zero balance."""
        with start_span("db.billing.create_account", attributes={"billing.username": username}):
            async with self.session() as session:
                stmt = (
                    postgres_upsert(AccountDB)
                    .values(username=username, balance=Decimal("0.00"))
                    .on_conflict_do_nothing(index_elements=[AccountDB.username])
                    .returning(AccountDB)
                )
                result = await session.execute(stmt)
                account = result.scalar_one_or_none()

                if account is None:
                    account = await session.get(AccountDB, username)

                if account is None:
                    raise RuntimeError(f"Failed to create or load billing account for {username}")

                await session.commit()
                return account

    async def get_account(self, username: str) -> AccountDB | None:
        with start_span("db.billing.get_account", attributes={"billing.username": username}):
            async with self.session() as session:
                return await session.get(AccountDB, username)

    async def _deposit_in_session(self, session: AsyncSession, username: str, amount: Decimal) -> AccountDB:
        """Core deposit logic executed inside an existing session/transaction."""
        stmt = (
            update(AccountDB)
            .where(AccountDB.username == username)
            .values(balance=AccountDB.balance + amount)
            .returning(AccountDB)
        )
        result = await session.execute(stmt)
        return result.scalar_one()

    async def deposit(self, username: str, amount: Decimal) -> AccountDB:
        with start_span("db.billing.deposit", attributes={"billing.username": username, "billing.amount": str(amount)}):
            async with self.session() as session:
                account = await self._deposit_in_session(session, username, amount)
                await session.commit()
                return account

    async def idempotent_deposit(
        self,
        idempotency_key: str | None,
        username: str,
        amount: Decimal,
    ) -> dict:
        """Deposit with idempotency: same key/kind always returns the stored result."""
        if not idempotency_key:
            account = await self.deposit(username, amount)
            return {"username": account.username, "balance": account.balance}

        with start_span(
            "db.billing.idempotent_deposit",
            attributes={
                "billing.username": username,
                "billing.amount": str(amount),
                "idempotency_key": idempotency_key,
            },
        ):
            async with self.session() as session:
                insert_stmt = (
                    postgres_upsert(IdempotencyKeyDB)
                    .values(idempotency_key=idempotency_key, kind="deposit", payload={})
                    .on_conflict_do_nothing(index_elements=[IdempotencyKeyDB.idempotency_key, IdempotencyKeyDB.kind])
                    .returning(IdempotencyKeyDB)
                )
                result = await session.execute(insert_stmt)
                row = result.scalar_one_or_none()

                if row is None:
                    existing = await session.execute(
                        select(IdempotencyKeyDB).where(
                            IdempotencyKeyDB.idempotency_key == idempotency_key,
                            IdempotencyKeyDB.kind == "deposit",
                        )
                    )
                    await session.commit()
                    return existing.scalar_one().payload

                account = await self._deposit_in_session(session, username, amount)
                payload = {"username": account.username, "balance": account.balance}
                row.payload = payload
                await session.commit()
                return payload

    async def _withdraw_in_session(self, session: AsyncSession, username: str, amount: Decimal) -> AccountDB | None:
        """Core withdraw logic executed inside an existing session/transaction."""
        stmt = (
            update(AccountDB)
            .where(AccountDB.username == username, AccountDB.balance >= amount)
            .values(balance=AccountDB.balance - amount)
            .returning(AccountDB)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def withdraw(self, username: str, amount: Decimal) -> AccountDB | None:
        """Atomically withdraw money if balance is sufficient.

        Returns the updated account on success, or None if there were
        insufficient funds (or the account does not exist).
        """
        with start_span(
            "db.billing.withdraw", attributes={"billing.username": username, "billing.amount": str(amount)}
        ):
            async with self.session() as session:
                account = await self._withdraw_in_session(session, username, amount)
                await session.commit()
                return account

    async def idempotent_withdraw(
        self,
        idempotency_key: str | None,
        username: str,
        amount: Decimal,
    ) -> dict:
        """Withdraw with idempotency: same key/kind always returns the stored result."""
        if not idempotency_key:
            account = await self.withdraw(username, amount)
            if account is None:
                existing = await self.get_account(username)
                if existing is None:
                    return {"error": "account_not_found"}
                return {"success": False, "balance": existing.balance}
            return {"success": True, "balance": account.balance}

        with start_span(
            "db.billing.idempotent_withdraw",
            attributes={
                "billing.username": username,
                "billing.amount": str(amount),
                "idempotency_key": idempotency_key,
            },
        ):
            async with self.session() as session:
                insert_stmt = (
                    postgres_upsert(IdempotencyKeyDB)
                    .values(idempotency_key=idempotency_key, kind="withdraw", payload={})
                    .on_conflict_do_nothing(index_elements=[IdempotencyKeyDB.idempotency_key, IdempotencyKeyDB.kind])
                    .returning(IdempotencyKeyDB)
                )
                result = await session.execute(insert_stmt)
                row = result.scalar_one_or_none()

                if row is None:
                    existing = await session.execute(
                        select(IdempotencyKeyDB).where(
                            IdempotencyKeyDB.idempotency_key == idempotency_key,
                            IdempotencyKeyDB.kind == "withdraw",
                        )
                    )
                    await session.commit()
                    return existing.scalar_one().payload

                account = await self._withdraw_in_session(session, username, amount)
                if account is None:
                    existing = await session.get(AccountDB, username)
                    if existing is None:
                        payload = {"error": "account_not_found"}
                    else:
                        payload = {"success": False, "balance": existing.balance}
                else:
                    payload = {"success": True, "balance": account.balance}

                row.payload = payload
                await session.commit()
                return payload


def get_account_crud() -> AccountCRUD:
    return AccountCRUD(AsyncSessionLocal)
