"""
AI Workspace API — Security Utilities

Password hashing, opaque session tokens, and secret encryption.
"""

import base64
import hashlib
import secrets
from typing import Final

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.fernet import Fernet, InvalidToken

_PASSWORD_HASHER: Final = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a plaintext password with argon2."""
    return _PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return whether ``password`` matches ``password_hash``."""
    try:
        return _PASSWORD_HASHER.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def generate_session_token() -> str:
    """Generate a high-entropy opaque session token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a session token before persistence or lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _fernet(secret: str) -> Fernet:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str, secret: str) -> str:
    """Encrypt a secret value for storage at rest."""
    return _fernet(secret).encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str, secret: str) -> str:
    """Decrypt a stored secret value."""
    try:
        return _fernet(secret).decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt secret") from exc
