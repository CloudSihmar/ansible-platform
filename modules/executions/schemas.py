from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class JobExecutionBase(BaseModel):
    playbook_id: Optional[uuid.UUID] = None
    inventory_id: Optional[uuid.UUID] = None
    status: str = 'running'
    output: Optional[str] = None
    error_message: Optional[str] = None

class JobExecutionCreate(BaseModel):
    playbook_id: uuid.UUID
    inventory_id: uuid.UUID
    extra_vars: Optional[Dict[str, Any]] = None

class JobExecutionUpdate(BaseModel):
    status: Optional[str] = None
    output: Optional[str] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None

class JobExecutionResponse(JobExecutionBase):
    id: uuid.UUID
    user_id: uuid.UUID
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ExecutionStats(BaseModel):
    total_executions: int
    successful_executions: int
    failed_executions: int
    running_executions: int
    average_duration: Optional[float] = None
