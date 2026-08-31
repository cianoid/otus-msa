from fastapi import APIRouter, Depends, Request
from starlette.status import HTTP_200_OK

from src.core.logger import log
from src.crud import NotificationCRUD, get_notification_crud
from src.models import NotificationDB
from src.schemes import Notification
from src.services.verify import VerifyBearer

router = APIRouter(prefix="/api/v1/notification", tags=["Notifications"])
security = VerifyBearer()


@router.get("", response_model=list[Notification], status_code=HTTP_200_OK)
async def list_notifications(
    payload: dict = Depends(security),
    notification_crud: NotificationCRUD = Depends(get_notification_crud),
):
    notifications: list[NotificationDB] = await notification_crud.list_all(payload.get("sub", ""))
    return [Notification(**n.model_to_dict()) for n in notifications]


@router.post("/alerts/events", status_code=HTTP_200_OK)
async def receive_alert_event(request: Request):
    """Webhook receiver for Alertmanager / Grafana alerting events."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    log.info("received alert event: %s", body)
    return {"status": "received"}
