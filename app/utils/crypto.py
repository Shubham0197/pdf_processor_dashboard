import os
from cryptography.fernet import Fernet
import base64
from app.config import settings

def get_encryption_key():
    """Get or generate encryption key"""
    key = settings.ENCRYPTION_KEY
    if not key:
        # Generate a key and save it (in production, this should be stored securely)
        key = Fernet.generate_key().decode()
        print(f"WARNING: Generated new encryption key. Set this in your .env file: ENCRYPTION_KEY={key}")
    return key.encode() if isinstance(key, str) else key

def encrypt_value(value: str) -> str:
    """Encrypt a string value"""
    if not value:
        return value
        
    f = Fernet(get_encryption_key())
    encrypted = f.encrypt(value.encode())
    return encrypted.decode()

def decrypt_value(encrypted_value: str) -> str:
    """Decrypt an encrypted string value"""
    if not encrypted_value:
        return encrypted_value
        
    f = Fernet(get_encryption_key())
    decrypted = f.decrypt(encrypted_value.encode())
    return decrypted.decode()
