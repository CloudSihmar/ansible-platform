from cryptography.fernet import Fernet
import os
from config.settings import settings

class EncryptionManager:
    def __init__(self):
        self.cipher_suite = Fernet(self._get_encryption_key())
    
    def _get_encryption_key(self) -> bytes:
        """Get or create encryption key for sensitive data"""
        key_file = "encryption.key"
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            return key
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        if not data:
            return data
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not encrypted_data:
            return encrypted_data
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()

# Create global instance
encryption_manager = EncryptionManager()
