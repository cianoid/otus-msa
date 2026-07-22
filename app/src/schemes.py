from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3)
    email: EmailStr
    password: str = Field(min_length=3)
    age: int
    real_name: str = Field(min_length=1)


class UserUpdate(BaseModel):

    email: Optional[EmailStr] = None
    age: Optional[int] = None
    real_name: Optional[str] = None


class User(BaseModel):
    id: str
    username: str
    real_name: str
    email: str
    age: int

    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    username: str = Field(min_length=3)
    email: EmailStr
    age: int
    real_name: str = Field(min_length=1)


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
