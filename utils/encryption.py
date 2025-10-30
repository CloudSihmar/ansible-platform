import os
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from config.settings import settings

logger = logging.getLogger(__name__)

class EncryptionManager:
    def __init__(self):
        self.secret_key = self._get_production_secret_key()
        self.cipher_suite = Fernet(self.secret_key)
        logger.info("🔐 Encryption manager initialized with production-grade key management")
    
    def _get_production_secret_key(self) -> bytes:
        """
        Production-grade key management hierarchy:
        1. Environment variable (for Docker/K8s deployments)
        2. Docker/Kubernetes secrets file
        3. Persistent volume file (with backup capability)
        4. Fallback: Generate new key with warning
        """
        
        # Method 1: Environment variable (Highest priority - Production)
        env_key = os.getenv('ENCRYPTION_KEY')
        if env_key:
            logger.info("✅ Using encryption key from ENCRYPTION_KEY environment variable")
            try:
                return self._validate_and_decode_key(env_key)
            except Exception as e:
                logger.error(f"❌ Invalid ENCRYPTION_KEY from environment: {e}")
                raise ValueError(f"Invalid ENCRYPTION_KEY environment variable: {e}")
        
        # Method 2: Docker/Kubernetes secrets file
        secret_file_path = os.getenv('ENCRYPTION_KEY_FILE', '/run/secrets/encryption_key')
        if os.path.exists(secret_file_path):
            try:
                with open(secret_file_path, 'r') as f:
                    file_key = f.read().strip()
                logger.info(f"✅ Using encryption key from secret file: {secret_file_path}")
                return self._validate_and_decode_key(file_key)
            except Exception as e:
                logger.error(f"❌ Failed to read encryption key from {secret_file_path}: {e}")
        
        # Method 3: Persistent local file (Development/Backup)
        # Use multiple backup locations for redundancy
        key_locations = [
            '/app/data/encryption_key.key',  # Docker volume
            '/app/encryption_key.key',       # App directory
            'encryption_key.key'             # Current directory
        ]
        
        for key_file in key_locations:
            if os.path.exists(key_file):
                try:
                    with open(key_file, 'rb') as f:
                        existing_key = f.read()
                    logger.info(f"✅ Using existing encryption key from: {key_file}")
                    return existing_key
                except Exception as e:
                    logger.error(f"❌ Failed to read key file {key_file}: {e}")
                    continue
        
        # Method 4: Generate new key with persistence
        logger.warning("⚠️  No existing encryption key found. Generating new key...")
        new_key = Fernet.generate_key()
        
        # Try to persist the key in multiple locations
        persistence_locations = [
            '/app/data/encryption_key.key',  # Primary persistence location
            'encryption_key.key'             # Fallback location
        ]
        
        key_saved = False
        for key_file in persistence_locations:
            try:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(key_file), exist_ok=True)
                
                with open(key_file, 'wb') as f:
                    f.write(new_key)
                # Set restrictive permissions
                os.chmod(key_file, 0o600)
                logger.info(f"✅ Generated and saved new encryption key to: {key_file}")
                key_saved = True
                break
            except Exception as e:
                logger.warning(f"⚠️  Could not save key to {key_file}: {e}")
                continue
        
        if not key_saved:
            logger.error("❌ CRITICAL: Could not persist encryption key anywhere!")
            logger.warning("⚠️  Encryption key will be lost on container restart!")
        
        return new_key
    
    def _validate_and_decode_key(self, key_str: str) -> bytes:
        """
        Validate and decode a base64 encoded key string
        Ensures the key is a valid Fernet key (32 url-safe base64-encoded bytes)
        """
        if not key_str:
            raise ValueError("Empty encryption key provided")
        
        # Remove any whitespace or quotes
        key_str = key_str.strip().strip('"').strip("'")
        
        try:
            # Fernet keys are 32 bytes, encoded as 44-character base64 strings
            if len(key_str) != 44:
                raise ValueError(f"Key must be 44 characters long, got {len(key_str)}")
            
            # Test if it's valid base64
            key_bytes = base64.urlsafe_b64decode(key_str)
            
            # Fernet requires exactly 32 bytes
            if len(key_bytes) != 32:
                raise ValueError(f"Key must decode to 32 bytes, got {len(key_bytes)}")
            
            # Test the key by creating a temporary Fernet instance
            test_fernet = Fernet(key_str.encode())
            test_fernet.encrypt(b"test")  # This will fail if key is invalid
            
            logger.debug("✅ Encryption key validation successful")
            return key_str.encode()  # Return as bytes
            
        except Exception as e:
            raise ValueError(f"Invalid encryption key format: {e}")
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt data and return as base64 string"""
        if not data:
            return ""
        
        try:
            encrypted_data = self.cipher_suite.encrypt(data.encode())
            # Double base64 encoding for safe storage in database
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"❌ Encryption failed: {e}")
            raise ValueError(f"Encryption failed: {e}")
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt base64 encoded encrypted data"""
        if not encrypted_data:
            return ""
        
        try:
            # Handle double base64 encoding from encrypt_data
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(encrypted_bytes)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"❌ Decryption failed: {e}")
            # Re-raise with more context
            raise ValueError(f"Decryption failed - possible key mismatch: {e}")
    
    def rotate_key(self, new_key: str) -> bool:
        """
        Rotate to a new encryption key (for key rotation procedures)
        Returns True if successful, False otherwise
        """
        try:
            validated_key = self._validate_and_decode_key(new_key)
            old_cipher_suite = self.cipher_suite
            self.cipher_suite = Fernet(validated_key)
            
            # Test the new key
            test_data = "test_rotation"
            encrypted = self.encrypt_data(test_data)
            decrypted = self.decrypt_data(encrypted)
            
            if decrypted == test_data:
                logger.info("✅ Encryption key rotation successful")
                return True
            else:
                # Revert on failure
                self.cipher_suite = old_cipher_suite
                logger.error("❌ Encryption key rotation test failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Encryption key rotation failed: {e}")
            return False
    
    def get_key_fingerprint(self) -> str:
        """Get a fingerprint of the current encryption key for verification"""
        import hashlib
        key_hash = hashlib.sha256(self.secret_key).hexdigest()[:16]
        return f"key_{key_hash}"

# Global instance
encryption_manager = EncryptionManager()
