from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import require_permission
from app.core.permissions import Permission
from app.db.database import get_db
from app.models import User
from app.services.workboard import WorkboardIntegrationService

router = APIRouter(prefix="/triggers", tags=["triggers"])


class WebhookTriggerPayload(BaseModel):
    workflow_id: str
    inputs: dict = Field(default_factory=dict)


class WorkboardStatusPayload(BaseModel):
    work_item_key: str
    status: str


@router.post("/webhook")
def webhook_trigger(
    payload: WebhookTriggerPayload,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RUN_WORKFLOWS)),
):
    from uuid import UUID

    from app.engine.orchestrator import WorkflowEngine
    from app.models import Workflow, WorkflowVersion

    workflow = db.get(Workflow, UUID(payload.workflow_id))
    if not workflow or workflow.deleted_at:
        raise HTTPException(status_code=404, detail="Workflow not found")
    version = (
        db.query(WorkflowVersion)
        .filter(
            WorkflowVersion.workflow_id == workflow.id,
            WorkflowVersion.version == workflow.current_version,
        )
        .one()
    )
    run = WorkflowEngine(db).start_run(
        workflow=workflow,
        version=version,
        triggered_by=user.id,
        inputs=payload.inputs,
        trigger_type="webhook",
    )
    return {"id": str(run.id), "status": run.status}


@router.post("/workboard-status")
def workboard_status_trigger(payload: WorkboardStatusPayload, db: Session = Depends(get_db)):
    run = WorkboardIntegrationService(db).handle_status_change(payload.work_item_key, payload.status)
    if not run:
        return {"triggered": False}
    return {"triggered": True, "runId": str(run.id), "status": run.status}
