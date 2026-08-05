from fastapi import APIRouter, Depends, Request
from src.crud import OrderCRUD, get_order_crud
from src.kafka import KafkaClient, get_kafka
from src.schemes import Order, OrderCreate
from src.services.http_client import ServiceClient
from src.services.verify import VerifyBearer
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

router = APIRouter(prefix="/api/v1/order", tags=["order"])
security = VerifyBearer()


def _extract_token(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1]
    return ""


@router.get("", response_model=list[Order], status_code=HTTP_200_OK)
async def list_orders(
    payload: dict = Depends(security),
    order_crud: OrderCRUD = Depends(get_order_crud),
):
    orders = await order_crud.list_orders(payload.get("sub", ""))
    return [Order(**o.__dict__) for o in orders]


@router.post("", response_model=Order, status_code=HTTP_201_CREATED)
async def create_order(
    request: OrderCreate,
    req: Request,
    kafka: KafkaClient = Depends(get_kafka),
    payload: dict = Depends(security),
    order_crud: OrderCRUD = Depends(get_order_crud),
):
    username = payload.get("sub", "")
    token = _extract_token(req)
    http_client = ServiceClient()

    try:
        # 1. Try to withdraw money synchronously.
        billing_result = await http_client.withdraw_from_billing(username, request.price, token)
        success = billing_result.get("success", False)

        # 2. Persist order.
        status = "paid" if success else "failed"
        order = await order_crud.create_order(username, request.price, status)

        # 3. Fetch user profile for email.
        profile = await http_client.get_user_profile(token)
        email = profile.get("email")

        # 4. Send notification event.
        message_type = "ORDER_SUCCESS" if success else "ORDER_FAILED"
        await kafka.send_notification(
            notification_id=str(order.id),
            message_type=message_type,
            username=username,
            email=email,
            data={
                "order_id": str(order.id),
                "price": str(request.price),
                "balance": str(billing_result.get("balance", "0.00")),
            },
        )
    finally:
        await http_client.close()

    return Order(**order.__dict__)
