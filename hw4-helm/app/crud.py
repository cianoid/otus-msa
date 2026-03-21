import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import UserDB
from app.schemes import UserCreate, UserUpdate


class UserCRUD:
    session: async_sessionmaker[AsyncSession]

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self.session = sessionmaker

    def __call__(self):  # noqa: D102
        return self


    async def create_user(self, user: UserCreate) -> UserDB:
        """Create a new user"""
        user_id = str(uuid.uuid4())
        db_user = UserDB(id=user_id, **user.model_dump())

        async with self.session() as db:
            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)
        return db_user

    async def read_user(self, user_id: str) -> UserDB | None:
        """Get a specific user by ID"""
        async with self.session() as db:
            db_user = await db.get(UserDB, user_id)
        return db_user

    async def read_users(self, skip: int, limit: int) -> list[UserDB]:
        """Get a list of users with pagination"""
        stmt = select(UserDB).offset(skip).limit(limit)

        async with self.session() as db:
            users = await db.execute(stmt)
        return users.scalars().all()

    async def update_user(self, user_id: str, user_update: UserUpdate):
        """Update a specific user by ID"""
        db_user = await self.read_user(user_id)
        if not db_user:
            return None

        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)

        async with self.session() as db:
            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)
        return db_user

    async def delete_user(self, user_id: str) -> bool | None:
        """Delete a specific user by ID"""
        db_user = await self.read_user(user_id)
        if not db_user:
            return None

        async with self.session() as db:
            await db.delete(db_user)
            await db.commit()
        return True

def get_user_crud():
    raise NotImplementedError
