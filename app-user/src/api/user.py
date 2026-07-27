from fastapi import APIRouter, Depends, HTTPException

from src.crud import UserCRUD, get_user_crud
from src.schemes import User, UserProfile, UserUpdate
from src.services.verify import VerifyBearer
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND

router = APIRouter(prefix="/profile", tags=["profile"])
security = VerifyBearer()


@router.get("", response_model=UserProfile, status_code=HTTP_200_OK)
async def profile(
    payload: dict = Depends(security),
    user_crud: UserCRUD = Depends(get_user_crud),
):
    async with user_crud.session() as session:
        user = await user_crud.get_or_update_user(session, payload.get("sub", ""))
    return UserProfile(username=user.username, telegram=user.telegram)


@router.put("", response_model=User)
async def update_user(
    user_data: UserUpdate,
    payload: dict = Depends(security),
    user_crud: UserCRUD = Depends(get_user_crud),
):
    async with user_crud.session() as session:
        updated_user = await user_crud.get_or_update_user(session, payload.get("sub", ""), user_data)
        if updated_user is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")

    return updated_user
