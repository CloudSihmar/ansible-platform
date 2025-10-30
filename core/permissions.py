from typing import Set

class PermissionManager:
    # Define all available permissions
    PERMISSIONS = {
        # User management
        'users:create',
        'users:read',
        'users:update',
        'users:delete',
        
        # Inventory management
        'inventory:create',
        'inventory:read', 
        'inventory:update',
        'inventory:delete',
        
        # Playbook management
        'playbooks:create',
        'playbooks:read',
        'playbooks:update', 
        'playbooks:delete',
        'playbooks:execute',
        
        # Kubernetes specific
        'kubernetes:cluster:create',
        'kubernetes:cluster:read',
        'kubernetes:cluster:update',
        'kubernetes:cluster:delete',
        'kubernetes:cluster:register',
        
        # Credentials management
        'credentials:create',
        'credentials:read',
        'credentials:update',
        'credentials:delete',
        
        # Execution management
        'executions:read',
        'executions:delete',
    }
    
    # Role definitions with permissions
    ROLES = {
        'admin': {
            'users:*',
            'inventory:*',
            'playbooks:*', 
            'kubernetes:*',
            'credentials:*',
            'executions:*'
        },
        'kubernetes_admin': {
            'inventory:create', 'inventory:read', 'inventory:update',
            'playbooks:create', 'playbooks:read', 'playbooks:execute',
            'kubernetes:*',
            'credentials:create', 'credentials:read',
            'executions:read'
        },
        'ansible_operator': {
            'inventory:read',
            'playbooks:read', 'playbooks:execute', 
            'kubernetes:cluster:read',
            'credentials:read',
            'executions:read'
        },
        'viewer': {
            'inventory:read',
            'playbooks:read',
            'kubernetes:cluster:read',
            'executions:read'
        }
    }
    
    def get_role_permissions(self, role: str) -> Set[str]:
        """Get all permissions for a role"""
        permissions = set()
        role_perms = self.ROLES.get(role, set())
        
        for perm_pattern in role_perms:
            if perm_pattern.endswith(':*'):
                # Wildcard permission - add all matching
                resource = perm_pattern[:-2]
                for perm in self.PERMISSIONS:
                    if perm.startswith(resource):
                        permissions.add(perm)
            else:
                permissions.add(perm_pattern)
        
        return permissions
    
    def has_permission(self, role: str, permission: str) -> bool:
        """Check if role has specific permission"""
        role_perms = self.get_role_permissions(role)
        return permission in role_perms

# Global instance
permission_manager = PermissionManager()
