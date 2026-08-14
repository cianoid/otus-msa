from fastapi import APIRouter, Depends
from src.core.tracing import start_span
from src.crud import WarehouseCRUD, get_warehouse_crud
from src.schemes import (
    CancelRequest,
    CancelResponse,
    Product,
    ProductCreateRequest,
    ReserveRequest,
    ReserveResponse,
)
from src.services.verify import VerifyBearer
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

router = APIRouter(prefix="/api/v1/warehouse", tags=["warehouse"])
security = VerifyBearer()


@router.get("/products", response_model=list[Product], status_code=HTTP_200_OK)
async def list_products(
    payload: dict = Depends(security),
    warehouse_crud: WarehouseCRUD = Depends(get_warehouse_crud),
):
    with start_span("warehouse.list_products"):
        return await warehouse_crud.list_products()


@router.post("/products", response_model=Product, status_code=HTTP_201_CREATED)
async def create_product(
    request: ProductCreateRequest,
    payload: dict = Depends(security),
    warehouse_crud: WarehouseCRUD = Depends(get_warehouse_crud),
):
    with start_span(
        "warehouse.create_product", attributes={"product.name": request.name, "product.stock": request.stock}
    ):
        return await warehouse_crud.create_product(request.name, request.stock)


@router.post("/reserve", response_model=ReserveResponse, status_code=HTTP_200_OK)
async def reserve(
    request: ReserveRequest,
    payload: dict = Depends(security),
    warehouse_crud: WarehouseCRUD = Depends(get_warehouse_crud),
):
    with start_span(
        "warehouse.reserve",
        attributes={
            "order.id": request.order_id,
            "warehouse.product_id": request.product_id,
            "warehouse.quantity": request.quantity,
        },
    ):
        reservation, stock = await warehouse_crud.reserve(request.order_id, request.product_id, request.quantity)
        if reservation is None:
            return ReserveResponse(success=False, reservation_id=None, stock=stock)
        return ReserveResponse(success=True, reservation_id=reservation.id, stock=stock)


@router.post("/cancel", response_model=CancelResponse, status_code=HTTP_200_OK)
async def cancel(
    request: CancelRequest,
    payload: dict = Depends(security),
    warehouse_crud: WarehouseCRUD = Depends(get_warehouse_crud),
):
    with start_span("warehouse.cancel", attributes={"warehouse.reservation_id": request.reservation_id}):
        success = await warehouse_crud.cancel(request.reservation_id)
        return CancelResponse(success=success)
