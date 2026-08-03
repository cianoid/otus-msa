from decimal import Decimal

from pydantic import BaseModel, Field


class Account(BaseModel):
    username: str
    balance: Decimal

    class Config:
        from_attributes = True


class DepositRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2)


class WithdrawRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2)


class WithdrawResponse(BaseModel):
    success: bool
    balance: Decimal
