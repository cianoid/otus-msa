from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_401_UNAUTHORIZED

from models import UserDB
from src.crud import UserCRUD, get_user_crud
from src.schemes import User, UserUpdate, UserProfile
from src.services.auth import decode_token

router = APIRouter(prefix="/profile", tags=["profile"])
security = HTTPBearer()


async def _get_user_from_jwt(credentials: HTTPAuthorizationCredentials, user_crud: UserCRUD) -> UserDB:
    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    username = payload.get("sub")
    if not username or not isinstance(username, str):
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Token missing subject")

    user = await user_crud.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")

    return user

@router.get("/", response_model=UserProfile, status_code=HTTP_200_OK)
async def profile(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user_crud: UserCRUD = Depends(get_user_crud),
):
    user = await _get_user_from_jwt(credentials, user_crud)

    return UserProfile(
        username=user.username,
        email=user.email,
        age=user.age,
        real_name=user.real_name,
    )


@router.put("/", response_model=User)
async def update_user(user_data: UserUpdate, user_crud: UserCRUD = Depends(get_user_crud), credentials: HTTPAuthorizationCredentials = Depends(security)):
    user = await _get_user_from_jwt(credentials, user_crud)

    updated_user = await user_crud.update_user(user.username, user_data)
    if updated_user is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")

    return updated_user
