from pydantic import BaseModel, Field


class Product(BaseModel):
    id: int
    name: str
    stock: int

    class Config:
        from_attributes = True


class ProductCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    stock: int = Field(..., ge=0)


class ReserveRequest(BaseModel):
    order_id: str = Field(..., min_length=1)
    product_id: int
    quantity: int = Field(..., gt=0)


class ReserveResponse(BaseModel):
    success: bool
    reservation_id: str | None
    stock: int


class CancelRequest(BaseModel):
    reservation_id: str = Field(..., min_length=1)


class CancelResponse(BaseModel):
    success: bool
