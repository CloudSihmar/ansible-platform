from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from core.database import get_db
from core.auth import auth_manager
from modules.users.service import UserService
from modules.users.schemas import UserResponse

security = HTTPBearer()

async def get_current_user(
    token: str = Depends(security),
    db: Session = Depends(get_db)
) -> UserResponse:
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
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user
