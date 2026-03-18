from fastapi import APIRouter, Depends, HTTPException
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND

from app.crud import UserCRUD, get_user_crud
from app.schemes import User, UserCreate, UserUpdate

router = APIRouter()


@router.post("/users/", response_model=User, status_code=HTTP_201_CREATED)
async def create_user(user: UserCreate, crud: UserCRUD = Depends(get_user_crud)):
    """Create a new user"""
    return await crud.create_user(user)



@router.get("/users/{user_id}", response_model=User)
async def read_user(user_id: str, crud: UserCRUD = Depends(get_user_crud)):
    """Get a specific user by ID"""
    db_user = await crud.read_user(user_id)
    if not db_user:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
    return db_user


@router.get("/users/", response_model=list[User])
async def read_users(skip: int = 0, limit: int = 20, crud: UserCRUD = Depends(get_user_crud)):
    """Get a list of users with pagination"""
    users = await crud.read_users(skip, limit)
    return users


@router.put("/users/{user_id}", response_model=User)
async def update_user(user_id: str, user_update: UserUpdate, crud: UserCRUD = Depends(get_user_crud)):
    """Update a specific user by ID"""
    updated_user = await crud.update_user(user_id, user_update)
    if updated_user is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")

    return updated_user


@router.delete("/users/{user_id}", status_code=HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, crud: UserCRUD = Depends(get_user_crud)):
    """Delete a specific user by ID"""
    db_user = await crud.delete_user(user_id)
    if not db_user:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")
    return
