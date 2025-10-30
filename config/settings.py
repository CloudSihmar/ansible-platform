import os
from typing import Dict, Any
from pathlib import Path

class Settings:
    # Database
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://ansible_user:ansible_password@localhost:5432/ansible_platform"
    )

    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30

    # Application
    PROJECT_NAME = "Ansible Platform"
    VERSION = "1.0.0"
    API_PREFIX = "/api"

    # Ansible
    ANSIBLE_ROLES_PATH = os.getenv("ANSIBLE_ROLES_PATH", "./ansible_roles")
    PLAYBOOKS_BASE_PATH = os.getenv("PLAYBOOKS_BASE_PATH", "./playbooks")

    # Kubernetes
    KUBECONFIG_STORAGE_PATH = os.getenv("KUBECONFIG_STORAGE_PATH", "./kubeconfigs")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Derived properties for path management
    @property
    def ansible_roles_directory(self) -> Path:
        """Get ansible roles directory as Path object"""
        return Path(self.ANSIBLE_ROLES_PATH)

    @property
    def playbooks_base_directory(self) -> Path:
        """Get playbooks base directory as Path object"""
        return Path(self.PLAYBOOKS_BASE_PATH)

    @property
    def kubeconfig_storage_directory(self) -> Path:
        """Get kubeconfig storage directory as Path object"""
        return Path(self.KUBECONFIG_STORAGE_PATH)

    def ensure_directories_exist(self):
        """Ensure all required application directories exist"""
        directories = [
            self.ansible_roles_directory,
            self.playbooks_base_directory,
            self.kubeconfig_storage_directory
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"✅ Directory ensured: {directory.absolute()}")

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration for SQLAlchemy"""
        return {
            "url": self.DATABASE_URL,
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "echo": self.LOG_LEVEL == "DEBUG"
        }

    def get_jwt_config(self) -> Dict[str, Any]:
        """Get JWT configuration"""
        return {
            "secret_key": self.SECRET_KEY,
            "algorithm": self.ALGORITHM,
            "access_token_expire_minutes": self.ACCESS_TOKEN_EXPIRE_MINUTES
        }

    def __str__(self) -> str:
        """String representation of settings (safe - hides sensitive data)"""
        return f"{self.PROJECT_NAME} v{self.VERSION}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary (safe - hides sensitive data)"""
        return {
            "project_name": self.PROJECT_NAME,
            "version": self.VERSION,
            "api_prefix": self.API_PREFIX,
            "ansible_roles_path": self.ANSIBLE_ROLES_PATH,
            "playbooks_base_path": self.PLAYBOOKS_BASE_PATH,
            "kubeconfig_storage_path": self.KUBECONFIG_STORAGE_PATH,
            "log_level": self.LOG_LEVEL,
            "algorithm": self.ALGORITHM,
            "access_token_expire_minutes": self.ACCESS_TOKEN_EXPIRE_MINUTES
        }

# Create global settings instance
settings = Settings()

# Ensure directories exist when module is imported
settings.ensure_directories_exist()
