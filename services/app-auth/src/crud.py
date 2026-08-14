from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.core.tracing import start_span
from src.db import AsyncSessionLocal
from src.models import UserDB
from src.schemes import UserCreate
from src.services.auth import hash_password


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


class UserCRUD(BaseCRUD):
    async def create_user(self, user: UserCreate) -> UserDB:
        """Create a new user"""
        with start_span("db.auth.create_user", attributes={"user.username": user.username}):
            db_user = UserDB(
                username=user.username,
                password_hash=hash_password(user.password),
            )

            async with self.session() as db:
                db.add(db_user)
                await db.commit()
                await db.refresh(db_user)
            return db_user

    async def get_user_by_username(self, username: str) -> UserDB | None:
        """Get a specific user by ID"""
        with start_span("db.auth.get_user", attributes={"user.username": username}):
            async with self.session() as db:
                stmt = select(UserDB).where(UserDB.username == username)
                result = await db.execute(stmt)
                return result.scalars().one_or_none()

    async def delete_user(self, username: str) -> bool | None:
        """Delete a specific user by ID"""
        with start_span("db.auth.delete_user", attributes={"user.username": username}):
            db_user = await self.get_user_by_username(username)
            if not db_user:
                return None

            async with self.session() as db:
                await db.delete(db_user)
                await db.commit()
            return True


def get_user_crud() -> UserCRUD:
    return UserCRUD(AsyncSessionLocal)
