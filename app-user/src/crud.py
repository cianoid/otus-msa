from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from schemes import UserUpdate
from src.db import AsyncSessionLocal
from src.models import UserDB
from src.schemes import User


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
    async def get_or_update_user(self, session: AsyncSession, username: str, user_update: UserUpdate | None = None) -> UserDB:
        user_db = UserDB(username=username)

        if user_update:
            update_data = user_update.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(user_db, field, value)

        await session.merge(user_db)
        await session.commit()
        return user_db

def get_user_crud() -> UserCRUD:
    return UserCRUD(AsyncSessionLocal)
