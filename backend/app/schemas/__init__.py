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
    is_active: bool
    created_at: datetime


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
