from decimal import Decimal

from sqlalchemy import Column, DateTime, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class IdempotencyKeyDB(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("idempotency_key", "kind", name="uq_idempotency_keys_key_kind"),)

    idempotency_key = Column(String, nullable=False)
    kind = Column(String, nullable=False)
    payload = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __mapper_args__ = {"primary_key": [idempotency_key, kind]}


class AccountDB(Base):
    __tablename__ = "accounts"

    username = Column(String, primary_key=True, index=True, nullable=False)
    balance = Column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
