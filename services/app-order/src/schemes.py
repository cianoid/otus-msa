import datetime as dt
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    price: Decimal = Field(..., gt=0, decimal_places=2)


class Order(BaseModel):
    id: UUID
    username: str
    price: Decimal
    status: str
    created_at: dt.datetime

    class Config:
        from_attributes = True
