from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class NotificationDB(Base):
    __tablename__ = "notifications"

    id = Column(UUID, primary_key=True, nullable=False)
    username = Column(String, nullable=True)
    email = Column(String, nullable=False)
    message_type = Column(String, nullable=False)
    subject = Column(String, nullable=True)
    body = Column(String, nullable=True)
    status = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
