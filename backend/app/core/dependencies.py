from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.permissions import Permission, has_permission
from app.core.security import decode_access_token, hash_token
from app.db.database import get_db
from app.models import ApiKey, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        user_id = UUID(payload["sub"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user


def get_optional_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    try:
        user_id = UUID(payload["sub"])
    except ValueError:
        return None
    user = db.get(User, user_id)
    if not user or not user.is_active:
        return None
    return user


def get_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> ApiKey | None:
    raw = x_api_key
    if not raw and credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
        if token.startswith("oof_"):
            raw = token
    if not raw:
        return None
    key = (
        db.query(ApiKey)
        .filter(ApiKey.token_hash == hash_token(raw), ApiKey.is_active.is_(True))
        .first()
    )
    if not key:
        return None
    if key.expires_at:
        expires = key.expires_at if key.expires_at.tzinfo else key.expires_at.replace(tzinfo=UTC)
        if expires < datetime.now(UTC):
            return None
    key.last_used_at = datetime.now(UTC)
    db.add(key)
    db.commit()
    return key


def require_permission(permission: Permission):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user.role, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return user

    return dependency


def require_user_or_api_key(
    *,
    permission: Permission | None = None,
    api_scope: str | None = None,
):
    """Allow JWT user (with optional permission) or API key (with optional scope)."""

    def dependency(
        user: User | None = Depends(get_optional_user),
        api_key: ApiKey | None = Depends(get_api_key),
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        if user:
            if permission and not has_permission(user.role, permission):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
            return {"type": "user", "user": user, "api_key": None}
        # Retry API key from bearer if OAuth2 didn't match and get_api_key missed
        if not api_key and credentials:
            token = credentials.credentials
            if token.startswith("oof_"):
                api_key = (
                    db.query(ApiKey)
                    .filter(ApiKey.token_hash == hash_token(token), ApiKey.is_active.is_(True))
                    .first()
                )
                if api_key and (not api_key.expires_at or api_key.expires_at >= datetime.now(UTC)):
                    api_key.last_used_at = datetime.now(UTC)
                    db.add(api_key)
                    db.commit()
                else:
                    api_key = None
        if api_key:
            scopes = api_key.scopes or []
            if api_scope and api_scope not in scopes and "*" not in scopes:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key scope denied")
            return {"type": "api_key", "user": None, "api_key": api_key}
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    return dependency
