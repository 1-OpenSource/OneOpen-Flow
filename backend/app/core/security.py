import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from cryptography.fernet import Fernet
from jose import JWTError, jwt

from app.core.config import get_settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")
    if len(raw) > 72:
        raw = hashlib.sha256(raw).digest()
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    raw = plain_password.encode("utf-8")
    if len(raw) > 72:
        raw = hashlib.sha256(raw).digest()
    try:
        return bcrypt.checkpw(raw, password_hash.encode("utf-8"))
    except ValueError:
        return False


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Return (raw_token, prefix, token_hash)."""
    raw = f"oof_{secrets.token_urlsafe(32)}"
    prefix = raw[:12]
    return raw, prefix, hash_token(raw)


def generate_invite_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expires_at}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None


def _fernet() -> Fernet:
    settings = get_settings()
    import base64

    digest = hashlib.sha256(settings.encryption_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")


def mask_secrets(text: str, secret_values: list[str]) -> str:
    masked = text
    for value in secret_values:
        if value:
            masked = masked.replace(value, "***")
    return masked
