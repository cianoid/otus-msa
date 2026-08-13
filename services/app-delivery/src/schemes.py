from pydantic import BaseModel, Field


class Slot(BaseModel):
    id: int
    time_slot: str
    capacity: int
    reserved: int

    class Config:
        from_attributes = True


class SlotCreateRequest(BaseModel):
    time_slot: str
    capacity: int = Field(..., ge=0)


class ReserveRequest(BaseModel):
    order_id: str
    slot_id: int


class ReserveResponse(BaseModel):
    success: bool
    reservation_id: str | None = None


class CancelRequest(BaseModel):
    reservation_id: str


class CancelResponse(BaseModel):
    success: bool
