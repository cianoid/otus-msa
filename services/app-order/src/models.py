from uuid import uuid4

from sqlalchemy import Column, DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class OrderDB(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    username = Column(String, nullable=False, index=True)
    price = Column(Numeric(18, 2), nullable=False)
    status = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
