from typing import Optional

from pydantic import BaseModel


class UserCreate(BaseModel):
    name: str
    email: str
    age: int


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None


class User(BaseModel):
    id: str
    name: str
    email: str
    age: int

    class Config:
        from_attributes = True

