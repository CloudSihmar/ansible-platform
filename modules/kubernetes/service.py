from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import uuid
import yaml
import subprocess
import tempfile
import os
import json
import base64
import logging
from pathlib import Path

from .models import KubernetesCluster, ClusterNode
from .schemas import (
    KubernetesClusterCreate, ExistingClusterRegister, KubernetesClusterUpdate, 
    ClusterDeploymentRequest, KubeconfigValidationResponse, ClusterStatusResponse,
    ClusterNodeSummary
)
from utils.encryption import encryption_manager

logger = logging.getLogger(__name__)

class KubernetesClusterService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_cluster_by_id(self, cluster_id: uuid.UUID) -> Optional[KubernetesCluster]:
        """Get cluster by ID"""
        return self.db.query(KubernetesCluster).filter(KubernetesCluster.id == cluster_id).first()
    
    def get_cluster_by_name(self, name: str, user_id: uuid.UUID) -> Optional[KubernetesCluster]:
        """Get cluster by name for a specific user"""
        return self.db.query(KubernetesCluster).filter(
            KubernetesCluster.name == name, 
            KubernetesCluster.user_id == user_id
        ).first()
    
    def get_user_clusters(self, user_id: uuid.UUID) -> List[KubernetesCluster]:
        """Get all clusters for a user"""
        return self.db.query(KubernetesCluster).filter(KubernetesCluster.user_id == user_id).all()
    
    def create_cluster(self, cluster_data: KubernetesClusterCreate, user_id: uuid.UUID) -> KubernetesCluster:
        """Create a new cluster deployment"""
        # Check if cluster with same name already exists for this user
        if self.get_cluster_by_name(cluster_data.name, user_id):
            raise ValueError("Cluster with this name already exists")
        
        cluster = KubernetesCluster(
            name=cluster_data.name,
            cluster_type=cluster_data.cluster_type,
            master_nodes=cluster_data.master_nodes,
            worker_nodes=cluster_data.worker_nodes,
            inventory_id=cluster_data.inventory_id,
            playbook_id=cluster_data.playbook_id,
            user_id=user_id,
            status='creating'
        )
        
        self.db.add(cluster)
        self.db.commit()
        self.db.refresh(cluster)
        
        return cluster
    
    def register_existing_cluster(self, cluster_data: ExistingClusterRegister, user_id: uuid.UUID) -> KubernetesCluster:
        """Register an existing Kubernetes cluster"""
        # Check if cluster with same name already exists for this user
        if self.get_cluster_by_name(cluster_data.name, user_id):
            raise ValueError("Cluster with this name already exists")
        
        # Extract API server for both auth types
        api_server = None
        if cluster_data.auth_type == 'token':
            # For token auth, use the provided API server
            api_server = cluster_data.api_server
            logger.info(f"Using provided API server for token auth: {api_server}")
        elif cluster_data.auth_type == 'kubeconfig':
            # Extract API server from kubeconfig
            try:
                config = yaml.safe_load(cluster_data.auth_data)
                clusters = config.get('clusters', [])
                if clusters:
                    api_server = clusters[0].get('cluster', {}).get('server')
                    logger.info(f"Extracted API server from kubeconfig: {api_server}")
            except Exception as e:
                logger.warning(f"Could not extract API server from kubeconfig: {e}")
        
        # Validate that API server is set for token auth
        if cluster_data.auth_type == 'token' and not api_server:
            raise ValueError("API server URL is required for token authentication")
        
        # Determine authentication type and encrypt accordingly
        auth_type = cluster_data.auth_type
        
        try:
            encrypted_auth_data = encryption_manager.encrypt_data(cluster_data.auth_data)
            logger.info("Successfully encrypted cluster authentication data")
        except Exception as e:
            logger.error(f"Failed to encrypt cluster data: {e}")
            raise ValueError(f"Failed to secure cluster credentials: {e}")
        
        # Extract cluster info for description
        cluster_info = self._extract_cluster_info(cluster_data.auth_data, auth_type, api_server)
        
        # Create cluster with ALL required fields
        cluster = KubernetesCluster(
            name=cluster_data.name,
            cluster_type='existing',
            auth_type=auth_type,
            master_nodes=0,  # Will be detected from cluster
            worker_nodes=0,  # Will be detected from cluster
            api_server=api_server,  # Store the API server URL
            kubeconfig=encrypted_auth_data,
            description=cluster_data.description or cluster_info.get('description', ''),
            user_id=user_id,
            status='registered'
        )
        
        logger.info(f"Creating cluster '{cluster_data.name}' with API server: {api_server}")
        
        self.db.add(cluster)
        self.db.commit()
        self.db.refresh(cluster)
        
        # Immediately try to get actual node counts after registration
        try:
            logger.info(f"Attempting to get initial node counts for cluster {cluster.id}")
            summary = self.get_cluster_node_summary(cluster.id, user_id)
            if "error" not in summary:
                logger.info(f"Initial node counts - Masters: {summary['master_nodes']}, Workers: {summary['worker_nodes']}")
        except Exception as e:
            logger.warning(f"Failed to get initial node counts: {e}")
        
        return cluster
    
    def _extract_cluster_info(self, auth_data: str, auth_type: str, api_server: Optional[str] = None) -> Dict[str, str]:
        """Extract cluster information from auth data"""
        info = {}
        
        try:
            if auth_type == 'kubeconfig':
                config = yaml.safe_load(auth_data)
                
                # Get current context
                current_context = config.get('current-context', '')
                contexts = config.get('contexts', [])
                
                for context in contexts:
                    if context.get('name') == current_context:
                        cluster_name = context.get('context', {}).get('cluster', 'unknown')
                        info['description'] = f"Registered cluster: {cluster_name}"
                        break
                
                # Get API server from first cluster
                clusters = config.get('clusters', [])
                if clusters:
                    server = clusters[0].get('cluster', {}).get('server', 'unknown')
                    info['api_server'] = server
                    
            elif auth_type == 'token':
                info['description'] = f"Token-authenticated cluster: {api_server}"
                info['api_server'] = api_server
                
        except Exception as e:
            info['description'] = "Registered Kubernetes cluster"
            
        return info
    
    def validate_kubeconfig(self, kubeconfig_content: str, auth_type: str = 'kubeconfig') -> KubeconfigValidationResponse:
        """Validate kubeconfig content or token"""
        try:
            if auth_type == 'kubeconfig':
                config = yaml.safe_load(kubeconfig_content)
                
                if not config or 'apiVersion' not in config:
                    return KubeconfigValidationResponse(
                        valid=False,
                        error="Invalid kubeconfig: missing apiVersion"
                    )
                
                # Check essential sections
                required_sections = ['clusters', 'contexts', 'users']
                missing_sections = [section for section in required_sections if section not in config]
                
                if missing_sections:
                    return KubeconfigValidationResponse(
                        valid=False,
                        error=f"Missing required sections: {', '.join(missing_sections)}"
                    )
                
                # Extract cluster info
                current_context = config.get('current-context', '')
                clusters = config.get('clusters', [])
                api_server = clusters[0].get('cluster', {}).get('server', '') if clusters else ''
                
                return KubeconfigValidationResponse(
                    valid=True,
                    cluster_name=current_context,
                    api_server=api_server,
                    auth_type='kubeconfig'
                )
            
            elif auth_type == 'token':
                # Basic token validation
                token = kubeconfig_content.strip()
                if len(token) < 50:
                    return KubeconfigValidationResponse(
                        valid=False,
                        error="Token appears to be invalid (too short)"
                    )
                
                return KubeconfigValidationResponse(
                    valid=True,
                    auth_type='token'
                )
            else:
                return KubeconfigValidationResponse(
                    valid=False,
                    error=f"Unsupported auth type: {auth_type}"
                )
                
        except yaml.YAMLError as e:
            if auth_type == 'kubeconfig':
                return KubeconfigValidationResponse(
                    valid=False,
                    error=f"Invalid YAML format: {str(e)}"
                )
            else:
                # For tokens, YAML errors are expected
                return KubeconfigValidationResponse(
                    valid=True,
                    auth_type='token'
                )
        except Exception as e:
            return KubeconfigValidationResponse(
                valid=False,
                error=f"Validation error: {str(e)}"
            )
    
    def get_cluster_auth_data(self, cluster_id: uuid.UUID, user_id: uuid.UUID) -> tuple[Optional[str], Optional[str]]:
        """Get decrypted authentication data and type for a cluster with graceful error handling"""
        cluster = self.get_cluster_by_id(cluster_id)
        if not cluster or cluster.user_id != user_id:
            return None, None
        
        if not cluster.kubeconfig:
            return None, None
        
        try:
            auth_data = encryption_manager.decrypt_data(cluster.kubeconfig)
            return auth_data, cluster.auth_type
        except Exception as e:
            logger.error(f"Failed to decrypt kubeconfig for cluster {cluster_id}: {e}")
            # Don't change cluster status automatically in production
            # Let the API handle this gracefully
            return None, None
    
    def _get_kubectl_nodes(self, auth_data: str, auth_type: str, api_server: Optional[str] = None) -> List[Dict[str, Any]]:
        """Execute kubectl get nodes command using appropriate authentication"""
        if auth_type == 'kubeconfig':
            return self._get_nodes_with_kubeconfig(auth_data)
        elif auth_type == 'token':
            # Use the provided API server for token auth
            if not api_server:
                raise ValueError("API server URL is required for token authentication")
            return self._get_nodes_with_token(auth_data, api_server)
        else:
            raise ValueError(f"Unsupported authentication type: {auth_type}")
    
    def _get_nodes_with_kubeconfig(self, kubeconfig: str) -> List[Dict[str, Any]]:
        """Get nodes using kubeconfig file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            temp_file.write(kubeconfig)
            temp_file_path = temp_file.name
        
        try:
            env = os.environ.copy()
            env['KUBECONFIG'] = temp_file_path
            
            result = subprocess.run([
                'kubectl', 'get', 'nodes', 
                '-o', 'json',
                '--kubeconfig', temp_file_path
            ], capture_output=True, text=True, env=env, timeout=30)
            
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                if "Unable to connect to the server" in error_msg:
                    raise Exception(f"Unable to connect to Kubernetes API: {error_msg}")
                elif "Forbidden" in error_msg or "Unauthorized" in error_msg:
                    raise Exception(f"Authentication failed: {error_msg}")
                else:
                    raise Exception(f"kubectl error: {error_msg}")
            
            return self._parse_nodes_json(result.stdout)
            
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def _get_nodes_with_token(self, token: str, api_server: str) -> List[Dict[str, Any]]:
        """Get nodes using bearer token"""
        kubeconfig = self._create_kubeconfig_with_token(token, api_server)
        return self._get_nodes_with_kubeconfig(kubeconfig)
    
    def _create_kubeconfig_with_token(self, token: str, api_server: str) -> str:
        """Create a minimal kubeconfig using bearer token"""
        # Better handling of TLS verification
        cluster_config = {
            'server': api_server,
        }
        
        # Add TLS verification if it's an HTTPS URL
        if api_server.startswith('https://'):
            cluster_config['insecure-skip-tls-verify'] = True  # Make configurable
        
        kubeconfig = {
            'apiVersion': 'v1',
            'kind': 'Config',
            'clusters': [
                {
                    'name': 'token-cluster',
                    'cluster': cluster_config
                }
            ],
            'users': [
                {
                    'name': 'token-user',
                    'user': {
                        'token': token
                    }
                }
            ],
            'contexts': [
                {
                    'name': 'token-context',
                    'context': {
                        'cluster': 'token-cluster',
                        'user': 'token-user',
                        'namespace': 'default'
                    }
                }
            ],
            'current-context': 'token-context'
        }
        
        return yaml.dump(kubeconfig)
    
    def get_cluster_node_summary(self, cluster_id: uuid.UUID, user_id: uuid.UUID) -> Dict[str, Any]:
        """Get cluster node summary (master/worker counts) by querying actual cluster"""
        cluster = self.get_cluster_by_id(cluster_id)
        if not cluster or cluster.user_id != user_id:
            return {"error": "Cluster not found or access denied"}
        
        auth_data, auth_type = self.get_cluster_auth_data(cluster_id, user_id)
        if not auth_data:
            return {
                "error": "Cluster authentication data unavailable. The cluster may need to be re-registered due to encryption key changes.",
                "needs_re_registration": True
            }
        
        try:
            # Use the stored API server from the cluster record
            api_server = cluster.api_server
            logger.debug(f"Using API server from cluster: {api_server}")
            logger.debug(f"Auth type: {auth_type}")
            logger.debug(f"Auth data available: {len(auth_data) if auth_data else 0} chars")
            
            # Validate API server for token auth
            if auth_type == 'token' and not api_server:
                return {"error": "API server URL is required for token authentication but not found in cluster record"}
            
            # Get nodes from actual cluster
            nodes_info = self._get_kubectl_nodes(auth_data, auth_type, api_server)
            logger.info(f"Retrieved {len(nodes_info)} nodes from cluster {cluster_id}")
            
            # Count master and worker nodes
            master_count = sum(1 for node in nodes_info if self._is_master_node(node))
            worker_count = len(nodes_info) - master_count
            
            logger.info(f"Node counts for cluster {cluster_id} - Masters: {master_count}, Workers: {worker_count}")
            
            # Update cluster record with actual counts
            if cluster:
                cluster.master_nodes = master_count
                cluster.worker_nodes = worker_count
                cluster.status = 'registered'
                self.db.commit()
            
            return {
                "total_nodes": len(nodes_info),
                "master_nodes": master_count,
                "worker_nodes": worker_count,
                "nodes": nodes_info,
                "auth_type": auth_type,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error getting cluster nodes for {cluster_id}: {str(e)}")
            # Return current database values with error info
            return {
                "total_nodes": cluster.master_nodes + cluster.worker_nodes,
                "master_nodes": cluster.master_nodes,
                "worker_nodes": cluster.worker_nodes,
                "nodes": [],
                "auth_type": auth_type,
                "status": "error",
                "error": f"Failed to connect to cluster: {str(e)}"
            }
    
    def _extract_api_server_from_auth(self, auth_data: str, auth_type: str) -> Optional[str]:
        """Extract API server URL from auth data"""
        if auth_type == 'kubeconfig':
            try:
                config = yaml.safe_load(auth_data)
                clusters = config.get('clusters', [])
                if clusters:
                    return clusters[0].get('cluster', {}).get('server')
            except:
                pass
        return None
    
    def _parse_nodes_json(self, json_output: str) -> List[Dict[str, Any]]:
        """Parse kubectl get nodes JSON output"""
        try:
            nodes_data = json.loads(json_output)
            
            nodes_info = []
            for node in nodes_data.get('items', []):
                # Extract node IP
                ip_address = "unknown"
                addresses = node['status'].get('addresses', [])
                for addr in addresses:
                    if addr['type'] == 'InternalIP':
                        ip_address = addr['address']
                        break
                
                # Extract node roles from labels
                roles = []
                labels = node['metadata'].get('labels', {})
                for label_key, label_value in labels.items():
                    if label_key.startswith('node-role.kubernetes.io/'):
                        role = label_key.replace('node-role.kubernetes.io/', '')
                        roles.append(role)
                
                # If no roles found, check for older master label
                if not roles and labels.get('kubernetes.io/role') == 'master':
                    roles.append('master')
                
                node_info = {
                    'name': node['metadata']['name'],
                    'status': next((condition['status'] for condition in node['status']['conditions'] 
                                  if condition['type'] == 'Ready'), 'Unknown'),
                    'roles': roles,
                    'version': node['status']['nodeInfo']['kubeletVersion'],
                    'os': node['status']['nodeInfo']['operatingSystem'],
                    'architecture': node['status']['nodeInfo']['architecture'],
                    'creation_timestamp': node['metadata']['creationTimestamp'],
                    'ip_address': ip_address,
                    'labels': labels
                }
                nodes_info.append(node_info)
            
            return nodes_info
        except Exception as e:
            logger.error(f"Error parsing nodes JSON: {e}")
            logger.debug(f"JSON output: {json_output[:500]}...")  # First 500 chars for debugging
            raise e
    
    def _is_master_node(self, node_info: Dict[str, Any]) -> bool:
        """Check if node is a master/control-plane node"""
        roles = node_info.get('roles', [])
        # Check for both control-plane and master roles
        return 'control-plane' in roles or 'master' in roles
    
    def update_cluster_status(self, cluster_id: uuid.UUID, status: str, user_id: uuid.UUID) -> Optional[KubernetesCluster]:
        """Update cluster status"""
        cluster = self.get_cluster_by_id(cluster_id)
        if not cluster or cluster.user_id != user_id:
            return None
        
        cluster.status = status
        self.db.commit()
        self.db.refresh(cluster)
        
        return cluster
    
    def delete_cluster(self, cluster_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete cluster"""
        cluster = self.get_cluster_by_id(cluster_id)
        if not cluster or cluster.user_id != user_id:
            return False
        
        # Also delete associated nodes
        nodes = self.db.query(ClusterNode).filter(ClusterNode.cluster_id == cluster_id).all()
        for node in nodes:
            self.db.delete(node)
        
        self.db.delete(cluster)
        self.db.commit()
        return True
    
    def add_cluster_node(self, cluster_id: uuid.UUID, node_data: Dict[str, Any]) -> ClusterNode:
        """Add a node to a cluster"""
        node = ClusterNode(
            cluster_id=cluster_id,
            node_type=node_data['node_type'],
            hostname=node_data['hostname'],
            ip_address=node_data.get('ip_address'),
            status=node_data.get('status', 'pending')
        )
        
        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)
        
        return node
    
    def get_cluster_nodes(self, cluster_id: uuid.UUID) -> List[ClusterNode]:
        """Get all nodes for a cluster"""
        return self.db.query(ClusterNode).filter(ClusterNode.cluster_id == cluster_id).all()
    
    def _parse_kubeconfig_nodes(self, cluster_id: uuid.UUID, auth_data: str, auth_type: str):
        """Parse cluster to extract node information and sync with cluster"""
        try:
            # Get actual node information from cluster
            # Note: This creates a circular dependency, so we need to handle it differently
            # For now, we'll skip automatic node parsing during registration
            # Nodes will be populated when user explicitly requests node summary
            pass
                
        except Exception as e:
            logger.error(f"Error parsing cluster nodes: {e}")
    
    def refresh_cluster_nodes(self, cluster_id: uuid.UUID, user_id: uuid.UUID) -> Dict[str, Any]:
        """Refresh cluster nodes from actual Kubernetes cluster"""
        logger.info(f"Refreshing nodes for cluster {cluster_id}")
        result = self.get_cluster_node_summary(cluster_id, user_id)
        
        if "error" in result:
            return {"error": result["error"]}
        else:
            return {
                "message": "Cluster nodes refreshed successfully",
                "data": result
            }
    
    def get_cluster_health(self, cluster_id: uuid.UUID, user_id: uuid.UUID) -> ClusterStatusResponse:
        """Get comprehensive cluster health status"""
        cluster = self.get_cluster_by_id(cluster_id)
        if not cluster or cluster.user_id != user_id:
            raise ValueError("Cluster not found or access denied")
        
        # Get node summary
        node_summary_data = self.get_cluster_node_summary(cluster_id, user_id)
        node_summary = None
        health_status = "unknown"
        
        if "error" not in node_summary_data:
            node_summary = ClusterNodeSummary(**node_summary_data)
            
            # Determine health status based on node conditions
            ready_nodes = sum(1 for node in node_summary_data.get('nodes', []) 
                            if node.get('status') == 'True')
            total_nodes = node_summary_data.get('total_nodes', 0)
            
            if total_nodes == 0:
                health_status = "critical"
            elif ready_nodes == total_nodes:
                health_status = "healthy"
            elif ready_nodes >= total_nodes * 0.5:
                health_status = "warning"
            else:
                health_status = "critical"
        
        return ClusterStatusResponse(
            cluster_id=cluster_id,
            name=cluster.name,
            status=cluster.status,
            node_summary=node_summary,
            health_status=health_status
        )
    
    def fix_cluster_api_server(self, cluster_id: uuid.UUID, api_server: str, user_id: uuid.UUID) -> Optional[KubernetesCluster]:
        """Fix missing API server for an existing cluster"""
        cluster = self.get_cluster_by_id(cluster_id)
        if not cluster or cluster.user_id != user_id:
            return None
        
        logger.info(f"Updating cluster {cluster_id} with API server: {api_server}")
        cluster.api_server = api_server
        self.db.commit()
        self.db.refresh(cluster)
        
        return cluster
    
    def debug_cluster_data(self, cluster_id: uuid.UUID, user_id: uuid.UUID) -> Dict[str, Any]:
        """Debug method to check cluster data"""
        cluster = self.get_cluster_by_id(cluster_id)
        if not cluster or cluster.user_id != user_id:
            return {"error": "Cluster not found"}
        
        # Try to get live node data for debugging
        auth_data, auth_type = self.get_cluster_auth_data(cluster_id, user_id)
        live_data_available = False
        if auth_data:
            try:
                nodes_info = self._get_kubectl_nodes(auth_data, auth_type, cluster.api_server)
                live_data_available = len(nodes_info) > 0
            except:
                live_data_available = False
        
        return {
            "id": str(cluster.id),
            "name": cluster.name,
            "auth_type": cluster.auth_type,
            "api_server": cluster.api_server,
            "has_kubeconfig": bool(cluster.kubeconfig),
            "status": cluster.status,
            "master_nodes_db": cluster.master_nodes,
            "worker_nodes_db": cluster.worker_nodes,
            "live_data_available": live_data_available,
            "auth_data_length": len(auth_data) if auth_data else 0
        }
    
    def migrate_cluster_encryption(self, cluster_id: uuid.UUID, user_id: uuid.UUID, new_kubeconfig: str) -> bool:
        """Migrate a cluster to use new encryption key"""
        cluster = self.get_cluster_by_id(cluster_id)
        if not cluster or cluster.user_id != user_id:
            return False
        
        try:
            # Encrypt with new key
            encrypted_kubeconfig = encryption_manager.encrypt_data(new_kubeconfig)
            cluster.kubeconfig = encrypted_kubeconfig
            cluster.status = 'registered'
            self.db.commit()
            logger.info(f"Successfully migrated cluster {cluster_id} to new encryption key")
            return True
        except Exception as e:
            logger.error(f"Failed to migrate cluster encryption for {cluster_id}: {e}")
            return False
