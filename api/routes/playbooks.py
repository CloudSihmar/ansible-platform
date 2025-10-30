from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from core.database import get_db
from modules.playbooks.service import PlaybookService
from modules.inventory.service import InventoryService
from modules.credentials.service import CredentialService
from modules.executions.service import ExecutionService
from modules.playbooks.schemas import PlaybookCreate, PlaybookUpdate, PlaybookResponse, PlaybookExecutionRequest
from modules.executions.schemas import JobExecutionCreate  # ADD THIS IMPORT
from modules.users.schemas import UserResponse
from api.middleware.auth import get_current_user
from utils.ansible_runner import ansible_runner

router = APIRouter()

@router.get("/playbooks", response_model=List[PlaybookResponse])
async def get_playbooks(
    playbook_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    playbook_service = PlaybookService(db)
    
    if playbook_type:
        return playbook_service.get_user_playbooks(current_user.id, playbook_type)
    else:
        return playbook_service.get_user_playbooks(current_user.id)

@router.get("/playbooks/kubernetes", response_model=List[PlaybookResponse])
async def get_kubernetes_playbooks(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    playbook_service = PlaybookService(db)
    return playbook_service.get_kubernetes_playbooks(current_user.id)

@router.get("/playbooks/{playbook_id}", response_model=PlaybookResponse)
async def get_playbook(
    playbook_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    playbook_service = PlaybookService(db)
    playbook = playbook_service.get_playbook_by_id(playbook_id)
    
    if not playbook or playbook.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playbook not found"
        )
    
    return playbook

@router.post("/playbooks", response_model=PlaybookResponse)
async def create_playbook(
    playbook_data: PlaybookCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    playbook_service = PlaybookService(db)
    
    try:
        playbook = playbook_service.create_playbook(playbook_data, current_user.id)
        return playbook
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/playbooks/{playbook_id}", response_model=PlaybookResponse)
async def update_playbook(
    playbook_id: uuid.UUID,
    playbook_data: PlaybookUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    playbook_service = PlaybookService(db)
    
    try:
        playbook = playbook_service.update_playbook(playbook_id, playbook_data, current_user.id)
        if not playbook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playbook not found"
            )
        return playbook
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/playbooks/{playbook_id}")
async def delete_playbook(
    playbook_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    playbook_service = PlaybookService(db)
    
    success = playbook_service.delete_playbook(playbook_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playbook not found"
        )
    
    return {"message": "Playbook deleted successfully"}

@router.post("/playbooks/{playbook_id}/execute")
async def execute_playbook(
    playbook_id: uuid.UUID,
    execution_data: PlaybookExecutionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """Execute a playbook with the provided inventory and variables"""
    playbook_service = PlaybookService(db)
    inventory_service = InventoryService(db)
    credential_service = CredentialService(db)
    execution_service = ExecutionService(db)
    
    # Verify playbook exists and user has access
    playbook = playbook_service.get_playbook_by_id(playbook_id)
    if not playbook or playbook.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playbook not found"
        )
    
    # Verify inventory exists and user has access
    inventory = inventory_service.get_inventory_by_id(execution_data.inventory_id)
    if not inventory or inventory.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found"
        )
    
    # FIX: Create the correct schema for execution service
    job_execution_data = JobExecutionCreate(
        playbook_id=playbook_id,  # Use the playbook_id from URL
        inventory_id=execution_data.inventory_id
    )
    
    # Create execution record with correct schema
    execution = execution_service.create_execution(job_execution_data, current_user.id)
    
    # Start background execution
    background_tasks.add_task(
        execute_playbook_background,
        db,
        playbook.id,
        inventory.id,
        execution.id,
        current_user.id,
        execution_data.extra_vars or {}
    )
    
    return {
        "message": "Playbook execution started",
        "execution_id": str(execution.id),
        "playbook_id": str(playbook_id),
        "inventory_id": str(execution_data.inventory_id),
        "status": "running"
    }

async def execute_playbook_background(
    db: Session,
    playbook_id: uuid.UUID,
    inventory_id: uuid.UUID,
    execution_id: uuid.UUID,
    user_id: uuid.UUID,
    extra_vars: dict
):
    """Background task to execute playbook"""
    playbook_service = PlaybookService(db)
    inventory_service = InventoryService(db)
    execution_service = ExecutionService(db)
    credential_service = CredentialService(db)
    
    try:
        # Get fresh database session for background task
        from core.database import SessionLocal
        db = SessionLocal()
        
        # Get playbook and inventory data
        playbook = playbook_service.get_playbook_by_id(playbook_id)
        inventory = inventory_service.get_inventory_by_id(inventory_id)
        
        if not playbook or not inventory:
            execution_service.complete_execution(
                execution_id, "failed", 
                error_message="Playbook or inventory not found"
            )
            return
        
        # Get SSH keys for this user (use first available)
        ssh_keys = credential_service.get_user_ssh_keys(user_id)
        ssh_private_key = None
        if ssh_keys:
            # For now, use the first SSH key
            ssh_key_data = credential_service.get_ssh_key_data(ssh_keys[0].id, user_id)
            if ssh_key_data:
                ssh_private_key = ssh_key_data['private_key']
        
        # Execute playbook
        return_code, stdout, stderr = ansible_runner.run_playbook(
            playbook_content=playbook.playbook_content or "",
            inventory_content=inventory.content,
            ssh_private_key=ssh_private_key,
            extra_vars=extra_vars
        )
        
        # Update execution record
        if return_code == 0:
            execution_service.complete_execution(
                execution_id, "success", output=stdout
            )
        else:
            execution_service.complete_execution(
                execution_id, "failed", output=stdout, error_message=stderr
            )
            
    except Exception as e:
        # Update execution record with error
        execution_service.complete_execution(
            execution_id, "failed", error_message=f"Execution error: {str(e)}"
        )
    finally:
        db.close()
