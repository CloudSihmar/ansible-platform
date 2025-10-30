from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from .models import SSHKey, Credential
from .schemas import SSHKeyCreate, CredentialCreate

class CredentialService:
    def __init__(self, db: Session):
        self.db = db
    
    # SSH Key methods
    def get_ssh_key_by_id(self, key_id: uuid.UUID) -> Optional[SSHKey]:
        """Get SSH key by ID"""
        return self.db.query(SSHKey).filter(SSHKey.id == key_id).first()
    
    def get_ssh_key_by_name(self, name: str, user_id: uuid.UUID) -> Optional[SSHKey]:
        """Get SSH key by name for a specific user"""
        return self.db.query(SSHKey).filter(
            SSHKey.name == name, 
            SSHKey.user_id == user_id
        ).first()
    
    def get_user_ssh_keys(self, user_id: uuid.UUID) -> List[SSHKey]:
        """Get all SSH keys for a user"""
        return self.db.query(SSHKey).filter(SSHKey.user_id == user_id).all()
    
    def create_ssh_key(self, key_data: SSHKeyCreate, user_id: uuid.UUID) -> SSHKey:
        """Create a new SSH key"""
        # Check if key with same name already exists for this user
        if self.get_ssh_key_by_name(key_data.name, user_id):
            raise ValueError("SSH key with this name already exists")
        
        ssh_key = SSHKey(
            name=key_data.name,
            private_key=key_data.private_key,  # Plain text for now
            public_key=key_data.public_key,
            passphrase=key_data.passphrase,  # Plain text for now
            user_id=user_id
        )
        
        self.db.add(ssh_key)
        self.db.commit()
        self.db.refresh(ssh_key)
        
        return ssh_key
    
    def get_ssh_key_data(self, key_id: uuid.UUID, user_id: uuid.UUID) -> Optional[dict]:
        """Get SSH key data"""
        ssh_key = self.get_ssh_key_by_id(key_id)
        if not ssh_key or ssh_key.user_id != user_id:
            return None
        
        return {
            'id': ssh_key.id,
            'name': ssh_key.name,
            'private_key': ssh_key.private_key,
            'public_key': ssh_key.public_key,
            'passphrase': ssh_key.passphrase,
            'created_at': ssh_key.created_at
        }
    
    def delete_ssh_key(self, key_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete SSH key"""
        ssh_key = self.get_ssh_key_by_id(key_id)
        if not ssh_key or ssh_key.user_id != user_id:
            return False
        
        self.db.delete(ssh_key)
        self.db.commit()
        return True
    
    # Credential methods
    def get_credential_by_id(self, credential_id: uuid.UUID) -> Optional[Credential]:
        """Get credential by ID"""
        return self.db.query(Credential).filter(Credential.id == credential_id).first()
    
    def get_credential_by_name(self, name: str, user_id: uuid.UUID) -> Optional[Credential]:
        """Get credential by name for a specific user"""
        return self.db.query(Credential).filter(
            Credential.name == name, 
            Credential.user_id == user_id
        ).first()
    
    def get_user_credentials(self, user_id: uuid.UUID) -> List[Credential]:
        """Get all credentials for a user"""
        return self.db.query(Credential).filter(Credential.user_id == user_id).all()
    
    def create_credential(self, credential_data: CredentialCreate, user_id: uuid.UUID) -> Credential:
        """Create a new credential"""
        # Check if credential with same name already exists for this user
        if self.get_credential_by_name(credential_data.name, user_id):
            raise ValueError("Credential with this name already exists")
        
        credential = Credential(
            name=credential_data.name,
            username=credential_data.username,
            password=credential_data.password,
            credential_type=credential_data.credential_type,
            user_id=user_id
        )
        
        self.db.add(credential)
        self.db.commit()
        self.db.refresh(credential)
        
        return credential
    
    def get_credential_data(self, credential_id: uuid.UUID, user_id: uuid.UUID) -> Optional[dict]:
        """Get credential data"""
        credential = self.get_credential_by_id(credential_id)
        if not credential or credential.user_id != user_id:
            return None
        
        return {
            'id': credential.id,
            'name': credential.name,
            'username': credential.username,
            'password': credential.password,
            'credential_type': credential.credential_type,
            'created_at': credential.created_at
        }
    
    def delete_credential(self, credential_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete credential"""
        credential = self.get_credential_by_id(credential_id)
        if not credential or credential.user_id != user_id:
            return False
        
        self.db.delete(credential)
        self.db.commit()
        return True
