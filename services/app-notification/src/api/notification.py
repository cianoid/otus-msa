from fastapi import APIRouter, Depends
from src.crud import NotificationCRUD, get_notification_crud
from src.models import NotificationDB
from src.schemes import Notification
from src.services.verify import VerifyBearer
from starlette.status import HTTP_200_OK

router = APIRouter(prefix="/api/v1/notification", tags=["Notifications"])
security = VerifyBearer()


@router.get("", response_model=list[Notification], status_code=HTTP_200_OK)
async def list_notifications(
    payload: dict = Depends(security),
    notification_crud: NotificationCRUD = Depends(get_notification_crud),
):
    notifications: list[NotificationDB] = await notification_crud.list_all(payload.get("sub", ""))
    return [Notification(**n.model_to_dict()) for n in notifications]
