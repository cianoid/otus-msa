from pydantic import BaseModel


class UserUpdate(BaseModel):
    email: str | None = None
    telegram: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None
    telegram: str | None = None

    class Config:
        from_attributes = True
