from fastapi import APIRouter, Depends, HTTPException
from src.core.logger import log
from src.crud import UserCRUD, get_user_crud
from src.kafka import send_user_created
from src.schemes import TokenPair, TokenRefresh, TokenVerify, TokenVerifyResponse, UserCreate, UserLogin
from src.services.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from starlette.status import (
    HTTP_201_CREATED,
    HTTP_401_UNAUTHORIZED,
    HTTP_409_CONFLICT,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenPair, status_code=HTTP_201_CREATED)
async def register(user_data: UserCreate, user_crud: UserCRUD = Depends(get_user_crud)):
    existing = await user_crud.get_user_by_username(user_data.username)
    if existing:
        raise HTTPException(status_code=HTTP_409_CONFLICT, detail="Username already taken")

    try:
        await user_crud.create_user(user_data)
    except Exception as err:
        log.critical("%s: Error during user save", str(err), exc_info=True)

    # Отправляем событие о создании пользователя в Kafka
    await send_user_created(username=user_data.username, email=user_data.email)

    access_token = create_access_token(user_data.username)
    refresh_token = create_refresh_token(user_data.username)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenPair)
async def login(user_data: UserLogin, user_crud: UserCRUD = Depends(get_user_crud)):
    user = await user_crud.get_user_by_username(user_data.username)
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(user.username)
    refresh_token = create_refresh_token(user.username)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: TokenRefresh):
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Token is not a refresh token")

    username = payload["sub"]
    access_token = create_access_token(username)
    refresh_token = create_refresh_token(username)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/verify", response_model=TokenVerifyResponse)
async def verify(body: TokenVerify):
    try:
        payload = decode_token(body.access_token)
    except Exception:
        return TokenVerifyResponse(valid=False)

    if payload.get("type") != "access":
        return TokenVerifyResponse(valid=False)

    return TokenVerifyResponse(valid=True, username=payload.get("sub"))
