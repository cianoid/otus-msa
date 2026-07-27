from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3)
    email: EmailStr
    password: str = Field(min_length=3)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    age: Optional[int] = None
    real_name: Optional[str] = None


class UserLogin(BaseModel):
    username: str = Field()
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class TokenVerify(BaseModel):
    access_token: str


class TokenVerifyResponse(BaseModel):
    valid: bool
    username: str | None = None
