#!/usr/bin/env python3
"""
Generate encryption keys for production deployment
"""
from cryptography.fernet import Fernet
import base64
import os

def generate_encryption_key():
    """Generate and display a new encryption key"""
    key = Fernet.generate_key()
    key_str = key.decode()
    
    print("🔐 Encryption Key Generated:")
    print("=" * 50)
    print(key_str)
    print("=" * 50)
    print("\nAdd this to your environment variables:")
    print(f"ENCRYPTION_KEY={key_str}")
    
    # Also save to file for Docker secrets
    with open('encryption.key', 'w') as f:
        f.write(key_str)
    print("\n✅ Also saved to 'encryption.key'")
    print("🔒 Remember to set file permissions: chmod 600 encryption.key")

if __name__ == "__main__":
    generate_encryption_key()
