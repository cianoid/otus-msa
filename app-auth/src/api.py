from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_401_UNAUTHORIZED,
    HTTP_409_CONFLICT,
)

from src.auth import (
    create_access_token,
    create_refresh_token,
    create_user,
    decode_token,
    get_user_by_username,
    verify_password,
)
from src.db import get_async_session
from src.schemes import TokenPair, TokenRefresh, TokenVerify, TokenVerifyResponse, UserLogin, UserRegister

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenPair, status_code=HTTP_201_CREATED)
async def register(body: UserRegister, db: AsyncSession = Depends(get_async_session)):
    existing = await get_user_by_username(db, body.username)
    if existing:
        raise HTTPException(status_code=HTTP_409_CONFLICT, detail="Username already taken")

    user = await create_user(db, body.username, body.email, body.password)

    access_token = create_access_token(user.username)
    refresh_token = create_refresh_token(user.username)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenPair)
async def login(body: UserLogin, db: AsyncSession = Depends(get_async_session)):
    user = await get_user_by_username(db, body.username)
    if not user or not verify_password(body.password, user.password_hash):
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


@router.get("/liveness", status_code=HTTP_200_OK)
async def liveness():
    return {"status": "ok"}


@router.get("/readiness", status_code=HTTP_200_OK)
async def readiness():
    return {"status": "ok"}
