from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from core.database import BaseModel

class JobExecution(BaseModel):
    __tablename__ = "job_executions"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    playbook_id = Column(UUID(as_uuid=True), ForeignKey("playbooks.id"))
    inventory_id = Column(UUID(as_uuid=True), ForeignKey("inventory.id"))
    status = Column(String(50), default='running')  # running, success, failed, cancelled
    output = Column(Text)
    started_at = Column(Text, server_default=func.now())
    completed_at = Column(Text)
    error_message = Column(Text)

    def __repr__(self):
        return f"<JobExecution(id='{self.id}', status='{self.status}')>"
