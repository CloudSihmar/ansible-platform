from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import uuid

# Base schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: str = "ansible_operator"
    is_active: bool = True

# Create schemas
class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

# Response schemas
class UserResponse(UserBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[uuid.UUID] = None

class LoginRequest(BaseModel):
    username: str
    password: str
