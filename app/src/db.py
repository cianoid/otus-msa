from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.core.config import DATABASE_URL
from src.core.logger import log

engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,
    pool_recycle=3600,
    max_overflow=100,
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
log.info(
    "Database DSN: %s", (DATABASE_URL.split("@")[0].rsplit(":", maxsplit=1)[0]) + ":***@" + DATABASE_URL.split("@")[1]
)


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as async_session:
        yield async_session
