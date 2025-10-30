from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import uuid
import subprocess
import tempfile
import os
import yaml

from core.database import get_db
from core.auth import get_current_user
from modules.kubernetes.service import KubernetesClusterService
from modules.kubernetes.schemas import (
    KubernetesClusterCreate, KubernetesClusterResponse, ExistingClusterRegister,
    KubernetesClusterUpdate, ClusterNodeResponse, ClusterNodeSummary,
    ClusterRefreshResponse, ClusterStatusResponse, KubeconfigValidationResponse
)

router = APIRouter()

@router.get("/clusters", response_model=List[KubernetesClusterResponse])
async def get_user_clusters(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all clusters for the current user"""
    cluster_service = KubernetesClusterService(db)
    clusters = cluster_service.get_user_clusters(current_user.id)
    return clusters

@router.post("/clusters", response_model=KubernetesClusterResponse)
async def create_cluster(
    cluster_data: KubernetesClusterCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new Kubernetes cluster deployment"""
    cluster_service = KubernetesClusterService(db)
    try:
        cluster = cluster_service.create_cluster(cluster_data, current_user.id)
        return cluster
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/clusters/register", response_model=KubernetesClusterResponse)
async def register_cluster(
    cluster_data: ExistingClusterRegister,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register an existing Kubernetes cluster"""
    cluster_service = KubernetesClusterService(db)
    try:
        cluster = cluster_service.register_existing_cluster(cluster_data, current_user.id)
        return cluster
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/clusters/register/upload", response_model=KubernetesClusterResponse)
async def register_cluster_with_upload(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    kubeconfig_file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register cluster with kubeconfig file upload"""
    cluster_service = KubernetesClusterService(db)
    
    # Validate file type
    if not kubeconfig_file.filename.endswith(('.yaml', '.yml', '.config')):
        raise HTTPException(status_code=400, detail="File must be a YAML file (.yaml, .yml, .config)")
    
    # Read the file content
    try:
        kubeconfig_content = await kubeconfig_file.read()
        kubeconfig_text = kubeconfig_content.decode('utf-8')
        
        print(f"DEBUG: Uploaded file: {kubeconfig_file.filename}")
        print(f"DEBUG: File size: {len(kubeconfig_text)} bytes")
        
        # Validate it's a proper kubeconfig
        try:
            config = yaml.safe_load(kubeconfig_text)
            
            # Basic validation
            if 'clusters' not in config or 'users' not in config:
                raise ValueError("Invalid kubeconfig: missing clusters or users section")
                
            print(f"DEBUG: ✅ Valid kubeconfig file")
            
        except yaml.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML in kubeconfig: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid kubeconfig: {str(e)}")
        
        # Test the kubeconfig immediately to ensure it works
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
                temp_file.write(kubeconfig_text)
                temp_file_path = temp_file.name
            
            # Test connectivity with a simple command
            result = subprocess.run([
                'kubectl', 'get', 'nodes', '--kubeconfig', temp_file_path, '--output', 'name'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                print(f"DEBUG: Kubeconfig test failed: {error_msg}")
                
                # Check if it's a connectivity issue vs authentication issue
                if "Unable to connect" in error_msg or "connection refused" in error_msg:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Cannot connect to cluster API server. Check network connectivity."
                    )
                elif "Forbidden" in error_msg or "Unauthorized" in error_msg:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Authentication failed: {error_msg}"
                    )
                else:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Kubeconfig is valid but cannot connect to cluster: {error_msg}"
                    )
            
            print(f"DEBUG: ✅ Kubeconfig tested successfully")
            
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=400, detail="Connection to cluster timed out after 30 seconds")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=400, detail=f"Failed to test kubeconfig: {str(e)}")
        finally:
            # Clean up temp file
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
        # Register the cluster
        cluster_data = ExistingClusterRegister(
            name=name,
            auth_data=kubeconfig_text,
            auth_type="kubeconfig",
            description=description
        )
        
        cluster = cluster_service.register_existing_cluster(cluster_data, current_user.id)
        return cluster
        
    except Exception as e:
        print(f"DEBUG: Error processing uploaded file: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@router.get("/clusters/{cluster_id}", response_model=KubernetesClusterResponse)
async def get_cluster(
    cluster_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific cluster by ID"""
    cluster_service = KubernetesClusterService(db)
    cluster = cluster_service.get_cluster_by_id(cluster_id)
    
    if not cluster or cluster.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found"
        )
    
    return cluster

@router.put("/clusters/{cluster_id}", response_model=KubernetesClusterResponse)
async def update_cluster(
    cluster_id: uuid.UUID,
    cluster_data: KubernetesClusterUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a cluster"""
    cluster_service = KubernetesClusterService(db)
    cluster = cluster_service.get_cluster_by_id(cluster_id)
    
    if not cluster or cluster.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found"
        )
    
    # Update fields if provided
    if cluster_data.name is not None:
        cluster.name = cluster_data.name
    if cluster_data.status is not None:
        cluster.status = cluster_data.status
    if cluster_data.description is not None:
        cluster.description = cluster_data.description
    
    db.commit()
    db.refresh(cluster)
    return cluster

@router.delete("/clusters/{cluster_id}")
async def delete_cluster(
    cluster_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a cluster"""
    cluster_service = KubernetesClusterService(db)
    success = cluster_service.delete_cluster(cluster_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found"
        )
    
    return {"message": "Cluster deleted successfully"}

@router.get("/clusters/{cluster_id}/nodes", response_model=List[ClusterNodeResponse])
async def get_cluster_nodes(
    cluster_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all nodes for a cluster"""
    cluster_service = KubernetesClusterService(db)
    
    # Check if user has access to this cluster
    cluster = cluster_service.get_cluster_by_id(cluster_id)
    if not cluster or cluster.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found"
        )
    
    nodes = cluster_service.get_cluster_nodes(cluster_id)
    return nodes

@router.get("/clusters/{cluster_id}/nodes/summary", response_model=ClusterNodeSummary)
async def get_cluster_node_summary(
    cluster_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get cluster node summary (master/worker counts) from actual cluster"""
    cluster_service = KubernetesClusterService(db)
    
    # Check if user has access to this cluster
    cluster = cluster_service.get_cluster_by_id(cluster_id)
    if not cluster or cluster.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found"
        )
    
    if not cluster.kubeconfig:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cluster kubeconfig not available"
        )
    
    summary = cluster_service.get_cluster_node_summary(cluster_id, current_user.id)
    
    if "error" in summary:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=summary["error"]
        )
    
    return summary

@router.post("/clusters/{cluster_id}/nodes/refresh", response_model=ClusterRefreshResponse)
async def refresh_cluster_nodes(
    cluster_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Refresh cluster nodes from actual Kubernetes cluster"""
    cluster_service = KubernetesClusterService(db)
    
    # Check if user has access to this cluster
    cluster = cluster_service.get_cluster_by_id(cluster_id)
    if not cluster or cluster.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found"
        )
    
    result = cluster_service.refresh_cluster_nodes(cluster_id, current_user.id)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )
    
    return {"message": "Cluster nodes refreshed successfully", "data": result}

@router.post("/clusters/{cluster_id}/refresh", response_model=Dict[str, Any])
async def refresh_cluster(
    cluster_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Refresh cluster data including node counts"""
    cluster_service = KubernetesClusterService(db)
    
    # Check if user has access to this cluster
    cluster = cluster_service.get_cluster_by_id(cluster_id)
    if not cluster or cluster.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found"
        )
    
    result = cluster_service.refresh_cluster_nodes(cluster_id, current_user.id)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )
    
    return {"message": "Cluster refreshed successfully", "data": result}

@router.get("/clusters/{cluster_id}/health", response_model=ClusterStatusResponse)
async def get_cluster_health(
    cluster_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive cluster health status"""
    cluster_service = KubernetesClusterService(db)
    
    try:
        health_status = cluster_service.get_cluster_health(cluster_id, current_user.id)
        return health_status
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.post("/clusters/validate-kubeconfig", response_model=KubeconfigValidationResponse)
async def validate_kubeconfig(
    kubeconfig_data: Dict[str, str],
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Validate kubeconfig content"""
    cluster_service = KubernetesClusterService(db)
    
    kubeconfig_content = kubeconfig_data.get('kubeconfig', '')
    auth_type = kubeconfig_data.get('auth_type', 'kubeconfig')
    
    if not kubeconfig_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kubeconfig content is required"
        )
    
    validation_result = cluster_service.validate_kubeconfig(kubeconfig_content, auth_type)
    return validation_result

@router.get("/clusters/{cluster_id}/kubeconfig")
async def get_cluster_kubeconfig(
    cluster_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get decrypted kubeconfig for a cluster"""
    cluster_service = KubernetesClusterService(db)
    
    # Check if user has access to this cluster
    cluster = cluster_service.get_cluster_by_id(cluster_id)
    if not cluster or cluster.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found"
        )
    
    kubeconfig = cluster_service.get_cluster_kubeconfig(cluster_id, current_user.id)
    
    if not kubeconfig:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kubeconfig not available for this cluster"
        )
    
    return {"kubeconfig": kubeconfig}

@router.get("/{cluster_id}/debug")
async def debug_cluster(
    cluster_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Debug cluster data"""
    cluster_service = KubernetesClusterService(db)
    
    debug_data = cluster_service.debug_cluster_data(cluster_id, current_user.id)
    if "error" in debug_data:
        raise HTTPException(status_code=404, detail=debug_data["error"])
    
    return debug_data

@router.post("/{cluster_id}/fix-api-server")
async def fix_cluster_api_server(
    cluster_id: uuid.UUID,
    api_server: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Temporary endpoint to fix missing API server"""
    cluster_service = KubernetesClusterService(db)
    
    cluster = cluster_service.fix_cluster_api_server(cluster_id, api_server, current_user.id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    return cluster
