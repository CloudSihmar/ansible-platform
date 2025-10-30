from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from .models import Inventory
from .schemas import InventoryCreate, InventoryUpdate

class InventoryService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_inventory_by_id(self, inventory_id: uuid.UUID) -> Optional[Inventory]:
        """Get inventory by ID"""
        return self.db.query(Inventory).filter(Inventory.id == inventory_id).first()
    
    def get_inventory_by_name(self, name: str, user_id: uuid.UUID) -> Optional[Inventory]:
        """Get inventory by name for a specific user"""
        return self.db.query(Inventory).filter(
            Inventory.name == name, 
            Inventory.user_id == user_id
        ).first()
    
    def get_user_inventories(self, user_id: uuid.UUID) -> List[Inventory]:
        """Get all inventories for a user"""
        return self.db.query(Inventory).filter(Inventory.user_id == user_id).all()
    
    def create_inventory(self, inventory_data: InventoryCreate, user_id: uuid.UUID) -> Inventory:
        """Create a new inventory"""
        # Check if inventory with same name already exists for this user
        if self.get_inventory_by_name(inventory_data.name, user_id):
            raise ValueError("Inventory with this name already exists")
        
        inventory = Inventory(
            name=inventory_data.name,
            description=inventory_data.description,
            inventory_type=inventory_data.inventory_type,
            content=inventory_data.content,
            variables=inventory_data.variables or {},
            user_id=user_id
        )
        
        self.db.add(inventory)
        self.db.commit()
        self.db.refresh(inventory)
        
        return inventory
    
    def update_inventory(self, inventory_id: uuid.UUID, inventory_data: InventoryUpdate, user_id: uuid.UUID) -> Optional[Inventory]:
        """Update inventory"""
        inventory = self.get_inventory_by_id(inventory_id)
        if not inventory or inventory.user_id != user_id:
            return None
        
        update_data = inventory_data.dict(exclude_unset=True)
        
        # Check name uniqueness if name is being updated
        if 'name' in update_data and update_data['name'] != inventory.name:
            if self.get_inventory_by_name(update_data['name'], user_id):
                raise ValueError("Inventory with this name already exists")
        
        for field, value in update_data.items():
            setattr(inventory, field, value)
        
        self.db.commit()
        self.db.refresh(inventory)
        
        return inventory
    
    def delete_inventory(self, inventory_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete inventory"""
        inventory = self.get_inventory_by_id(inventory_id)
        if not inventory or inventory.user_id != user_id:
            return False
        
        self.db.delete(inventory)
        self.db.commit()
        return True
    
    def validate_inventory_content(self, content: str) -> bool:
        """Basic inventory content validation"""
        # Check if it's valid INI format (basic check)
        lines = content.strip().split('\n')
        group_found = False
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                if line.startswith('[') and line.endswith(']'):
                    group_found = True
                elif '=' in line and group_found:
                    return True
        
        return False
