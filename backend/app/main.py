from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agents, auth, runs, triggers, workflows
from app.core.config import get_settings
from app.executors.builtin import register_builtin_executors

settings = get_settings()
register_builtin_executors()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="OneOpen Flow — visual workflow orchestration and validation platform.",
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
