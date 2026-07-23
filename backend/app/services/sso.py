from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import encrypt_secret, decrypt_secret
from app.models import OrganizationSettings


def get_or_create_org_settings(db: Session) -> OrganizationSettings:
    settings = db.get(OrganizationSettings, 1)
    if settings:
        return settings
    settings = OrganizationSettings(id=1)
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def resolve_oidc_config(db: Session) -> dict[str, Any]:
    """Merge env settings with org DB settings. Env wins when oidc_enabled."""
    env = get_settings()
    org = get_or_create_org_settings(db)

    if env.oidc_enabled and env.oidc_issuer and env.oidc_client_id:
        return {
            "enabled": True,
            "provider_name": env.oidc_provider_name,
            "issuer": env.oidc_issuer.rstrip("/"),
            "client_id": env.oidc_client_id,
            "client_secret": env.oidc_client_secret or "",
            "redirect_uri": env.oidc_redirect_uri
            or f"http://localhost:8000{env.api_prefix}/auth/sso/callback",
            "scopes": env.oidc_scopes,
            "default_role": env.oidc_default_role,
            "allow_local_login": True,
            "source": "env",
        }

    secret = ""
    if org.oidc_client_secret_encrypted:
        try:
            secret = decrypt_secret(org.oidc_client_secret_encrypted)
        except Exception:
            secret = ""

    return {
        "enabled": bool(org.sso_enabled and org.oidc_issuer and org.oidc_client_id),
        "provider_name": org.sso_provider_name or "OIDC",
        "issuer": (org.oidc_issuer or "").rstrip("/"),
        "client_id": org.oidc_client_id or "",
        "client_secret": secret,
        "redirect_uri": org.oidc_redirect_uri
        or f"http://localhost:8000{env.api_prefix}/auth/sso/callback",
        "scopes": org.oidc_scopes or "openid profile email",
        "default_role": org.oidc_default_role or "member",
        "allow_local_login": org.allow_local_login,
        "source": "org",
    }


def update_org_sso(db: Session, *, actor_id, payload: dict[str, Any]) -> OrganizationSettings:
    org = get_or_create_org_settings(db)
    for field in (
        "sso_enabled",
        "sso_provider_name",
        "oidc_issuer",
        "oidc_client_id",
        "oidc_redirect_uri",
        "oidc_scopes",
        "oidc_default_role",
        "allow_local_login",
    ):
        if field in payload and payload[field] is not None:
            setattr(org, field, payload[field])
    if payload.get("oidc_client_secret"):
        org.oidc_client_secret_encrypted = encrypt_secret(payload["oidc_client_secret"])
    org.updated_by = actor_id
    org.updated_at = datetime.now(UTC)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def admin_sso_view(db: Session) -> dict[str, Any]:
    org = get_or_create_org_settings(db)
    env = get_settings()
    return {
        "sso_enabled": org.sso_enabled or env.oidc_enabled,
        "sso_provider_name": org.sso_provider_name if not env.oidc_enabled else env.oidc_provider_name,
        "oidc_issuer": org.oidc_issuer or env.oidc_issuer,
        "oidc_client_id": org.oidc_client_id or env.oidc_client_id,
        "oidc_client_secret_set": bool(org.oidc_client_secret_encrypted or env.oidc_client_secret),
        "oidc_redirect_uri": org.oidc_redirect_uri or env.oidc_redirect_uri,
        "oidc_scopes": org.oidc_scopes or env.oidc_scopes,
        "oidc_default_role": org.oidc_default_role or env.oidc_default_role,
        "allow_local_login": org.allow_local_login,
    }


async def fetch_oidc_discovery(issuer: str) -> dict[str, Any]:
    url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


def build_authorize_url(cfg: dict[str, Any], discovery: dict[str, Any], state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "scope": cfg["scopes"],
        "state": state,
    }
    endpoint = discovery.get("authorization_endpoint") or f"{cfg['issuer']}/authorize"
    return f"{endpoint}?{urlencode(params)}"


async def exchange_code_for_tokens(cfg: dict[str, Any], discovery: dict[str, Any], code: str) -> dict[str, Any]:
    token_url = discovery.get("token_endpoint") or f"{cfg['issuer']}/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": cfg["redirect_uri"],
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(token_url, data=data)
        response.raise_for_status()
        return response.json()


async def fetch_userinfo(discovery: dict[str, Any], access_token: str) -> dict[str, Any]:
    userinfo_url = discovery.get("userinfo_endpoint")
    if not userinfo_url:
        return {}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(userinfo_url, headers={"Authorization": f"Bearer {access_token}"})
        response.raise_for_status()
        return response.json()


def invite_expiry(days: int = 7) -> datetime:
    return datetime.now(UTC) + timedelta(days=days)
