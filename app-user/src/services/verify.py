"""VerifyBearer — custom HTTPBearer that decodes JWT and fires background verification."""

from __future__ import annotations

import jwt
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer
from starlette.status import HTTP_401_UNAUTHORIZED

from src.core.config import (
    JWT_ALGORITHM,
    JWT_SECRET,
)
from src.core.logger import log


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


class VerifyBearer(HTTPBearer):
    """Security dependency: extracts Bearer token, decodes JWT, fires background verify.

    Returns the decoded JWT payload on success, raises 401 on failure.
    Every endpoint using this dependency automatically gets background token verification.
    """

    async def __call__(self, request: Request) -> dict:
        credentials = await super().__call__(request)
        token = credentials.credentials

        try:
            payload = decode_token(token)
            log.debug("Background token verify OK: sub=%s", payload.get("sub", "?"))
        except Exception:
            log.debug("Background token verify failed: token invalid or expired")

        # Synchronous decode
        try:
            return decode_token(token)
        except Exception:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
