from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import AgentJob, ExecutionAgent, NodeRun
from app.storage.service import sign_job_payload


class AgentJobService:
    """Queues signed jobs for external browser/CLI agents."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def select_agent(
        self,
        *,
        agent_type: str,
        required_tags: list[str] | None = None,
    ) -> ExecutionAgent | None:
        required = set(required_tags or [])
        agents = (
            self.db.query(ExecutionAgent)
            .filter(
                ExecutionAgent.agent_type == agent_type,
                ExecutionAgent.is_enabled.is_(True),
                ExecutionAgent.status.in_(["idle", "busy", "online"]),
            )
            .all()
        )
        candidates = []
        for agent in agents:
            tags = set(agent.tags or [])
            if required and not required.issubset(tags):
                continue
            if agent.current_workload >= agent.max_workload:
                continue
            # Prefer recent heartbeats
            heartbeat = agent.last_heartbeat_at or datetime.min.replace(tzinfo=UTC)
            candidates.append((heartbeat, agent))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def enqueue_job(
        self,
        *,
        run_id: UUID,
        node_run: NodeRun,
        job_type: str,
        payload: dict[str, Any],
        required_tags: list[str] | None = None,
        agent: ExecutionAgent | None = None,
    ) -> AgentJob:
        job_payload = {
            "jobId": str(uuid4()),
            "runId": str(run_id),
            "nodeRunId": str(node_run.id),
            "nodeId": node_run.node_id,
            "jobType": job_type,
            "payload": payload,
            "issuedAt": datetime.now(UTC).isoformat(),
        }
        signature = sign_job_payload(job_payload, self.settings.agent_job_signing_secret)
        job = AgentJob(
            id=UUID(job_payload["jobId"]),
            agent_id=agent.id if agent else None,
            run_id=run_id,
            node_run_id=node_run.id,
            job_type=job_type,
            status="queued",
            payload=job_payload,
            signature=signature,
            required_tags=required_tags or [],
        )
        self.db.add(job)
        self.db.flush()
        return job

    def wait_for_job(self, job_id: UUID, timeout_seconds: float = 600) -> AgentJob:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            self.db.expire_all()
            job = self.db.get(AgentJob, job_id)
            if job and job.status in {"completed", "failed", "cancelled"}:
                return job
            time.sleep(0.5)
        job = self.db.get(AgentJob, job_id)
        if job:
            job.status = "failed"
            job.result = {
                "status": "failed",
                "failure_classification": "command_timeout",
                "error": "Agent job timed out",
            }
            self.db.add(job)
            self.db.commit()
            return job
        raise TimeoutError("Agent job disappeared")


class AgentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def register(self, data: dict[str, Any]) -> tuple[ExecutionAgent, str]:
        token = str(uuid4())
        agent = ExecutionAgent(
            name=data["name"],
            agent_type=data["agent_type"],
            operating_system=data["operating_system"],
            supported_shells=data.get("supported_shells") or [],
            tags=data.get("tags") or [],
            capabilities=data.get("capabilities") or [],
            version=data.get("version") or "1.0.0",
            profile=data.get("profile") or "restricted",
            max_workload=data.get("max_workload") or 2,
            token_hash=hash_password(token),
            status="online",
            last_heartbeat_at=datetime.now(UTC),
        )
        self.db.add(agent)
        self.db.flush()
        return agent, token

    def authenticate(self, agent_id: UUID, token: str) -> ExecutionAgent:
        from app.core.security import verify_password

        agent = self.db.get(ExecutionAgent, agent_id)
        if not agent or not agent.is_enabled or not verify_password(token, agent.token_hash):
            raise PermissionError("Invalid agent credentials")
        return agent

    def heartbeat(self, agent: ExecutionAgent, status: str, workload: int, meta: dict[str, Any]) -> ExecutionAgent:
        agent.status = status
        agent.current_workload = workload
        agent.meta = meta
        agent.last_heartbeat_at = datetime.now(UTC)
        self.db.add(agent)
        self.db.flush()
        return agent

    def claim_job(self, agent: ExecutionAgent) -> AgentJob | None:
        query = (
            self.db.query(AgentJob)
            .filter(AgentJob.status == "queued", AgentJob.job_type.startswith(agent.agent_type))
            .order_by(AgentJob.created_at.asc())
        )
        for job in query.all():
            required = set(job.required_tags or [])
            if required and not required.issubset(set(agent.tags or [])):
                continue
            if job.agent_id and job.agent_id != agent.id:
                continue
            job.agent_id = agent.id
            job.status = "running"
            job.claimed_at = datetime.now(UTC)
            agent.current_workload += 1
            agent.status = "busy"
            self.db.add(job)
            self.db.add(agent)
            self.db.flush()
            return job
        return None

    def complete_job(
        self,
        agent: ExecutionAgent,
        job_id: UUID,
        status: str,
        result: dict[str, Any],
        logs: list[str],
    ) -> AgentJob:
        job = self.db.get(AgentJob, job_id)
        if not job or job.agent_id != agent.id:
            raise PermissionError("Job not claimed by this agent")
        job.status = "completed" if status == "passed" else status
        job.result = {**result, "logs": logs}
        job.completed_at = datetime.now(UTC)
        agent.current_workload = max(0, agent.current_workload - 1)
        agent.status = "idle" if agent.current_workload == 0 else "busy"
        self.db.add(job)
        self.db.add(agent)
        self.db.flush()
        return job
