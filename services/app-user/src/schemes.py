from pydantic import BaseModel


class UserUpdate(BaseModel):
    telegram: str | None = None


class User(BaseModel):
    username: str
    telegram: str | None = None

    class Config:
        from_attributes = True
