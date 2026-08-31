from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as postgres_upsert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.cache import CacheClient
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
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession], cache: CacheClient | None = None) -> None:
        super().__init__(sessionmaker)
        self.cache = cache

    @staticmethod
    def _profile_cache_key(username: str) -> str:
        return f"user:profile:{username}"

    async def get_or_create_user(self, username: str) -> UserDB:
        cache_key = self._profile_cache_key(username)
        if self.cache is not None:
            cached = await self.cache.get_json(cache_key)
            if cached is not None:
                return UserDB(**cached)

        with start_span("db.user.get_or_create", attributes={"user.username": username}):
            async with self.session() as session:
                user_db = await session.get(UserDB, username)

                if user_db is None:
                    user_db = UserDB(username=username)
                    session.add(user_db)
                    await session.commit()

        if self.cache is not None:
            await self.cache.set_json(
                cache_key,
                {"username": user_db.username, "email": user_db.email, "telegram": user_db.telegram},
            )
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
                user_db = result.scalar_one()

        if self.cache is not None:
            await self.cache.delete(self._profile_cache_key(username))
        return user_db


def get_user_crud() -> UserCRUD:
    return UserCRUD(AsyncSessionLocal)
