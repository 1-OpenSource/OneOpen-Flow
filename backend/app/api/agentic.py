from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_user_or_api_key
from app.core.permissions import Permission
from app.db.database import get_db
from app.models import Workflow
from app.schemas import AgenticCatalog, AgenticTool, ExposedWorkflowSummary

router = APIRouter(prefix="/agentic", tags=["agentic"])


AGENTIC_TOOLS: list[AgenticTool] = [
    AgenticTool(
        name="list_workflows",
        description="List all workflows",
        method="GET",
        path="/api/workflows",
        permission=Permission.VIEW_WORKFLOWS.value,
    ),
    AgenticTool(
        name="get_workflow",
        description="Get workflow definition by id",
        method="GET",
        path="/api/workflows/{workflow_id}",
        permission=Permission.VIEW_WORKFLOWS.value,
    ),
    AgenticTool(
        name="create_workflow",
        description="Create a workflow",
        method="POST",
        path="/api/workflows",
        permission=Permission.EDIT_WORKFLOWS.value,
        body_schema={"name": "string", "description": "string", "definition": "object"},
    ),
    AgenticTool(
        name="update_workflow",
        description="Update workflow metadata or definition",
        method="PUT",
        path="/api/workflows/{workflow_id}",
        permission=Permission.EDIT_WORKFLOWS.value,
    ),
    AgenticTool(
        name="delete_workflow",
        description="Soft-delete a workflow",
        method="DELETE",
        path="/api/workflows/{workflow_id}",
        permission=Permission.EDIT_WORKFLOWS.value,
    ),
    AgenticTool(
        name="validate_workflow",
        description="Validate workflow graph",
        method="POST",
        path="/api/workflows/{workflow_id}/validate",
        permission=Permission.VIEW_WORKFLOWS.value,
    ),
    AgenticTool(
        name="run_workflow",
        description="Start a workflow run",
        method="POST",
        path="/api/workflows/{workflow_id}/run",
        permission=Permission.RUN_WORKFLOWS.value,
        body_schema={"inputs": "object", "environment_id": "uuid?"},
    ),
    AgenticTool(
        name="clone_workflow",
        description="Clone a workflow",
        method="POST",
        path="/api/workflows/{workflow_id}/clone",
        permission=Permission.EDIT_WORKFLOWS.value,
    ),
    AgenticTool(
        name="export_workflow",
        description="Export workflow JSON",
        method="GET",
        path="/api/workflows/{workflow_id}/export",
        permission=Permission.VIEW_WORKFLOWS.value,
    ),
    AgenticTool(
        name="import_workflow",
        description="Import workflow JSON",
        method="POST",
        path="/api/workflows/import",
        permission=Permission.EDIT_WORKFLOWS.value,
    ),
    AgenticTool(
        name="expose_workflow",
        description="Publish/expose a workflow for agentic discovery and invoke",
        method="PUT",
        path="/api/workflows/{workflow_id}/expose",
        permission=Permission.EXPOSE_WORKFLOWS.value,
        body_schema={"enabled": "boolean", "slug": "string", "description": "string", "input_schema": "object"},
    ),
    AgenticTool(
        name="list_exposed_workflows",
        description="List workflows exposed for agentic use",
        method="GET",
        path="/api/exposed/workflows",
        permission=Permission.VIEW_WORKFLOWS.value,
    ),
    AgenticTool(
        name="get_exposed_workflow",
        description="Get exposed workflow schema and invoke path",
        method="GET",
        path="/api/exposed/workflows/{slug}",
        permission=Permission.VIEW_WORKFLOWS.value,
    ),
    AgenticTool(
        name="invoke_exposed_workflow",
        description="Invoke an exposed workflow by slug",
        method="POST",
        path="/api/exposed/workflows/{slug}/invoke",
        permission=Permission.RUN_WORKFLOWS.value,
        body_schema={"inputs": "object"},
    ),
    AgenticTool(
        name="list_runs",
        description="List workflow runs",
        method="GET",
        path="/api/runs",
        permission=Permission.VIEW_WORKFLOWS.value,
    ),
    AgenticTool(
        name="get_run",
        description="Get run details including node runs and artifacts",
        method="GET",
        path="/api/runs/{run_id}",
        permission=Permission.VIEW_WORKFLOWS.value,
    ),
    AgenticTool(
        name="cancel_run",
        description="Cancel a running workflow",
        method="POST",
        path="/api/runs/{run_id}/cancel",
        permission=Permission.RUN_WORKFLOWS.value,
    ),
    AgenticTool(
        name="retry_run",
        description="Retry a failed run",
        method="POST",
        path="/api/runs/{run_id}/retry",
        permission=Permission.RUN_WORKFLOWS.value,
    ),
    AgenticTool(
        name="retry_from_node",
        description="Retry from a specific node",
        method="POST",
        path="/api/runs/{run_id}/retry-from-node",
        permission=Permission.RUN_WORKFLOWS.value,
        body_schema={"node_id": "string"},
    ),
    AgenticTool(
        name="provide_input",
        description="Provide human-in-the-loop input (OTP, etc.)",
        method="POST",
        path="/api/runs/{run_id}/provide-input",
        permission=Permission.RUN_WORKFLOWS.value,
        body_schema={"otp": "string?", "value": "string?", "inputs": "object"},
    ),
    AgenticTool(
        name="download_evidence",
        description="Download run evidence ZIP",
        method="GET",
        path="/api/runs/{run_id}/evidence",
        permission=Permission.VIEW_WORKFLOWS.value,
    ),
    AgenticTool(
        name="create_work_item",
        description="Create a Workboard defect from a failed run",
        method="POST",
        path="/api/runs/{run_id}/create-work-item",
        permission=Permission.CREATE_WORKBOARD_DEFECTS.value,
    ),
    AgenticTool(
        name="list_agents",
        description="List execution agents",
        method="GET",
        path="/api/agents",
        permission=Permission.VIEW_WORKFLOWS.value,
    ),
    AgenticTool(
        name="update_agent",
        description="Enable/disable or update an agent",
        method="PATCH",
        path="/api/agents/{agent_id}",
        permission=Permission.MANAGE_AGENTS.value,
    ),
    AgenticTool(
        name="list_secrets",
        description="List secret metadata",
        method="GET",
        path="/api/secrets",
        permission=Permission.MANAGE_SECRETS.value,
    ),
    AgenticTool(
        name="create_secret",
        description="Create a secret",
        method="POST",
        path="/api/secrets",
        permission=Permission.MANAGE_SECRETS.value,
    ),
    AgenticTool(
        name="update_secret",
        description="Rotate/update a secret",
        method="PUT",
        path="/api/secrets/{secret_id}",
        permission=Permission.MANAGE_SECRETS.value,
    ),
    AgenticTool(
        name="list_environments",
        description="List environments",
        method="GET",
        path="/api/environments",
        permission=Permission.VIEW_WORKFLOWS.value,
    ),
    AgenticTool(
        name="create_environment",
        description="Create an environment",
        method="POST",
        path="/api/environments",
        permission=Permission.EDIT_WORKFLOWS.value,
    ),
    AgenticTool(
        name="update_environment",
        description="Update an environment",
        method="PUT",
        path="/api/environments/{environment_id}",
        permission=Permission.EDIT_WORKFLOWS.value,
    ),
    AgenticTool(
        name="list_users",
        description="Admin: list users",
        method="GET",
        path="/api/admin/users",
        permission=Permission.MANAGE_USERS.value,
    ),
    AgenticTool(
        name="update_user",
        description="Admin: update user role or active flag",
        method="PATCH",
        path="/api/admin/users/{user_id}",
        permission=Permission.MANAGE_USERS.value,
    ),
]


@router.get("/catalog", response_model=AgenticCatalog)
def agentic_catalog(
    db: Session = Depends(get_db),
    _auth: dict = Depends(
        require_user_or_api_key(permission=Permission.VIEW_WORKFLOWS, api_scope="workflows:read")
    ),
) -> AgenticCatalog:
    exposed = (
        db.query(Workflow)
        .filter(Workflow.is_exposed.is_(True), Workflow.deleted_at.is_(None), Workflow.expose_slug.isnot(None))
        .order_by(Workflow.name.asc())
        .all()
    )
    return AgenticCatalog(
        auth={
            "recommended": "service_account",
            "service_account": (
                "Create via POST /api/admin/service-accounts (admin UI: Admin → Service accounts). "
                "Send Authorization: Bearer <client_secret> or X-API-Key: <client_secret>. "
                "Token prefix is oof_…"
            ),
            "user_jwt": "Authorization: Bearer <access_token> from POST /api/auth/login (human operators)",
            "scopes": ["workflows:read", "workflows:run", "exposed:invoke", "*"],
        },
        tools=AGENTIC_TOOLS,
        exposed_workflows=[
            ExposedWorkflowSummary(
                id=w.id,
                name=w.name,
                slug=w.expose_slug or "",
                description=w.expose_description or w.description,
                input_schema=w.input_schema or {},
                tags=w.tags or [],
                current_version=w.current_version,
            )
            for w in exposed
        ],
    )
