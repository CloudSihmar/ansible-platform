from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

from .models import JobExecution
from .schemas import JobExecutionCreate, JobExecutionUpdate, ExecutionStats

class ExecutionService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_execution_by_id(self, execution_id: uuid.UUID) -> Optional[JobExecution]:
        """Get execution by ID"""
        return self.db.query(JobExecution).filter(JobExecution.id == execution_id).first()
    
    def get_user_executions(self, user_id: uuid.UUID, limit: int = 50) -> List[JobExecution]:
        """Get all executions for a user"""
        return self.db.query(JobExecution).filter(
            JobExecution.user_id == user_id
        ).order_by(JobExecution.started_at.desc()).limit(limit).all()
    
    def get_playbook_executions(self, playbook_id: uuid.UUID, user_id: uuid.UUID) -> List[JobExecution]:
        """Get all executions for a specific playbook"""
        return self.db.query(JobExecution).filter(
            JobExecution.playbook_id == playbook_id,
            JobExecution.user_id == user_id
        ).order_by(JobExecution.started_at.desc()).all()
    
    def create_execution(self, execution_data: JobExecutionCreate, user_id: uuid.UUID) -> JobExecution:
        """Create a new execution record"""
        execution = JobExecution(
            playbook_id=execution_data.playbook_id,
            inventory_id=execution_data.inventory_id,
            user_id=user_id,
            status='running'
        )
        
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        
        return execution
    
    def update_execution(self, execution_id: uuid.UUID, update_data: JobExecutionUpdate, user_id: uuid.UUID) -> Optional[JobExecution]:
        """Update execution status and output"""
        execution = self.get_execution_by_id(execution_id)
        if not execution or execution.user_id != user_id:
            return None
        
        update_dict = update_data.dict(exclude_unset=True)
        
        for field, value in update_dict.items():
            setattr(execution, field, value)
        
        self.db.commit()
        self.db.refresh(execution)
        
        return execution
    
    def complete_execution(self, execution_id: uuid.UUID, status: str, output: str = None, error_message: str = None, user_id: uuid.UUID = None) -> Optional[JobExecution]:
        """Mark execution as completed"""
        execution = self.get_execution_by_id(execution_id)
        if not execution:
            return None
        
        # If user_id is provided, verify ownership
        if user_id and execution.user_id != user_id:
            return None
        
        execution.status = status
        execution.completed_at = datetime.utcnow()
        
        if output is not None:
            execution.output = output
        
        if error_message is not None:
            execution.error_message = error_message
        
        self.db.commit()
        self.db.refresh(execution)
        
        return execution
    
    def get_execution_stats(self, user_id: uuid.UUID) -> ExecutionStats:
        """Get execution statistics for a user"""
        executions = self.get_user_executions(user_id, limit=1000)  # Get more for stats
        
        total = len(executions)
        successful = len([e for e in executions if e.status == 'success'])
        failed = len([e for e in executions if e.status == 'failed'])
        running = len([e for e in executions if e.status == 'running'])
        
        # Calculate average duration for completed executions
        completed_executions = [e for e in executions if e.completed_at and e.started_at]
        durations = []
        
        for exec in completed_executions:
            if exec.completed_at and exec.started_at:
                # Convert string timestamps to datetime objects if needed
                if isinstance(exec.started_at, str):
                    started = datetime.fromisoformat(exec.started_at.replace('Z', '+00:00'))
                else:
                    started = exec.started_at
                
                if isinstance(exec.completed_at, str):
                    completed = datetime.fromisoformat(exec.completed_at.replace('Z', '+00:00'))
                else:
                    completed = exec.completed_at
                
                duration = (completed - started).total_seconds()
                durations.append(duration)
        
        average_duration = sum(durations) / len(durations) if durations else None
        
        return ExecutionStats(
            total_executions=total,
            successful_executions=successful,
            failed_executions=failed,
            running_executions=running,
            average_duration=average_duration
        )
    
    def delete_execution(self, execution_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete execution"""
        execution = self.get_execution_by_id(execution_id)
        if not execution or execution.user_id != user_id:
            return False
        
        self.db.delete(execution)
        self.db.commit()
        return True
