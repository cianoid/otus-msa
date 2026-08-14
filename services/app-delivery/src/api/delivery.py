from fastapi import APIRouter, Depends
from src.core.tracing import start_span
from src.crud import DeliveryCRUD, get_delivery_crud
from src.schemes import (
    CancelRequest,
    CancelResponse,
    ReserveRequest,
    ReserveResponse,
    Slot,
    SlotCreateRequest,
)
from src.services.verify import VerifyBearer
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

router = APIRouter(prefix="/api/v1/delivery", tags=["delivery"])
security = VerifyBearer()


@router.get("/slots", response_model=list[Slot], status_code=HTTP_200_OK)
async def get_slots(
    payload: dict = Depends(security),
    delivery_crud: DeliveryCRUD = Depends(get_delivery_crud),
):
    with start_span("delivery.list_slots"):
        return await delivery_crud.get_slots()


@router.post("/slots", response_model=Slot, status_code=HTTP_201_CREATED)
async def create_slot(
    request: SlotCreateRequest,
    payload: dict = Depends(security),
    delivery_crud: DeliveryCRUD = Depends(get_delivery_crud),
):
    with start_span(
        "delivery.create_slot",
        attributes={"delivery.time_slot": request.time_slot, "delivery.capacity": request.capacity},
    ):
        return await delivery_crud.create_slot(request.time_slot, request.capacity)


@router.post("/reserve", response_model=ReserveResponse, status_code=HTTP_200_OK)
async def reserve(
    request: ReserveRequest,
    payload: dict = Depends(security),
    delivery_crud: DeliveryCRUD = Depends(get_delivery_crud),
):
    with start_span(
        "delivery.reserve",
        attributes={"order.id": request.order_id, "delivery.slot_id": request.slot_id},
    ):
        reservation = await delivery_crud.reserve(request.order_id, request.slot_id)
        if reservation is None:
            return ReserveResponse(success=False, reservation_id=None)
        return ReserveResponse(success=True, reservation_id=reservation.id)


@router.post("/cancel", response_model=CancelResponse, status_code=HTTP_200_OK)
async def cancel(
    request: CancelRequest,
    payload: dict = Depends(security),
    delivery_crud: DeliveryCRUD = Depends(get_delivery_crud),
):
    with start_span("delivery.cancel", attributes={"delivery.reservation_id": request.reservation_id}):
        success = await delivery_crud.cancel(request.reservation_id)
        return CancelResponse(success=success)
