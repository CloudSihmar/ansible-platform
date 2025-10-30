from pydantic import BaseModel, validator
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class InventoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    inventory_type: str = "static"
    content: str
    variables: Optional[Dict[str, Any]] = {}

    @validator('name')
    def validate_name(cls, v):
        if len(v) < 1 or len(v) > 100:
            raise ValueError('Name must be between 1 and 100 characters')
        return v

    @validator('inventory_type')
    def validate_inventory_type(cls, v):
        if v not in ['static', 'dynamic']:
            raise ValueError('Inventory type must be static or dynamic')
        return v

    @validator('content')
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError('Content cannot be empty')
        return v

class InventoryCreate(InventoryBase):
    pass

class InventoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None

class InventoryResponse(InventoryBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
