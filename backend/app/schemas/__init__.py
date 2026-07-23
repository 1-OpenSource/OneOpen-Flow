from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    name: str
    email: str
    password: str


class UserRead(ORMModel):
    id: UUID
    name: str
    email: str
    role: str
    auth_provider: str = "local"
    is_active: bool
    created_at: datetime


class UserAdminUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    name: str | None = None


class InviteCreate(BaseModel):
    email: str
    role: str = "member"


class InviteRead(ORMModel):
    id: UUID
    email: str
    role: str
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime


class InviteCreatedResponse(BaseModel):
    invite: InviteRead
    accept_token: str
    accept_url: str


class AcceptInviteRequest(BaseModel):
    token: str
    name: str
    password: str


class RolePermissionsRead(BaseModel):
    roles: dict[str, list[str]]
    permissions: list[str]


class ApiKeyCreate(BaseModel):
    name: str
    client_id: str | None = None
    description: str | None = None
    scopes: list[str] = Field(
        default_factory=lambda: ["workflows:run", "workflows:read", "exposed:invoke"]
    )
    expires_in_days: int | None = None


class ApiKeyRead(ORMModel):
    id: UUID
    name: str
    client_id: str = ""
    description: str | None = None
    prefix: str
    scopes: list[Any]
    is_active: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyCreatedResponse(BaseModel):
    key: ApiKeyRead
    token: str
    service_account: ApiKeyRead | None = None
    client_secret: str | None = None


class SsoPublicConfig(BaseModel):
    enabled: bool
    provider_name: str = "SSO"
    authorize_url: str | None = None
    allow_local_login: bool = True


class SsoAdminConfig(BaseModel):
    sso_enabled: bool = False
    sso_provider_name: str = "OIDC"
    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret_set: bool = False
    oidc_redirect_uri: str | None = None
    oidc_scopes: str = "openid profile email"
    oidc_default_role: str = "member"
    allow_local_login: bool = True


class SsoAdminUpdate(BaseModel):
    sso_enabled: bool | None = None
    sso_provider_name: str | None = None
    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    oidc_redirect_uri: str | None = None
    oidc_scopes: str | None = None
    oidc_default_role: str | None = None
    allow_local_login: bool | None = None


class WorkflowExposeRequest(BaseModel):
    enabled: bool = True
    slug: str | None = None
    description: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)


class ExposedWorkflowSummary(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    input_schema: dict[str, Any]
    tags: list[Any]
    current_version: int


class ExposedWorkflowDetail(ExposedWorkflowSummary):
    invoke_path: str
    variables: dict[str, Any] = Field(default_factory=dict)


class AgenticTool(BaseModel):
    name: str
    description: str
    method: str
    path: str
    permission: str | None = None
    body_schema: dict[str, Any] = Field(default_factory=dict)


class AgenticCatalog(BaseModel):
    version: str = "1.0"
    auth: dict[str, Any]
    tools: list[AgenticTool]
    exposed_workflows: list[ExposedWorkflowSummary]


class SecretUpdate(BaseModel):
    value: str | None = None
    description: str | None = None


class EnvironmentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    variables: dict[str, Any] | None = None


class AgentUpdate(BaseModel):
    is_enabled: bool | None = None
    tags: list[str] | None = None
    max_workload: int | None = None
    profile: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str
    password: str


class SetupStatus(BaseModel):
    needs_owner: bool


class Position(BaseModel):
    x: float = 0
    y: float = 0


class WorkflowNodeDefinition(BaseModel):
    id: str
    type: str
    name: str
    config: dict[str, Any] = Field(default_factory=dict)
    position: Position = Field(default_factory=Position)


class WorkflowEdgeDefinition(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: str | None = None
    targetHandle: str | None = None
    label: str | None = None


class WorkflowDefinition(BaseModel):
    id: str | None = None
    name: str
    version: int = 1
    description: str | None = None
    variables: dict[str, Any] = Field(default_factory=dict)
    nodes: list[WorkflowNodeDefinition] = Field(default_factory=list)
    edges: list[WorkflowEdgeDefinition] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    trigger_type: str = "manual"


class WorkflowCreate(BaseModel):
    name: str
    description: str | None = None
    definition: WorkflowDefinition | None = None
    tags: list[str] = Field(default_factory=list)
    trigger_type: str = "manual"


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    definition: WorkflowDefinition | None = None
    tags: list[str] | None = None
    trigger_type: str | None = None


class WorkflowSummary(ORMModel):
    id: UUID
    name: str
    description: str | None
    current_version: int
    owner_id: UUID
    tags: list[Any]
    trigger_type: str
    is_exposed: bool = False
    expose_slug: str | None = None
    expose_description: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)
    last_run_at: datetime | None
    last_status: str | None
    created_at: datetime
    updated_at: datetime


class WorkflowDetail(WorkflowSummary):
    definition: WorkflowDefinition


class ValidationIssue(BaseModel):
    severity: str
    code: str
    message: str
    node_id: str | None = None


class ValidationResult(BaseModel):
    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)


class RunRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)
    environment_id: UUID | None = None
    trigger_type: str = "manual"


class RetryFromNodeRequest(BaseModel):
    node_id: str


class ProvideInputRequest(BaseModel):
    """Human-in-the-loop input for paused runs (OTP, codes, free text)."""

    otp: str | None = None
    value: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)


class NodeRunRead(ORMModel):
    id: UUID
    node_id: str
    node_type: str
    node_name: str
    status: str
    attempt: int
    outputs: dict[str, Any]
    result: dict[str, Any]
    error: str | None
    failure_classification: str | None
    logs: list[Any]
    started_at: datetime | None
    ended_at: datetime | None
    duration_ms: int | None


class ArtifactRead(ORMModel):
    id: UUID
    name: str
    artifact_type: str
    storage_path: str
    content_type: str | None
    size_bytes: int | None
    created_at: datetime


class WorkflowRunRead(ORMModel):
    id: UUID
    workflow_id: UUID
    version: int
    status: str
    trigger_type: str
    inputs: dict[str, Any]
    variables: dict[str, Any]
    failure_classification: str | None
    failure_message: str | None
    recommended_action: str | None
    current_node_id: str | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_ms: int | None
    created_at: datetime
    node_runs: list[NodeRunRead] = Field(default_factory=list)
    artifacts: list[ArtifactRead] = Field(default_factory=list)


class AgentRegisterRequest(BaseModel):
    name: str
    agent_type: str
    operating_system: str
    supported_shells: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    version: str = "1.0.0"
    profile: str = "restricted"
    max_workload: int = 2
    registration_token: str | None = None


class AgentRegisterResponse(BaseModel):
    id: UUID
    token: str
    name: str
    agent_type: str


class AgentHeartbeatRequest(BaseModel):
    status: str = "idle"
    current_workload: int = 0
    meta: dict[str, Any] = Field(default_factory=dict)


class AgentRead(ORMModel):
    id: UUID
    name: str
    agent_type: str
    operating_system: str
    supported_shells: list[Any]
    tags: list[Any]
    capabilities: list[Any]
    status: str
    version: str
    current_workload: int
    max_workload: int
    profile: str
    last_heartbeat_at: datetime | None
    is_enabled: bool
    created_at: datetime


class ClaimJobResponse(BaseModel):
    job: dict[str, Any] | None


class CompleteJobRequest(BaseModel):
    status: str
    result: dict[str, Any] = Field(default_factory=dict)
    logs: list[str] = Field(default_factory=list)


class SecretCreate(BaseModel):
    name: str
    value: str
    description: str | None = None


class SecretRead(ORMModel):
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class EnvironmentCreate(BaseModel):
    name: str
    description: str | None = None
    variables: dict[str, Any] = Field(default_factory=dict)


class EnvironmentRead(ORMModel):
    id: UUID
    name: str
    description: str | None
    variables: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CreateWorkItemRequest(BaseModel):
    project_id: str | None = None
    title: str | None = None
    additional_notes: str | None = None


class WorkboardLinkRead(ORMModel):
    id: UUID
    run_id: UUID
    work_item_key: str
    work_item_id: str
    project_id: str | None
    status: str
    reproduction_url: str | None
    created_at: datetime


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int


class Page(BaseModel):
    items: list[Any]
    meta: PageMeta
