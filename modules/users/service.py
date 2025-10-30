from sqlalchemy.orm import Session
from typing import Optional, List
import uuid

from .models import User
from .schemas import UserCreate, UserUpdate
from core.auth import auth_manager
from core.permissions import permission_manager

class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_all_users(self) -> List[User]:
        """Get all active users"""
        return self.db.query(User).filter(User.is_active == True).all()
    
    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user"""
        # Check if user already exists
        if self.get_user_by_username(user_data.username):
            raise ValueError("Username already exists")
        
        if self.get_user_by_email(user_data.email):
            raise ValueError("Email already exists")
        
        # Hash password
        password_hash = auth_manager.hash_password(user_data.password)
        
        # Create user
        user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
            role=user_data.role,
            is_active=user_data.is_active
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def update_user(self, user_id: uuid.UUID, user_data: UserUpdate) -> Optional[User]:
        """Update user"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        update_data = user_data.dict(exclude_unset=True)
        
        # Handle password update
        if 'password' in update_data:
            update_data['password_hash'] = auth_manager.hash_password(update_data.pop('password'))
        
        for field, value in update_data.items():
            setattr(user, field, value)
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def delete_user(self, user_id: uuid.UUID) -> bool:
        """Soft delete user"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.is_active = False
        self.db.commit()
        return True
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user"""
        user = self.get_user_by_username(username)
        if not user or not user.is_active:
            return None
        
        if not auth_manager.verify_password(password, user.password_hash):
            return None
        
        return user
    
    def user_has_permission(self, user_id: uuid.UUID, permission: str) -> bool:
        """Check if user has specific permission"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        return permission_manager.has_permission(user.role, permission)
