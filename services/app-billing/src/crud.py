from decimal import Decimal

from sqlalchemy import text, update
from sqlalchemy.dialects.postgresql import insert as postgres_upsert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.db import AsyncSessionLocal
from src.models import AccountDB


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
        async with self.session() as session:
            return await session.get(AccountDB, username)

    async def deposit(self, username: str, amount: Decimal) -> AccountDB:
        async with self.session() as session:
            stmt = (
                update(AccountDB)
                .where(AccountDB.username == username)
                .values(balance=AccountDB.balance + amount)
                .returning(AccountDB)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.scalar_one()

    async def withdraw(self, username: str, amount: Decimal) -> AccountDB | None:
        """Atomically withdraw money if balance is sufficient.

        Returns the updated account on success, or None if there were
        insufficient funds (or the account does not exist).
        """
        async with self.session() as session:
            stmt = (
                update(AccountDB)
                .where(AccountDB.username == username, AccountDB.balance >= amount)
                .values(balance=AccountDB.balance - amount)
                .returning(AccountDB)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.scalar_one_or_none()


def get_account_crud() -> AccountCRUD:
    return AccountCRUD(AsyncSessionLocal)
