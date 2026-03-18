from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"server_settings": {"timezone": "Europe/Moscow"}},
    pool_size=5,
    pool_recycle=3600,
    max_overflow=100,
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as async_session:
        yield async_session
