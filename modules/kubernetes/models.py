from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from core.database import Base

class KubernetesCluster(Base):
    __tablename__ = "kubernetes_clusters"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    cluster_type = Column(String(20), nullable=False)  # 'new' or 'existing'
    auth_type = Column(String(20), default='kubeconfig')  # 'kubeconfig' or 'token'
    master_nodes = Column(Integer, default=1)
    worker_nodes = Column(Integer, default=2)
    api_server = Column(Text)  # API server URL is properly stored
    kubeconfig = Column(Text)  # Stores encrypted kubeconfig or token
    status = Column(String(50), default='pending')
    description = Column(Text)
    
    # Foreign keys
    inventory_id = Column(UUID(as_uuid=True), ForeignKey('inventory.id'), nullable=True)
    playbook_id = Column(UUID(as_uuid=True), ForeignKey('playbooks.id'), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ClusterNode(Base):
    __tablename__ = "cluster_nodes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_id = Column(UUID(as_uuid=True), ForeignKey('kubernetes_clusters.id'), nullable=False)
    node_type = Column(String(20), nullable=False)  # 'master' or 'worker'
    hostname = Column(String(255), nullable=False)
    ip_address = Column(String(45))  # IPv4 or IPv6
    status = Column(String(50), default='pending')
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
