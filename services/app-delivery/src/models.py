from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
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


class SlotDB(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    time_slot = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False)
    reserved = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CourierReservationDB(Base):
    __tablename__ = "courier_reservations"

    id = Column(String, primary_key=True, index=True, nullable=False)
    order_id = Column(String, nullable=False)
    slot_id = Column(Integer, ForeignKey("slots.id"), nullable=False)
    status = Column(String, nullable=False, default="active")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
