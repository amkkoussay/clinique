"""
Data encryption helper using Fernet (AES-128-CBC).
Student demo project: no compliance certification of any kind.
"""
from cryptography.fernet import Fernet
import os

KEY_FILE = os.path.join(os.path.dirname(__file__), 'secret.key')

def get_encryption_key():
    """Get or generate persistent encryption key."""
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, 'rb') as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        try:
            with open(KEY_FILE, 'wb') as f:
                f.write(key)
        except Exception:
            pass
        return key

try:
    cipher = Fernet(get_encryption_key())
except Exception:
    cipher = Fernet(Fernet.generate_key())


def encrypt_data(plaintext):
    """Encrypt sensitive string data."""
    if not plaintext:
        return plaintext
    if isinstance(plaintext, str):
        plaintext = plaintext.encode('utf-8')
    try:
        return cipher.encrypt(plaintext).decode('utf-8')
    except Exception:
        return plaintext


def decrypt_data(ciphertext):
    """Decrypt sensitive string data."""
    if not ciphertext:
        return ciphertext
    try:
        if isinstance(ciphertext, str):
            ciphertext = ciphertext.encode('utf-8')
        decrypted = cipher.decrypt(ciphertext)
        return decrypted.decode('utf-8')
    except Exception:
        # Return original if not encrypted or decryption fails
        return ciphertext.decode('utf-8') if isinstance(ciphertext, bytes) else ciphertext
