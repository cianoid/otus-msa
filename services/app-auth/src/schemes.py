from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str
    password: str
    email: str


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
