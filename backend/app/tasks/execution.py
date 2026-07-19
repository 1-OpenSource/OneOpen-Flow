from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "oneopen_flow",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.task_routes = {"app.tasks.execution.*": {"queue": "flow"}}


@celery_app.task(name="app.tasks.execution.execute_run")
def execute_run_task(run_id: str) -> str:
    from uuid import UUID

    from app.db.database import SessionLocal
    from app.engine.orchestrator import WorkflowEngine

    db = SessionLocal()
    try:
        WorkflowEngine(db).execute_run(UUID(run_id))
        return run_id
    finally:
        db.close()
