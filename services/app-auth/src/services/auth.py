from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from src.core.config import settings


def hash_password(password: str) -> str:
    return PasswordHasher().hash(password)  # принимает пароль любой длины


def verify_password(plain: str, hashed: str) -> bool:
    return PasswordHasher().verify(hashed, plain)


def create_access_token(username: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": username,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(username: str) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": username,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
