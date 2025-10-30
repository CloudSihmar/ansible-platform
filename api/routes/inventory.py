from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from core.database import get_db
from modules.inventory.service import InventoryService
from modules.inventory.schemas import InventoryCreate, InventoryUpdate, InventoryResponse
from modules.users.schemas import UserResponse
from api.middleware.auth import get_current_user

router = APIRouter()

@router.get("/inventory", response_model=List[InventoryResponse])
async def get_inventories(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    inventory_service = InventoryService(db)
    return inventory_service.get_user_inventories(current_user.id)

@router.get("/inventory/{inventory_id}", response_model=InventoryResponse)
async def get_inventory(
    inventory_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    inventory_service = InventoryService(db)
    inventory = inventory_service.get_inventory_by_id(inventory_id)
    
    if not inventory or inventory.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found"
        )
    
    return inventory

@router.post("/inventory", response_model=InventoryResponse)
async def create_inventory(
    inventory_data: InventoryCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    inventory_service = InventoryService(db)
    
    try:
        # Basic validation of inventory content
        if not inventory_service.validate_inventory_content(inventory_data.content):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid inventory content format"
            )
        
        inventory = inventory_service.create_inventory(inventory_data, current_user.id)
        return inventory
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/inventory/{inventory_id}", response_model=InventoryResponse)
async def update_inventory(
    inventory_id: uuid.UUID,
    inventory_data: InventoryUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    inventory_service = InventoryService(db)
    
    try:
        inventory = inventory_service.update_inventory(inventory_id, inventory_data, current_user.id)
        if not inventory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory not found"
            )
        return inventory
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/inventory/{inventory_id}")
async def delete_inventory(
    inventory_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    inventory_service = InventoryService(db)
    
    success = inventory_service.delete_inventory(inventory_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found"
        )
    
    return {"message": "Inventory deleted successfully"}
