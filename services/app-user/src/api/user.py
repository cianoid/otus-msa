from fastapi import APIRouter, Depends
from src.crud import UserCRUD, get_user_crud
from src.schemes import User, UserUpdate
from src.services.verify import VerifyBearer
from starlette.status import HTTP_200_OK

router = APIRouter(prefix="/profile", tags=["profile"])
security = VerifyBearer()


@router.get("", response_model=User, status_code=HTTP_200_OK)
async def profile(
    payload: dict = Depends(security),
    user_crud: UserCRUD = Depends(get_user_crud),
):
    user = await user_crud.get_or_create_user(payload.get("sub", ""))
    return User(username=user.username, telegram=user.telegram)


@router.put("", response_model=User)
async def update_user(
    user_data: UserUpdate,
    payload: dict = Depends(security),
    user_crud: UserCRUD = Depends(get_user_crud),
):
    user = await user_crud.get_or_update_user(payload.get("sub", ""), user_data)
    return User(username=user.username, telegram=user.telegram)
