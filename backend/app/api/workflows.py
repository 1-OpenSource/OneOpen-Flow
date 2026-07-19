from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_permission
from app.core.permissions import Permission
from app.db.database import get_db
from app.engine.orchestrator import WorkflowEngine
from app.models import Environment, User, Workflow, WorkflowVersion
from app.schemas import (
    RunRequest,
    ValidationResult,
    WorkflowCreate,
    WorkflowDefinition,
    WorkflowDetail,
    WorkflowSummary,
    WorkflowUpdate,
)
from app.services.workflows import WorkflowService

router = APIRouter(prefix="/workflows", tags=["workflows"])


def _detail(service: WorkflowService, workflow: Workflow) -> WorkflowDetail:
    definition = service.get_definition(workflow)
    return WorkflowDetail(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        current_version=workflow.current_version,
        owner_id=workflow.owner_id,
        tags=workflow.tags,
        trigger_type=workflow.trigger_type,
        last_run_at=workflow.last_run_at,
        last_status=workflow.last_status,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
        definition=definition,
    )


@router.post("", response_model=WorkflowDetail, status_code=status.HTTP_201_CREATED)
def create_workflow(
    payload: WorkflowCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.EDIT_WORKFLOWS)),
) -> WorkflowDetail:
    service = WorkflowService(db)
    workflow = service.create(owner_id=user.id, payload=payload.model_dump())
    return _detail(service, workflow)


@router.get("", response_model=list[WorkflowSummary])
def list_workflows(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.VIEW_WORKFLOWS)),
) -> list[Workflow]:
    return WorkflowService(db).list_workflows()


@router.get("/{workflow_id}", response_model=WorkflowDetail)
def get_workflow(
    workflow_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.VIEW_WORKFLOWS)),
) -> WorkflowDetail:
    service = WorkflowService(db)
    workflow = service.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return _detail(service, workflow)


@router.put("/{workflow_id}", response_model=WorkflowDetail)
def update_workflow(
    workflow_id: UUID,
    payload: WorkflowUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.EDIT_WORKFLOWS)),
) -> WorkflowDetail:
    service = WorkflowService(db)
    workflow = service.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    workflow = service.update(
        workflow=workflow,
        actor_id=user.id,
        payload=payload.model_dump(exclude_unset=True),
    )
    return _detail(service, workflow)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(
    workflow_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.EDIT_WORKFLOWS)),
) -> None:
    service = WorkflowService(db)
    workflow = service.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    service.soft_delete(workflow, user.id)


@router.post("/{workflow_id}/validate", response_model=ValidationResult)
def validate_workflow(
    workflow_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.VIEW_WORKFLOWS)),
) -> ValidationResult:
    service = WorkflowService(db)
    workflow = service.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return service.validate(workflow)


@router.post("/{workflow_id}/run", status_code=status.HTTP_201_CREATED)
def run_workflow(
    workflow_id: UUID,
    payload: RunRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RUN_WORKFLOWS)),
):
    service = WorkflowService(db)
    workflow = service.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
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
    engine = WorkflowEngine(db)
    run = engine.start_run(
        workflow=workflow,
        version=version,
        triggered_by=user.id,
        inputs=payload.inputs,
        trigger_type=payload.trigger_type,
        environment_variables=env_vars,
    )
    return {"id": str(run.id), "status": run.status}


@router.post("/{workflow_id}/clone", response_model=WorkflowDetail, status_code=status.HTTP_201_CREATED)
def clone_workflow(
    workflow_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.EDIT_WORKFLOWS)),
) -> WorkflowDetail:
    service = WorkflowService(db)
    workflow = service.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    cloned = service.clone(workflow, user.id)
    return _detail(service, cloned)


@router.post("/import", response_model=WorkflowDetail, status_code=status.HTTP_201_CREATED)
def import_workflow(
    definition: WorkflowDefinition,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.EDIT_WORKFLOWS)),
) -> WorkflowDetail:
    service = WorkflowService(db)
    workflow = service.import_definition(user.id, definition.model_dump())
    return _detail(service, workflow)


@router.get("/{workflow_id}/export")
def export_workflow(
    workflow_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.VIEW_WORKFLOWS)),
):
    service = WorkflowService(db)
    workflow = service.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return JSONResponse(service.export(workflow))
