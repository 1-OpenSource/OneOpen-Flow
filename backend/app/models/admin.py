import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.database import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


class ApiKey(Base):
    """Service account credentials for machine-to-machine / Agentic AI access.

    Each row is a service account identity with a hashed secret token.
    Humans use JWT; AI agents and automation use these accounts.
    """

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    client_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    scopes: Mapped[list[Any]] = mapped_column(JSONType, nullable=False, default=list)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UserInvite(Base):
    __tablename__ = "user_invites"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(40), nullable=False, default="member")
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    invited_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class OrganizationSettings(Base):
    """Singleton-style org settings (SSO, branding flags). Always id=1."""

    __tablename__ = "organization_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    sso_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sso_provider_name: Mapped[str] = mapped_column(String(80), nullable=False, default="OIDC")
    oidc_issuer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    oidc_client_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    oidc_client_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    oidc_redirect_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    oidc_scopes: Mapped[str] = mapped_column(String(255), nullable=False, default="openid profile email")
    oidc_default_role: Mapped[str] = mapped_column(String(40), nullable=False, default="member")
    allow_local_login: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
