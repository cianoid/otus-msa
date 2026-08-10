from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

RESERVATION_STATUS_ACTIVE = "active"
RESERVATION_STATUS_CANCELLED = "cancelled"


class ProductDB(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    stock = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ReservationDB(Base):
    __tablename__ = "reservations"

    id = Column(String, primary_key=True, index=True, nullable=False)
    order_id = Column(String, nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(String, default=RESERVATION_STATUS_ACTIVE, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
