from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from core.database import get_db
from modules.credentials.service import CredentialService
from modules.credentials.schemas import (
    SSHKeyCreate, SSHKeyResponse, SSHKeySafeResponse,
    CredentialCreate, CredentialResponse, CredentialSafeResponse
)
from modules.users.schemas import UserResponse
from api.middleware.auth import get_current_user

router = APIRouter()

# SSH Key routes
@router.get("/ssh-keys", response_model=List[SSHKeySafeResponse])
async def get_ssh_keys(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    credential_service = CredentialService(db)
    ssh_keys = credential_service.get_user_ssh_keys(current_user.id)
    
    # Convert to safe response (without private key and passphrase)
    safe_keys = []
    for key in ssh_keys:
        safe_keys.append({
            'id': key.id,
            'name': key.name,
            'public_key': key.public_key,
            'created_at': key.created_at
        })
    
    return safe_keys

@router.get("/ssh-keys/{key_id}", response_model=SSHKeyResponse)
async def get_ssh_key(
    key_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    credential_service = CredentialService(db)
    ssh_key_data = credential_service.get_ssh_key_data(key_id, current_user.id)
    
    if not ssh_key_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SSH key not found"
        )
    
    return ssh_key_data

@router.post("/ssh-keys", response_model=SSHKeyResponse)
async def create_ssh_key(
    key_data: SSHKeyCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    credential_service = CredentialService(db)
    
    try:
        ssh_key = credential_service.create_ssh_key(key_data, current_user.id)
        return credential_service.get_ssh_key_data(ssh_key.id, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/ssh-keys/{key_id}")
async def delete_ssh_key(
    key_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    credential_service = CredentialService(db)
    
    success = credential_service.delete_ssh_key(key_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SSH key not found"
        )
    
    return {"message": "SSH key deleted successfully"}

# Credential routes
@router.get("/credentials", response_model=List[CredentialSafeResponse])
async def get_credentials(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    credential_service = CredentialService(db)
    credentials = credential_service.get_user_credentials(current_user.id)
    
    # Convert to safe response (without sensitive data)
    safe_credentials = []
    for cred in credentials:
        safe_credentials.append({
            'id': cred.id,
            'name': cred.name,
            'credential_type': cred.credential_type,
            'created_at': cred.created_at
        })
    
    return safe_credentials

@router.get("/credentials/{credential_id}", response_model=CredentialResponse)
async def get_credential(
    credential_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    credential_service = CredentialService(db)
    credential_data = credential_service.get_credential_data(credential_id, current_user.id)
    
    if not credential_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found"
        )
    
    return credential_data

@router.post("/credentials", response_model=CredentialResponse)
async def create_credential(
    credential_data: CredentialCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    credential_service = CredentialService(db)
    
    try:
        credential = credential_service.create_credential(credential_data, current_user.id)
        return credential_service.get_credential_data(credential.id, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/credentials/{credential_id}")
async def delete_credential(
    credential_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    credential_service = CredentialService(db)
    
    success = credential_service.delete_credential(credential_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found"
        )
    
    return {"message": "Credential deleted successfully"}
