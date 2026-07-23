from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, hash_password, hash_token, verify_password
from app.db.database import get_db
from app.models import User, UserInvite
from app.schemas import (
    AcceptInviteRequest,
    LoginRequest,
    SetupStatus,
    SsoPublicConfig,
    TokenResponse,
    UserCreate,
    UserRead,
)
from app.services.sso import (
    build_authorize_url,
    exchange_code_for_tokens,
    fetch_oidc_discovery,
    fetch_userinfo,
    resolve_oidc_config,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/setup-status", response_model=SetupStatus)
def setup_status(db: Session = Depends(get_db)) -> SetupStatus:
    count = db.query(User).count()
    return SetupStatus(needs_owner=count == 0)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    is_first = db.query(User).count() == 0
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="owner" if is_first else "member",
        auth_provider="local",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    cfg = resolve_oidc_config(db)
    if not cfg.get("allow_local_login", True) and cfg.get("enabled"):
        raise HTTPException(status_code=403, detail="Local login disabled. Use SSO.")
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    token = create_access_token(str(user.id), expires_delta=timedelta(minutes=1440))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/accept-invite", response_model=TokenResponse)
def accept_invite(payload: AcceptInviteRequest, db: Session = Depends(get_db)) -> TokenResponse:
    invite = (
        db.query(UserInvite)
        .filter(UserInvite.token_hash == hash_token(payload.token), UserInvite.accepted_at.is_(None))
        .first()
    )
    if not invite:
        raise HTTPException(status_code=400, detail="Invalid invite")
    from datetime import UTC, datetime

    expires = invite.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        raise HTTPException(status_code=400, detail="Invite expired")
    existing = db.query(User).filter(User.email == invite.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    user = User(
        name=payload.name,
        email=invite.email,
        password_hash=hash_password(payload.password),
        role=invite.role,
        auth_provider="local",
    )
    db.add(user)
    invite.accepted_at = datetime.now(UTC)
    db.add(invite)
    db.commit()
    db.refresh(user)
    token = create_access_token(str(user.id), expires_delta=timedelta(minutes=1440))
    return TokenResponse(access_token=token)


@router.get("/sso/config", response_model=SsoPublicConfig)
def sso_public_config(request: Request, db: Session = Depends(get_db)) -> SsoPublicConfig:
    cfg = resolve_oidc_config(db)
    base = str(request.base_url).rstrip("/")
    return SsoPublicConfig(
        enabled=bool(cfg["enabled"]),
        provider_name=cfg["provider_name"],
        authorize_url=f"{base}/api/auth/sso/authorize" if cfg["enabled"] else None,
        allow_local_login=bool(cfg.get("allow_local_login", True)),
    )


@router.get("/sso/authorize")
async def sso_authorize(db: Session = Depends(get_db)):
    cfg = resolve_oidc_config(db)
    if not cfg["enabled"]:
        raise HTTPException(status_code=400, detail="SSO is not enabled")
    try:
        discovery = await fetch_oidc_discovery(cfg["issuer"])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OIDC discovery failed: {exc}") from exc
    import secrets

    state = secrets.token_urlsafe(24)
    url = build_authorize_url(cfg, discovery, state)
    response = RedirectResponse(url)
    response.set_cookie("oof_sso_state", state, httponly=True, max_age=600, samesite="lax")
    return response


@router.get("/sso/callback")
async def sso_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    frontend = settings.frontend_url.rstrip("/")
    if error:
        return RedirectResponse(f"{frontend}/login?sso_error={error}")
    if not code:
        return RedirectResponse(f"{frontend}/login?sso_error=missing_code")
    cookie_state = request.cookies.get("oof_sso_state")
    if not state or not cookie_state or state != cookie_state:
        return RedirectResponse(f"{frontend}/login?sso_error=invalid_state")

    cfg = resolve_oidc_config(db)
    if not cfg["enabled"]:
        return RedirectResponse(f"{frontend}/login?sso_error=sso_disabled")

    try:
        discovery = await fetch_oidc_discovery(cfg["issuer"])
        tokens = await exchange_code_for_tokens(cfg, discovery, code)
        userinfo = await fetch_userinfo(discovery, tokens.get("access_token", ""))
    except Exception:
        return RedirectResponse(f"{frontend}/login?sso_error=token_exchange_failed")

    email = (userinfo.get("email") or "").lower().strip()
    subject = str(userinfo.get("sub") or "")
    name = userinfo.get("name") or userinfo.get("preferred_username") or email or "SSO User"
    if not email and not subject:
        return RedirectResponse(f"{frontend}/login?sso_error=missing_profile")

    user = None
    if subject:
        user = db.query(User).filter(User.sso_subject == subject).first()
    if not user and email:
        user = db.query(User).filter(User.email == email).first()

    if not user:
        is_first = db.query(User).count() == 0
        user = User(
            name=name,
            email=email or f"{subject}@sso.local",
            password_hash=None,
            role="owner" if is_first else cfg.get("default_role", "member"),
            auth_provider="oidc",
            sso_subject=subject or None,
        )
        db.add(user)
    else:
        user.auth_provider = "oidc"
        if subject:
            user.sso_subject = subject
        if name and not user.name:
            user.name = name
        db.add(user)
    db.commit()
    db.refresh(user)

    if not user.is_active:
        return RedirectResponse(f"{frontend}/login?sso_error=inactive")

    token = create_access_token(str(user.id), expires_delta=timedelta(minutes=1440))
    response = RedirectResponse(f"{frontend}/login?sso_token={token}")
    response.delete_cookie("oof_sso_state")
    return response
