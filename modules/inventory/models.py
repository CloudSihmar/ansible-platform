from sqlalchemy import Column, String, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from core.database import BaseModel

class Inventory(BaseModel):
    __tablename__ = "inventory"

    name = Column(String(100), nullable=False)
    description = Column(Text)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    inventory_type = Column(String(20), default='static')
    content = Column(Text, nullable=False)
    variables = Column(JSON, default=dict)
    created_at = Column(Text, server_default=func.now())
    updated_at = Column(Text, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Inventory(name='{self.name}', type='{self.inventory_type}')>"
