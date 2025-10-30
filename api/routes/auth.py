from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from datetime import timedelta

from core.database import get_db
from core.auth import auth_manager
from modules.users.service import UserService
from modules.users.schemas import LoginRequest, Token, UserCreate, UserResponse
from config.settings import settings

router = APIRouter()
security = HTTPBearer()

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user_service = UserService(db)
    user = user_service.authenticate_user(login_data.username, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth_manager.create_access_token(
        data={"sub": user.username, "user_id": str(user.id), "role": user.role}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    user_service = UserService(db)
    
    try:
        user = user_service.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user(
    token: str = Depends(security),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = auth_manager.verify_token(token.credentials)
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    user_service = UserService(db)
    user = user_service.get_user_by_username(username)
    if user is None:
        raise credentials_exception
    
    return user
