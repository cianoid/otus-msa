import datetime as dt
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    price: Decimal = Field(..., gt=0, decimal_places=2)
    product_id: int
    quantity: int = Field(..., gt=0)
    slot_id: int


class Order(BaseModel):
    id: UUID
    username: str
    price: Decimal
    status: str
    product_id: int | None = None
    quantity: int | None = None
    slot_id: int | None = None
    created_at: dt.datetime
    updated_at: dt.datetime | None = None
    error: str | None = None
    idempotency_key: str | None = None

    class Config:
        from_attributes = True
