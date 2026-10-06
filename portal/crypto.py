"""Separate keys: Fernet protects stored credentials; AES/HMAC authenticates to Guacamole."""
import base64
import hashlib
import hmac
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.conf import settings

def encrypt_secret(value):
    return Fernet(settings.CREDENTIAL_KEY.encode()).encrypt(value.encode()).decode()

def decrypt_secret(value):
    return Fernet(settings.CREDENTIAL_KEY.encode()).decrypt(value.encode()).decode()

def guacamole_payload(data):
    # The zero IV is REQUIRED by Guacamole's encrypted-JSON protocol.
    # This is protocol compatibility code, not a general encryption recipe.
    key = bytes.fromhex(settings.GUACAMOLE_JSON_SECRET)
    if len(key) != 16:
        raise ValueError("GUACAMOLE_JSON_SECRET must contain 32 hexadecimal characters")
    message = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode()
    signature = hmac.new(key, message, hashlib.sha256).digest()
    padder = padding.PKCS7(128).padder()
    padded = padder.update(signature + message) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(bytes(16))).encryptor()
    return base64.b64encode(encryptor.update(padded) + encryptor.finalize()).decode()

def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()
