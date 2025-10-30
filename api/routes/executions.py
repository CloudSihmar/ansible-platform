from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from core.database import get_db
from modules.executions.service import ExecutionService
from modules.executions.schemas import JobExecutionResponse, ExecutionStats, JobExecutionUpdate
from modules.users.schemas import UserResponse
from api.middleware.auth import get_current_user

router = APIRouter()

@router.get("/executions", response_model=List[JobExecutionResponse])
async def get_executions(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    execution_service = ExecutionService(db)
    return execution_service.get_user_executions(current_user.id, limit)

@router.get("/executions/stats", response_model=ExecutionStats)
async def get_execution_stats(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    execution_service = ExecutionService(db)
    return execution_service.get_execution_stats(current_user.id)

@router.get("/executions/{execution_id}", response_model=JobExecutionResponse)
async def get_execution(
    execution_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    execution_service = ExecutionService(db)
    execution = execution_service.get_execution_by_id(execution_id)
    
    if not execution or execution.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    return execution

@router.get("/playbooks/{playbook_id}/executions", response_model=List[JobExecutionResponse])
async def get_playbook_executions(
    playbook_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    execution_service = ExecutionService(db)
    return execution_service.get_playbook_executions(playbook_id, current_user.id)

@router.put("/executions/{execution_id}")
async def update_execution(
    execution_id: uuid.UUID,
    update_data: JobExecutionUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    execution_service = ExecutionService(db)
    
    execution = execution_service.update_execution(execution_id, update_data, current_user.id)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    return {"message": "Execution updated successfully"}

@router.post("/executions/{execution_id}/complete")
async def complete_execution(
    execution_id: uuid.UUID,
    status: str,
    output: str = None,
    error_message: str = None,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    execution_service = ExecutionService(db)
    
    if status not in ['success', 'failed', 'cancelled']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be one of: success, failed, cancelled"
        )
    
    execution = execution_service.complete_execution(
        execution_id, status, output, error_message, current_user.id
    )
    
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    return {"message": f"Execution marked as {status}"}

@router.delete("/executions/{execution_id}")
async def delete_execution(
    execution_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    execution_service = ExecutionService(db)
    
    success = execution_service.delete_execution(execution_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    return {"message": "Execution deleted successfully"}
