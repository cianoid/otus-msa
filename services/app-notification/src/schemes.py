import datetime as dt
from uuid import UUID

from pydantic import BaseModel
from src.core.enums import MessageStatus


class Notification(BaseModel):
    id: UUID
    username: str
    email: str
    message_type: str
    subject: str | None = None
    body: str | None = None
    created_at: dt.datetime
    status: MessageStatus

    class Config:
        from_attributes = True
