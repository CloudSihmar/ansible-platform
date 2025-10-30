import subprocess
import tempfile
import os
import shutil
from typing import Dict, List, Optional, Tuple
import uuid
from datetime import datetime

class AnsibleRunner:
    def __init__(self, playbooks_base_path: str = "./playbooks"):
        self.playbooks_base_path = playbooks_base_path
        self.ensure_directories()
    
    def ensure_directories(self):
        """Ensure required directories exist"""
        os.makedirs(self.playbooks_base_path, exist_ok=True)
        os.makedirs("/tmp/ansible_runs", exist_ok=True)
    
    def run_playbook(
        self,
        playbook_content: str,
        inventory_content: str,
        ssh_private_key: Optional[str] = None,
        extra_vars: Optional[Dict] = None,
        tags: Optional[str] = None,
        skip_tags: Optional[str] = None
    ) -> Tuple[int, str, str]:
        """
        Execute an Ansible playbook
        
        Returns: (return_code, stdout, stderr)
        """
        # Create temporary files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as pb_file:
            pb_file.write(playbook_content)
            playbook_path = pb_file.name
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as inv_file:
            inv_file.write(inventory_content)
            inventory_path = inv_file.name
        
        # Create temporary SSH key file if provided
        ssh_key_path = None
        if ssh_private_key:
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as key_file:
                key_file.write(ssh_private_key)
                ssh_key_path = key_file.name
            os.chmod(ssh_key_path, 0o600)  # Secure permissions
        
        try:
            # Build ansible command
            cmd = [
                'ansible-playbook',
                '-i', inventory_path,
                playbook_path
            ]
            
            # Add SSH key if provided
            if ssh_key_path:
                cmd.extend(['--private-key', ssh_key_path])
            
            # Add extra variables
            if extra_vars:
                import json
                cmd.extend(['--extra-vars', json.dumps(extra_vars)])
            
            # Add tags
            if tags:
                cmd.extend(['--tags', tags])
            
            # Add skip tags
            if skip_tags:
                cmd.extend(['--skip-tags', skip_tags])
            
            # Set ANSIBLE environment variables
            env = os.environ.copy()
            env['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
            env['ANSIBLE_SSH_RETRIES'] = '3'
            
            print(f"Executing Ansible command: {' '.join(cmd)}")
            
            # Execute playbook
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=3600  # 1 hour timeout
            )
            
            return result.returncode, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return 1, "", "Playbook execution timed out after 1 hour"
        except Exception as e:
            return 1, "", f"Execution error: {str(e)}"
        finally:
            # Cleanup temporary files
            for file_path in [playbook_path, inventory_path]:
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
            if ssh_key_path and os.path.exists(ssh_key_path):
                os.unlink(ssh_key_path)
    
    def validate_playbook_syntax(self, playbook_content: str) -> Tuple[bool, str]:
        """Validate playbook syntax without executing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as pb_file:
            pb_file.write(playbook_content)
            playbook_path = pb_file.name
        
        try:
            cmd = ['ansible-playbook', '--syntax-check', playbook_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True, "Syntax check passed"
            else:
                return False, result.stderr
        except Exception as e:
            return False, f"Syntax check failed: {str(e)}"
        finally:
            if os.path.exists(playbook_path):
                os.unlink(playbook_path)
    
    def get_ansible_version(self) -> Optional[str]:
        """Get Ansible version"""
        try:
            result = subprocess.run(
                ['ansible-playbook', '--version'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.split('\n')[0]  # First line contains version
            return None
        except:
            return None

# Global instance
ansible_runner = AnsibleRunner()
