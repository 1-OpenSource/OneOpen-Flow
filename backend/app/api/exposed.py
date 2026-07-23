from __future__ import annotations

import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_permission, require_user_or_api_key
from app.core.permissions import Permission
from app.db.database import get_db
from app.engine.orchestrator import WorkflowEngine
from app.models import Environment, User, Workflow, WorkflowVersion
from app.schemas import (
    ExposedWorkflowDetail,
    ExposedWorkflowSummary,
    RunRequest,
    WorkflowDetail,
    WorkflowExposeRequest,
)
from app.services.audit import AuditService
from app.services.workflows import WorkflowService

router = APIRouter(tags=["exposed-workflows"])


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:100] or "workflow"


def _to_summary(workflow: Workflow) -> ExposedWorkflowSummary:
    return ExposedWorkflowSummary(
        id=workflow.id,
        name=workflow.name,
        slug=workflow.expose_slug or "",
        description=workflow.expose_description or workflow.description,
        input_schema=workflow.input_schema or {},
        tags=workflow.tags or [],
        current_version=workflow.current_version,
    )


@router.put("/workflows/{workflow_id}/expose", response_model=WorkflowDetail)
def expose_workflow(
    workflow_id: UUID,
    payload: WorkflowExposeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.EXPOSE_WORKFLOWS)),
):
    service = WorkflowService(db)
    workflow = service.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if payload.enabled:
        slug = _slugify(payload.slug or workflow.expose_slug or workflow.name)
        conflict = (
            db.query(Workflow)
            .filter(
                Workflow.expose_slug == slug,
                Workflow.id != workflow.id,
                Workflow.deleted_at.is_(None),
            )
            .first()
        )
        if conflict:
            raise HTTPException(status_code=400, detail=f"Slug '{slug}' is already in use")
        workflow.is_exposed = True
        workflow.expose_slug = slug
        workflow.expose_description = payload.description if payload.description is not None else workflow.expose_description
        if payload.input_schema:
            workflow.input_schema = payload.input_schema
        elif not workflow.input_schema:
            definition = service.get_definition(workflow)
            workflow.input_schema = {
                "type": "object",
                "properties": {k: {"type": "string"} for k in (definition.variables or {})},
                "additionalProperties": True,
            }
    else:
        workflow.is_exposed = False

    db.add(workflow)
    AuditService(db).record(
        action="workflow.exposed" if payload.enabled else "workflow.unexposed",
        resource_type="workflow",
        resource_id=str(workflow.id),
        actor_id=user.id,
        details={"slug": workflow.expose_slug, "enabled": payload.enabled},
    )
    db.commit()
    db.refresh(workflow)
    from app.api.workflows import _detail

    return _detail(service, workflow)


@router.get("/exposed/workflows", response_model=list[ExposedWorkflowSummary])
def list_exposed_workflows(
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_user_or_api_key(permission=Permission.VIEW_WORKFLOWS, api_scope="workflows:read")),
):
    workflows = (
        db.query(Workflow)
        .filter(Workflow.is_exposed.is_(True), Workflow.deleted_at.is_(None), Workflow.expose_slug.isnot(None))
        .order_by(Workflow.name.asc())
        .all()
    )
    return [_to_summary(w) for w in workflows]


@router.get("/exposed/workflows/{slug}", response_model=ExposedWorkflowDetail)
def get_exposed_workflow(
    slug: str,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_user_or_api_key(permission=Permission.VIEW_WORKFLOWS, api_scope="workflows:read")),
):
    workflow = (
        db.query(Workflow)
        .filter(
            Workflow.expose_slug == slug,
            Workflow.is_exposed.is_(True),
            Workflow.deleted_at.is_(None),
        )
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=404, detail="Exposed workflow not found")
    service = WorkflowService(db)
    definition = service.get_definition(workflow)
    summary = _to_summary(workflow)
    return ExposedWorkflowDetail(
        **summary.model_dump(),
        invoke_path=f"/api/exposed/workflows/{slug}/invoke",
        variables=definition.variables or {},
    )


@router.post("/exposed/workflows/{slug}/invoke", status_code=status.HTTP_201_CREATED)
def invoke_exposed_workflow(
    slug: str,
    payload: RunRequest,
    db: Session = Depends(get_db),
    auth: dict = Depends(require_user_or_api_key(permission=Permission.RUN_WORKFLOWS, api_scope="exposed:invoke")),
):
    workflow = (
        db.query(Workflow)
        .filter(
            Workflow.expose_slug == slug,
            Workflow.is_exposed.is_(True),
            Workflow.deleted_at.is_(None),
        )
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=404, detail="Exposed workflow not found")
    version = (
        db.query(WorkflowVersion)
        .filter(
            WorkflowVersion.workflow_id == workflow.id,
            WorkflowVersion.version == workflow.current_version,
        )
        .one()
    )
    env_vars = {}
    if payload.environment_id:
        env = db.get(Environment, payload.environment_id)
        if env:
            env_vars = env.variables or {}
    triggered_by = auth["user"].id if auth.get("user") else workflow.owner_id
    engine = WorkflowEngine(db)
    run = engine.start_run(
        workflow=workflow,
        version=version,
        triggered_by=triggered_by,
        inputs=payload.inputs,
        trigger_type=payload.trigger_type or "api",
        environment_variables=env_vars,
    )
    return {"id": str(run.id), "status": run.status, "workflow_id": str(workflow.id), "slug": slug}
