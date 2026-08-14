from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.core.enums import MessageStatus
from src.core.tracing import start_span
from src.db import AsyncSessionLocal
from src.models import NotificationDB


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


class NotificationCRUD(BaseCRUD):
    async def add_new_message(self, notification_id: UUID, username: str, email: str, message_type: str) -> None:
        with start_span(
            "db.notification.add",
            attributes={
                "notification.id": str(notification_id),
                "notification.username": username,
                "notification.message_type": message_type,
            },
        ):
            async with self.session() as session:
                notification = NotificationDB(
                    id=notification_id,
                    username=username,
                    email=email,
                    message_type=message_type,
                    status=MessageStatus.READY_TO_SEND,
                )
                session.add(notification)
                await session.commit()

    async def _update(self, notification_id: UUID, **fields) -> None:
        with start_span(
            "db.notification.update",
            attributes={"notification.id": str(notification_id), **fields},
        ):
            async with self.session() as session:
                stmt = update(NotificationDB).where(NotificationDB.id == notification_id).values(**fields)
                await session.execute(stmt)
                await session.commit()

    async def update_message_with_data(self, notification_id: UUID, subject: str, body: str) -> None:
        await self._update(notification_id, subject=subject, body=body)

    async def update_message_success(self, notification_id: UUID) -> None:
        await self._update(notification_id, status=MessageStatus.SENT)

    async def update_message_error(self, notification_id: UUID) -> None:
        await self._update(notification_id, status=MessageStatus.ERROR)

    async def get_one(self, notification_id: UUID) -> NotificationDB | None:
        with start_span("db.notification.get_one", attributes={"notification.id": str(notification_id)}):
            async with self.session() as session:
                result = await session.execute(select(NotificationDB).where(NotificationDB.id == notification_id))
                return result.scalars().one_or_none()

    async def list_all(self, username: str) -> list[NotificationDB]:
        with start_span("db.notification.list_all", attributes={"notification.username": username}):
            async with self.session() as session:
                stmt = (
                    select(NotificationDB)
                    .where(NotificationDB.username == username)
                    .order_by(NotificationDB.created_at.desc())
                )
                result = await session.execute(stmt)
                return list(result.scalars().all())


def get_notification_crud() -> NotificationCRUD:
    return NotificationCRUD(AsyncSessionLocal)
