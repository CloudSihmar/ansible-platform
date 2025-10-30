from pydantic import BaseModel, validator, Field, root_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import yaml

class KubernetesClusterBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Cluster name")
    cluster_type: str = Field(..., description="Cluster type: 'new' or 'existing'")
    master_nodes: int = Field(default=1, ge=0, le=5, description="Number of master nodes")
    worker_nodes: int = Field(default=2, ge=0, le=50, description="Number of worker nodes")
    inventory_id: Optional[uuid.UUID] = Field(None, description="Associated inventory ID")
    playbook_id: Optional[uuid.UUID] = Field(None, description="Associated playbook ID")

    @validator('name')
    def validate_name(cls, v):
        # Much more permissive validation - only check for empty or whitespace-only names
        if not v or not v.strip():
            raise ValueError('Cluster name cannot be empty or whitespace only')
        # Allow any characters except control characters and excessive length
        if len(v.strip()) > 100:
            raise ValueError('Cluster name must be 100 characters or less')
        return v.strip()

    @validator('cluster_type')
    def validate_cluster_type(cls, v):
        if v not in ['new', 'existing']:
            raise ValueError('Cluster type must be "new" or "existing"')
        return v

class KubernetesClusterCreate(KubernetesClusterBase):
    pass

class ExistingClusterRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Cluster name")
    auth_data: str = Field(..., description="Kubeconfig content or bearer token")
    auth_type: str = Field(..., description="Authentication type: 'kubeconfig' or 'token'")
    api_server: Optional[str] = Field(None, description="Kubernetes API server URL (required for token auth)")
    description: Optional[str] = Field(None, max_length=500, description="Cluster description")

    @root_validator(pre=True)
    def validate_all_fields(cls, values):
        auth_type = values.get('auth_type')
        auth_data = values.get('auth_data')
        api_server = values.get('api_server')

        # Validate auth_type
        if not auth_type:
            raise ValueError('Auth type is required')
        if auth_type not in ['kubeconfig', 'token']:
            raise ValueError('Auth type must be "kubeconfig" or "token"')

        # Validate auth_data
        if not auth_data or not auth_data.strip():
            raise ValueError('Authentication data cannot be empty')

        if auth_type == 'kubeconfig':
            try:
                config = yaml.safe_load(auth_data)
                if not config or 'apiVersion' not in config or 'clusters' not in config:
                    raise ValueError('Invalid kubeconfig format: missing apiVersion or clusters')
                
                clusters = config.get('clusters', [])
                if not clusters:
                    raise ValueError('Invalid kubeconfig: no clusters defined')
                
                if len(clusters) > 0:
                    cluster = clusters[0].get('cluster', {})
                    if not cluster.get('server'):
                        raise ValueError('Invalid kubeconfig: cluster server URL missing')
                        
            except yaml.YAMLError as e:
                raise ValueError(f'Invalid kubeconfig YAML format: {str(e)}')
            except Exception as e:
                raise ValueError(f'Invalid kubeconfig: {str(e)}')
                
        elif auth_type == 'token':
            token = auth_data.strip()
            if len(token) < 10:  # Reduced minimum length to be more permissive
                raise ValueError('Token appears to be invalid (too short)')
            
            if not api_server:
                raise ValueError('API server URL is required for token authentication')
            
            if api_server and not api_server.startswith(('http://', 'https://')):
                raise ValueError('API server URL must start with http:// or https://')

        return values

class KubeconfigUpload(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Cluster name")
    description: Optional[str] = Field(None, max_length=500, description="Cluster description")

class KubernetesClusterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Cluster name")
    status: Optional[str] = Field(None, description="Cluster status")
    description: Optional[str] = Field(None, max_length=500, description="Cluster description")

class KubernetesClusterResponse(KubernetesClusterBase):
    id: uuid.UUID
    user_id: uuid.UUID
    status: str
    auth_type: Optional[str] = None
    api_server: Optional[str] = None  # Include API server in response
    description: Optional[str] = None
    kubeconfig_available: bool = Field(False, description="Whether kubeconfig is available")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ClusterNodeBase(BaseModel):
    node_type: str
    hostname: str
    ip_address: Optional[str] = None
    status: str = 'pending'

class ClusterNodeResponse(ClusterNodeBase):
    id: uuid.UUID
    cluster_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

class ClusterDeploymentRequest(BaseModel):
    inventory_id: uuid.UUID
    playbook_id: uuid.UUID
    extra_vars: Optional[Dict[str, Any]] = None

class ClusterNodeSummary(BaseModel):
    total_nodes: int
    master_nodes: int
    worker_nodes: int
    nodes: List[Dict[str, Any]]
    auth_type: str
    status: str

class ClusterRefreshResponse(BaseModel):
    message: str
    data: ClusterNodeSummary

class KubeconfigValidationResponse(BaseModel):
    valid: bool
    cluster_name: Optional[str] = None
    api_server: Optional[str] = None
    auth_type: Optional[str] = None
    error: Optional[str] = None

class ClusterStatusResponse(BaseModel):
    cluster_id: uuid.UUID
    name: str
    status: str
    node_summary: Optional[ClusterNodeSummary] = None
    health_status: str = Field('unknown', description="Cluster health: healthy, warning, critical")

class ClusterDebugResponse(BaseModel):
    id: str
    name: str
    auth_type: str
    api_server: Optional[str]
    has_kubeconfig: bool
    status: str
