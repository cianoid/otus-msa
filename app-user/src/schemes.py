from pydantic import BaseModel, Field


class UserUpdate(BaseModel):
    telegram: str | None = None


class User(BaseModel):
    username: str
    telegram: str

    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    username: str = Field(min_length=3)
    telegram: str | None
