from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, agentic, agents, auth, exposed, runs, triggers, workflows
from app.core.config import get_settings
from app.db.database import Base, SessionLocal, engine
from app.executors.builtin import register_builtin_executors
from app.models import OrganizationSettings  # noqa: F401 — register models
import app.models  # noqa: F401

settings = get_settings()
register_builtin_executors()


def _ensure_schema() -> None:
    """Create tables and add columns for SQLite/dev without requiring alembic."""
    Base.metadata.create_all(bind=engine)
    if not settings.database_url.startswith("sqlite"):
        return
    from sqlalchemy import text

    alters = [
        "ALTER TABLE users ADD COLUMN auth_provider VARCHAR(40) DEFAULT 'local'",
        "ALTER TABLE users ADD COLUMN sso_subject VARCHAR(255)",
        "ALTER TABLE workflows ADD COLUMN is_exposed BOOLEAN DEFAULT 0",
        "ALTER TABLE workflows ADD COLUMN expose_slug VARCHAR(120)",
        "ALTER TABLE workflows ADD COLUMN expose_description TEXT",
        "ALTER TABLE workflows ADD COLUMN input_schema JSON DEFAULT '{}'",
        "ALTER TABLE api_keys ADD COLUMN client_id VARCHAR(120) DEFAULT ''",
        "ALTER TABLE api_keys ADD COLUMN description TEXT",
    ]
    with engine.begin() as conn:
        for stmt in alters:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass
    db = SessionLocal()
    try:
        if not db.get(OrganizationSettings, 1):
            db.add(OrganizationSettings(id=1))
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _ensure_schema()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description=(
        "OneOpen Flow — visual workflow orchestration and validation platform. "
        "Agentic AI uses service accounts (POST /api/admin/service-accounts). "
        "Discover tools via GET /api/agentic/catalog."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "oneopen-flow"}


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(workflows.router, prefix=settings.api_prefix)
app.include_router(runs.router, prefix=settings.api_prefix)
app.include_router(agents.router, prefix=settings.api_prefix)
app.include_router(triggers.router, prefix=settings.api_prefix)
app.include_router(exposed.router, prefix=settings.api_prefix)
app.include_router(agentic.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
