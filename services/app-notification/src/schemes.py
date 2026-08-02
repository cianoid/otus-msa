from pydantic import BaseModel


class Notification(BaseModel):
    id: str
    username: str | None = None
    email: str
    message_type: str
    subject: str | None = None
    body: str | None = None
    created_at: str | None = None

    class Config:
        from_attributes = True
