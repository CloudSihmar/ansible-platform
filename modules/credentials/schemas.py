from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
import uuid

class SSHKeyBase(BaseModel):
    name: str
    private_key: str
    public_key: str
    passphrase: Optional[str] = None

    @validator('name')
    def validate_name(cls, v):
        if len(v) < 1 or len(v) > 100:
            raise ValueError('Name must be between 1 and 100 characters')
        return v

    @validator('private_key')
    def validate_private_key(cls, v):
        if not v.strip():
            raise ValueError('Private key cannot be empty')
        # More flexible validation
        if 'PRIVATE' not in v.upper():
            raise ValueError('Invalid private key format - should contain PRIVATE key markers')
        return v

    @validator('public_key')
    def validate_public_key(cls, v):
        if not v.strip():
            raise ValueError('Public key cannot be empty')
        return v

class SSHKeyCreate(SSHKeyBase):
    pass

class SSHKeyResponse(SSHKeyBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

class CredentialBase(BaseModel):
    name: str
    username: Optional[str] = None
    password: Optional[str] = None
    credential_type: str

    @validator('name')
    def validate_name(cls, v):
        if len(v) < 1 or len(v) > 100:
            raise ValueError('Name must be between 1 and 100 characters')
        return v

    @validator('credential_type')
    def validate_credential_type(cls, v):
        allowed_types = ['ssh_password', 'api_token', 'vault_password', 'cloud_access_key']
        if v not in allowed_types:
            raise ValueError(f'Credential type must be one of: {", ".join(allowed_types)}')
        return v

class CredentialCreate(CredentialBase):
    pass

class CredentialResponse(CredentialBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

# Response schemas that don't include sensitive data
class SSHKeySafeResponse(BaseModel):
    id: uuid.UUID
    name: str
    public_key: str
    created_at: datetime

    class Config:
        from_attributes = True

class CredentialSafeResponse(BaseModel):
    id: uuid.UUID
    name: str
    credential_type: str
    created_at: datetime

    class Config:
        from_attributes = True
