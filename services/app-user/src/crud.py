from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as postgres_upsert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.core.tracing import start_span
from src.db import AsyncSessionLocal
from src.models import UserDB
from src.schemes import UserUpdate


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
    async def get_or_create_user(self, username: str) -> UserDB:
        with start_span("db.user.get_or_create", attributes={"user.username": username}):
            async with self.session() as session:
                user_db = await session.get(UserDB, username)

                if user_db is None:
                    user_db = UserDB(username=username)
                    session.add(user_db)
                    await session.commit()

                return user_db

    async def get_or_update_user(self, username: str, user_update: UserUpdate | None = None) -> UserDB:
        """Insert or update a user row.  Fields carried by *user_update* are
        applied on conflict; an empty or missing *user_update* is a no-op
        upsert (inserts the row or leaves the existing one untouched)."""
        update_fields: dict[str, object] = {}
        if user_update:
            update_fields = user_update.model_dump(exclude_unset=True)

        values: dict[str, object] = {"username": username, **update_fields}
        # On conflict we always update: when *user_update* is empty the SET
        # clause is a single no-op assignment on the PK column itself.
        set_clause: dict[str, object] = update_fields if update_fields else {"username": username}

        with start_span("db.user.get_or_update", attributes={"user.username": username}):
            async with self.session() as session:
                stmt = (
                    postgres_upsert(UserDB)
                    .values(**values)
                    .on_conflict_do_update(
                        index_elements=[UserDB.username],
                        set_=set_clause,
                    )
                    .returning(UserDB)
                )
                result = await session.execute(stmt)
                await session.commit()
                return result.scalar_one()


def get_user_crud() -> UserCRUD:
    return UserCRUD(AsyncSessionLocal)
