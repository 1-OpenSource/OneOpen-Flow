import asyncio
import json
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import get_current_user, require_permission
from app.core.permissions import Permission
from app.db.database import get_db
from app.engine.events import event_broker
from app.engine.orchestrator import WorkflowEngine
from app.models import User, Workflow, WorkflowRun, WorkflowVersion
from app.schemas import (
    CreateWorkItemRequest,
    ProvideInputRequest,
    RetryFromNodeRequest,
    WorkboardLinkRead,
    WorkflowRunRead,
)
from app.services.audit import AuditService
from app.services.workboard import WorkboardIntegrationService
from app.storage.service import StorageService

router = APIRouter(tags=["runs"])


@router.get("/runs", response_model=list[WorkflowRunRead])
def list_runs(
    workflow_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.VIEW_WORKFLOWS)),
):
    query = db.query(WorkflowRun).options(
        joinedload(WorkflowRun.node_runs),
        joinedload(WorkflowRun.artifacts),
    )
    if workflow_id:
        query = query.filter(WorkflowRun.workflow_id == workflow_id)
    return query.order_by(WorkflowRun.created_at.desc()).limit(100).all()


@router.get("/runs/{run_id}", response_model=WorkflowRunRead)
def get_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.VIEW_WORKFLOWS)),
):
    run = (
        db.query(WorkflowRun)
        .options(joinedload(WorkflowRun.node_runs), joinedload(WorkflowRun.artifacts))
        .filter(WorkflowRun.id == run_id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/runs/{run_id}/cancel", response_model=WorkflowRunRead)
def cancel_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RUN_WORKFLOWS)),
):
    engine = WorkflowEngine(db)
    return engine.cancel_run(run_id)


@router.post("/runs/{run_id}/retry")
def retry_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RUN_WORKFLOWS)),
):
    run = db.get(WorkflowRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    workflow = db.get(Workflow, run.workflow_id)
    version = (
        db.query(WorkflowVersion)
        .filter(
            WorkflowVersion.workflow_id == run.workflow_id,
            WorkflowVersion.version == run.version,
        )
        .one()
    )
    engine = WorkflowEngine(db)
    new_run = engine.start_run(
        workflow=workflow,  # type: ignore[arg-type]
        version=version,
        triggered_by=user.id,
        inputs=run.inputs,
        trigger_type="manual",
        retry_of_run_id=run.id,
    )
    return {"id": str(new_run.id), "status": new_run.status}


@router.post("/runs/{run_id}/retry-from-node")
def retry_from_node(
    run_id: UUID,
    payload: RetryFromNodeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RUN_WORKFLOWS)),
):
    run = db.get(WorkflowRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    workflow = db.get(Workflow, run.workflow_id)
    version = (
        db.query(WorkflowVersion)
        .filter(
            WorkflowVersion.workflow_id == run.workflow_id,
            WorkflowVersion.version == run.version,
        )
        .one()
    )
    engine = WorkflowEngine(db)
    new_run = engine.start_run(
        workflow=workflow,  # type: ignore[arg-type]
        version=version,
        triggered_by=user.id,
        inputs=run.inputs,
        trigger_type="manual",
        retry_of_run_id=run.id,
        start_from_node=payload.node_id,
    )
    return {"id": str(new_run.id), "status": new_run.status}


@router.post("/runs/{run_id}/provide-input", response_model=WorkflowRunRead)
def provide_input(
    run_id: UUID,
    payload: ProvideInputRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RUN_WORKFLOWS)),
):
    """Resume a run paused for human OTP / verification input."""
    engine = WorkflowEngine(db)
    try:
        run = engine.provide_input(
            run_id,
            {
                "otp": payload.otp,
                "value": payload.value,
                "inputs": payload.inputs,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    AuditService(db).record(
        action="run.human_input_provided",
        resource_type="workflow_run",
        resource_id=str(run_id),
        actor_id=user.id,
        details={"inputType": "otp"},
    )
    db.commit()
    refreshed = (
        db.query(WorkflowRun)
        .options(joinedload(WorkflowRun.node_runs), joinedload(WorkflowRun.artifacts))
        .filter(WorkflowRun.id == run_id)
        .first()
    )
    return refreshed


@router.get("/runs/{run_id}/events")
async def run_events(
    run_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.VIEW_WORKFLOWS)),
):
    run = db.get(WorkflowRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    queue = event_broker.subscribe(run_id)

    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'subscribed', 'runId': str(run_id)})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {json.dumps(event, default=str)}\n\n"
                    if event.get("type") in {"run.completed", "run.failed", "run.cancelled"}:
                        break
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        finally:
            event_broker.unsubscribe(run_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/runs/{run_id}/evidence")
def download_evidence(
    run_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.VIEW_WORKFLOWS)),
):
    run = (
        db.query(WorkflowRun)
        .options(joinedload(WorkflowRun.node_runs), joinedload(WorkflowRun.artifacts))
        .filter(WorkflowRun.id == run_id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    workflow = db.get(Workflow, run.workflow_id)
    storage = StorageService()
    manifest = {
        "workflow": {"id": str(workflow.id), "name": workflow.name, "version": run.version},  # type: ignore[union-attr]
        "run": {
            "id": str(run.id),
            "status": run.status,
            "inputs": run.inputs,
            "failureClassification": run.failure_classification,
            "failureMessage": run.failure_message,
            "startedAt": run.started_at,
            "endedAt": run.ended_at,
            "durationMs": run.duration_ms,
        },
        "nodeResults": [
            {
                "nodeId": nr.node_id,
                "name": nr.node_name,
                "status": nr.status,
                "outputs": nr.outputs,
                "error": nr.error,
                "durationMs": nr.duration_ms,
            }
            for nr in run.node_runs
        ],
    }
    files = [Path(a.storage_path) for a in run.artifacts]
    zip_path = storage.build_evidence_zip(run.id, manifest, files)
    AuditService(db).record(
        action="evidence.downloaded",
        resource_type="workflow_run",
        resource_id=str(run.id),
        actor_id=user.id,
    )
    db.commit()
    return FileResponse(zip_path, filename=f"evidence-{run.id}.zip", media_type="application/zip")


@router.post("/runs/{run_id}/create-work-item", response_model=WorkboardLinkRead)
def create_work_item(
    run_id: UUID,
    payload: CreateWorkItemRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.CREATE_WORKBOARD_DEFECTS)),
    authorization: str | None = Header(default=None),
):
    run = (
        db.query(WorkflowRun)
        .options(joinedload(WorkflowRun.node_runs), joinedload(WorkflowRun.artifacts))
        .filter(WorkflowRun.id == run_id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    workflow = db.get(Workflow, run.workflow_id)
    token = authorization.replace("Bearer ", "") if authorization else None
    link = WorkboardIntegrationService(db).create_work_item(
        run=run,
        workflow=workflow,  # type: ignore[arg-type]
        actor_id=user.id,
        project_id=payload.project_id,
        title=payload.title,
        additional_notes=payload.additional_notes,
        auth_token=token,
    )
    return link
