from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class OrderDB(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("username", "idempotency_key", name="uq_orders_username_idempotency_key"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    username = Column(String, nullable=False, index=True)
    price = Column(Numeric(18, 2), nullable=False)
    status = Column(String, nullable=False)  # pending, paid, failed
    product_id = Column(Integer, nullable=True)
    quantity = Column(Integer, nullable=True)
    slot_id = Column(Integer, nullable=True)
    error = Column(String, nullable=True)
    idempotency_key = Column(String, nullable=True)
    saga_state = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SagaStepDB(Base):
    __tablename__ = "saga_steps"
    __table_args__ = (UniqueConstraint("order_id", "step_name", name="uq_saga_steps_order_id_step_name"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    order_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    step_name = Column(String, nullable=False)  # warehouse_reserve, delivery_reserve, billing_withdraw
    status = Column(String, nullable=False)  # pending, in_progress, completed, failed
    attempts = Column(Integer, nullable=False, default=0)
    request_payload = Column(JSONB, nullable=True)
    result_payload = Column(JSONB, nullable=True)
    error = Column(String, nullable=True)
    reservation_id = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class OutboxDB(Base):
    __tablename__ = "outbox"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    order_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    kind = Column(String, nullable=False)  # compensation_warehouse, compensation_delivery, notification
    status = Column(String, nullable=False, default="pending", index=True)  # pending, processing, processed, failed
    payload = Column(JSONB, nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    error = Column(String, nullable=True)
    scheduled_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
