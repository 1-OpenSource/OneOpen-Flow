from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import require_permission
from app.core.permissions import VALID_ROLES, Permission, permissions_for_role
from app.core.security import generate_api_key, generate_invite_token
from app.db.database import get_db
from app.models import ApiKey, User, UserInvite
from app.schemas import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyRead,
    InviteCreate,
    InviteCreatedResponse,
    InviteRead,
    RolePermissionsRead,
    SsoAdminConfig,
    SsoAdminUpdate,
    UserAdminUpdate,
    UserRead,
)
from app.services.audit import AuditService
from app.services.sso import admin_sso_view, invite_expiry, update_org_sso

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_USERS)),
):
    return db.query(User).order_by(User.created_at.asc()).all()


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: UUID,
    payload: UserAdminUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission(Permission.MANAGE_USERS)),
):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.role is not None:
        if payload.role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid role. Use one of: {', '.join(VALID_ROLES)}")
        if target.role == "owner" and payload.role != "owner" and actor.role != "owner":
            raise HTTPException(status_code=403, detail="Only owner can demote an owner")
        if target.id == actor.id and payload.role != actor.role and actor.role == "owner":
            owners = db.query(User).filter(User.role == "owner", User.is_active.is_(True)).count()
            if owners <= 1:
                raise HTTPException(status_code=400, detail="Cannot demote the last owner")
        target.role = payload.role
    if payload.is_active is not None:
        if target.id == actor.id and not payload.is_active:
            raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
        target.is_active = payload.is_active
    if payload.name is not None:
        target.name = payload.name
    db.add(target)
    AuditService(db).record(
        action="user.updated",
        resource_type="user",
        resource_id=str(target.id),
        actor_id=actor.id,
        details=payload.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(target)
    return target


@router.get("/permissions", response_model=RolePermissionsRead)
def list_permissions(
    user: User = Depends(require_permission(Permission.MANAGE_USERS)),
):
    return RolePermissionsRead(
        roles={role: permissions_for_role(role) for role in VALID_ROLES},
        permissions=sorted(p.value for p in Permission),
    )


@router.post("/invites", response_model=InviteCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_invite(
    payload: InviteCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission(Permission.MANAGE_USERS)),
):
    if payload.role not in VALID_ROLES or payload.role == "owner":
        raise HTTPException(status_code=400, detail="Invite role must be admin, member, or viewer")
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    raw, token_hash = generate_invite_token()
    invite = UserInvite(
        email=payload.email.lower().strip(),
        role=payload.role,
        token_hash=token_hash,
        invited_by=actor.id,
        expires_at=invite_expiry(7),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    settings = get_settings()
    accept_url = f"{settings.frontend_url.rstrip('/')}/login?invite={raw}"
    return InviteCreatedResponse(
        invite=InviteRead.model_validate(invite),
        accept_token=raw,
        accept_url=accept_url,
    )


@router.get("/invites", response_model=list[InviteRead])
def list_invites(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_USERS)),
):
    return db.query(UserInvite).order_by(UserInvite.created_at.desc()).all()


@router.get("/sso", response_model=SsoAdminConfig)
def get_sso_config(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_SSO)),
):
    return SsoAdminConfig(**admin_sso_view(db))


@router.put("/sso", response_model=SsoAdminConfig)
def update_sso_config(
    payload: SsoAdminUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_SSO)),
):
    update_org_sso(db, actor_id=user.id, payload=payload.model_dump(exclude_unset=True))
    AuditService(db).record(
        action="sso.updated",
        resource_type="organization_settings",
        resource_id="1",
        actor_id=user.id,
    )
    db.commit()
    return SsoAdminConfig(**admin_sso_view(db))


@router.get("/api-keys", response_model=list[ApiKeyRead])
@router.get("/service-accounts", response_model=list[ApiKeyRead], include_in_schema=True)
def list_api_keys(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_API_KEYS)),
):
    return db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()


@router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
@router.post(
    "/service-accounts",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=True,
)
def create_api_key(
    payload: ApiKeyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_API_KEYS)),
):
    import re

    raw, prefix, token_hash = generate_api_key()
    expires_at = None
    if payload.expires_in_days:
        expires_at = datetime.now(UTC) + timedelta(days=payload.expires_in_days)
    client_id = (payload.client_id or "").strip().lower()
    if not client_id:
        slug = re.sub(r"[^a-z0-9]+", "-", payload.name.lower()).strip("-")[:80]
        client_id = f"svc-{slug or 'agent'}"
    if not client_id.startswith("svc-"):
        client_id = f"svc-{client_id}"
    existing = db.query(ApiKey).filter(ApiKey.client_id == client_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"client_id '{client_id}' already exists")
    key = ApiKey(
        name=payload.name,
        client_id=client_id,
        description=payload.description,
        prefix=prefix,
        token_hash=token_hash,
        scopes=payload.scopes,
        created_by=user.id,
        expires_at=expires_at,
    )
    db.add(key)
    AuditService(db).record(
        action="service_account.created",
        resource_type="service_account",
        resource_id=str(key.id),
        actor_id=user.id,
        details={"name": payload.name, "client_id": client_id, "scopes": payload.scopes},
    )
    db.commit()
    db.refresh(key)
    read = ApiKeyRead.model_validate(key)
    return ApiKeyCreatedResponse(key=read, token=raw, service_account=read, client_secret=raw)


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/service-accounts/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_API_KEYS)),
):
    key = db.get(ApiKey, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Service account not found")
    key.is_active = False
    db.add(key)
    AuditService(db).record(
        action="service_account.revoked",
        resource_type="service_account",
        resource_id=str(key.id),
        actor_id=user.id,
    )
    db.commit()
