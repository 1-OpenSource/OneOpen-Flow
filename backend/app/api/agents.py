from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_permission
from app.core.permissions import Permission
from app.core.security import encrypt_secret
from app.db.database import get_db
from app.models import Environment, ExecutionAgent, Secret, User
from app.schemas import (
    AgentHeartbeatRequest,
    AgentRead,
    AgentRegisterRequest,
    AgentRegisterResponse,
    AgentUpdate,
    ClaimJobResponse,
    CompleteJobRequest,
    EnvironmentCreate,
    EnvironmentRead,
    EnvironmentUpdate,
    SecretCreate,
    SecretRead,
    SecretUpdate,
)
from app.services.agents import AgentService
from app.services.audit import AuditService
from datetime import UTC, datetime

router = APIRouter(tags=["agents-secrets-environments"])


def _agent_from_auth(db: Session, agent_id: UUID, x_agent_token: str | None) -> ExecutionAgent:
    if not x_agent_token:
        raise HTTPException(status_code=401, detail="Missing agent token")
    try:
        return AgentService(db).authenticate(agent_id, x_agent_token)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.post("/agents/register", response_model=AgentRegisterResponse, status_code=status.HTTP_201_CREATED)
def register_agent(payload: AgentRegisterRequest, db: Session = Depends(get_db)):
    agent, token = AgentService(db).register(payload.model_dump())
    AuditService(db).record(
        action="agent.registered",
        resource_type="execution_agent",
        resource_id=str(agent.id),
        details={"name": agent.name, "type": agent.agent_type},
    )
    db.commit()
    return AgentRegisterResponse(
        id=agent.id,
        token=token,
        name=agent.name,
        agent_type=agent.agent_type,
    )


@router.post("/agents/heartbeat")
def heartbeat(
    payload: AgentHeartbeatRequest,
    db: Session = Depends(get_db),
    x_agent_id: UUID | None = Header(default=None),
    x_agent_token: str | None = Header(default=None),
):
    if not x_agent_id:
        raise HTTPException(status_code=400, detail="X-Agent-Id required")
    agent = _agent_from_auth(db, x_agent_id, x_agent_token)
    AgentService(db).heartbeat(agent, payload.status, payload.current_workload, payload.meta)
    db.commit()
    return {"status": "ok"}


@router.post("/agents/{agent_id}/claim-job", response_model=ClaimJobResponse)
def claim_job(
    agent_id: UUID,
    db: Session = Depends(get_db),
    x_agent_token: str | None = Header(default=None),
):
    agent = _agent_from_auth(db, agent_id, x_agent_token)
    job = AgentService(db).claim_job(agent)
    db.commit()
    if not job:
        return ClaimJobResponse(job=None)
    return ClaimJobResponse(
        job={
            "id": str(job.id),
            "signature": job.signature,
            "payload": job.payload,
            "requiredTags": job.required_tags,
        }
    )


@router.post("/agents/{agent_id}/complete-job")
def complete_job(
    agent_id: UUID,
    payload: CompleteJobRequest,
    job_id: UUID,
    db: Session = Depends(get_db),
    x_agent_token: str | None = Header(default=None),
):
    agent = _agent_from_auth(db, agent_id, x_agent_token)
    job = AgentService(db).complete_job(agent, job_id, payload.status, payload.result, payload.logs)
    AuditService(db).record(
        action="cli.command.executed" if agent.agent_type == "cli" else "browser.action.executed",
        resource_type="agent_job",
        resource_id=str(job.id),
        details={"agentId": str(agent.id), "status": payload.status},
    )
    db.commit()
    return {"status": job.status}


@router.get("/agents", response_model=list[AgentRead])
def list_agents(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.VIEW_WORKFLOWS)),
):
    return db.query(ExecutionAgent).order_by(ExecutionAgent.created_at.desc()).all()


@router.patch("/agents/{agent_id}", response_model=AgentRead)
def update_agent(
    agent_id: UUID,
    payload: AgentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_AGENTS)),
):
    agent = db.get(ExecutionAgent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(agent, key, value)
    db.add(agent)
    AuditService(db).record(
        action="agent.updated",
        resource_type="execution_agent",
        resource_id=str(agent.id),
        actor_id=user.id,
        details=data,
    )
    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_AGENTS)),
):
    agent = db.get(ExecutionAgent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.is_enabled = False
    db.add(agent)
    AuditService(db).record(
        action="agent.revoked",
        resource_type="execution_agent",
        resource_id=str(agent.id),
        actor_id=user.id,
    )
    db.commit()


@router.post("/secrets", response_model=SecretRead, status_code=status.HTTP_201_CREATED)
def create_secret(
    payload: SecretCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_SECRETS)),
):
    existing = db.query(Secret).filter(Secret.name == payload.name, Secret.deleted_at.is_(None)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Secret name already exists")
    secret = Secret(
        name=payload.name,
        description=payload.description,
        encrypted_value=encrypt_secret(payload.value),
        created_by=user.id,
    )
    db.add(secret)
    AuditService(db).record(
        action="secret.created",
        resource_type="secret",
        resource_id=payload.name,
        actor_id=user.id,
    )
    db.commit()
    db.refresh(secret)
    return secret


@router.get("/secrets", response_model=list[SecretRead])
def list_secrets(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_SECRETS)),
):
    return db.query(Secret).filter(Secret.deleted_at.is_(None)).order_by(Secret.name.asc()).all()


@router.delete("/secrets/{secret_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_secret(
    secret_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_SECRETS)),
):
    secret = db.get(Secret, secret_id)
    if not secret or secret.deleted_at:
        raise HTTPException(status_code=404, detail="Secret not found")
    secret.deleted_at = datetime.now(UTC)
    db.add(secret)
    AuditService(db).record(
        action="secret.deleted",
        resource_type="secret",
        resource_id=str(secret.id),
        actor_id=user.id,
    )
    db.commit()


@router.put("/secrets/{secret_id}", response_model=SecretRead)
def update_secret(
    secret_id: UUID,
    payload: SecretUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_SECRETS)),
):
    secret = db.get(Secret, secret_id)
    if not secret or secret.deleted_at:
        raise HTTPException(status_code=404, detail="Secret not found")
    if payload.value is not None:
        secret.encrypted_value = encrypt_secret(payload.value)
    if payload.description is not None:
        secret.description = payload.description
    db.add(secret)
    AuditService(db).record(
        action="secret.updated",
        resource_type="secret",
        resource_id=str(secret.id),
        actor_id=user.id,
    )
    db.commit()
    db.refresh(secret)
    return secret


@router.post("/environments", response_model=EnvironmentRead, status_code=status.HTTP_201_CREATED)
def create_environment(
    payload: EnvironmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.EDIT_WORKFLOWS)),
):
    env = Environment(
        name=payload.name,
        description=payload.description,
        variables=payload.variables,
        created_by=user.id,
    )
    db.add(env)
    db.commit()
    db.refresh(env)
    return env


@router.get("/environments", response_model=list[EnvironmentRead])
def list_environments(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.VIEW_WORKFLOWS)),
):
    return db.query(Environment).order_by(Environment.name.asc()).all()


@router.put("/environments/{environment_id}", response_model=EnvironmentRead)
def update_environment(
    environment_id: UUID,
    payload: EnvironmentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.EDIT_WORKFLOWS)),
):
    env = db.get(Environment, environment_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(env, key, value)
    db.add(env)
    db.commit()
    db.refresh(env)
    return env


@router.delete("/environments/{environment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_environment(
    environment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.EDIT_WORKFLOWS)),
):
    env = db.get(Environment, environment_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    db.delete(env)
    db.commit()
