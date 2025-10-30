from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from core.database import BaseModel

class SSHKey(BaseModel):
    __tablename__ = "ssh_keys"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    private_key = Column(Text, nullable=False)  # Will be encrypted
    public_key = Column(Text, nullable=False)
    passphrase = Column(Text)  # Will be encrypted if provided
    created_at = Column(Text, server_default=func.now())

    def __repr__(self):
        return f"<SSHKey(name='{self.name}', user_id='{self.user_id}')>"

class Credential(BaseModel):
    __tablename__ = "credentials"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    username = Column(Text)  # Will be encrypted
    password = Column(Text)  # Will be encrypted
    credential_type = Column(String(50), nullable=False)  # ssh_password, api_token, etc.
    created_at = Column(Text, server_default=func.now())

    def __repr__(self):
        return f"<Credential(name='{self.name}', type='{self.credential_type}')>"
