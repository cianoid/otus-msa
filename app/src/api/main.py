from fastapi import APIRouter
from fastapi.security import  HTTPBearer
from starlette.status import (
    HTTP_200_OK,
)

router = APIRouter(tags=["main"])
security = HTTPBearer()



@router.get("/liveness", status_code=HTTP_200_OK)
async def liveness():
    return {"status": "ok"}


@router.get("/readiness", status_code=HTTP_200_OK)
async def readiness():
    return {"status": "ok"}
