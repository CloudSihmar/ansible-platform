from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from core.database import get_db
from modules.users.service import UserService
from modules.users.schemas import UserResponse, UserCreate, UserUpdate
from api.middleware.auth import get_current_user

router = APIRouter()

@router.get("/users", response_model=List[UserResponse])
async def get_users(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    user_service = UserService(db)
    
    # Check permission
    if not user_service.user_has_permission(current_user.id, "users:read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return user_service.get_all_users()

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    user_service = UserService(db)
    
    # Check permission
    if not user_service.user_has_permission(current_user.id, "users:read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    user_service = UserService(db)
    
    # Check permission
    if not user_service.user_has_permission(current_user.id, "users:create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        user = user_service.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
