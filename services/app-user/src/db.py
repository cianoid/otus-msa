from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.core.config import settings
from src.core.logger import log
from src.core.tracing import instrument_sqlalchemy_engine

engine = create_async_engine(
    settings.database_url,
    pool_size=5,
    pool_recycle=3600,
    max_overflow=100,
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
instrument_sqlalchemy_engine(engine)
log.info(
    "Database DSN: %s",
    (settings.database_url.split("@")[0].rsplit(":", maxsplit=1)[0]) + ":***@" + settings.database_url.split("@")[1],
)


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as async_session:
        yield async_session
