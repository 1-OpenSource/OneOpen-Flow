import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.database import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


class ExecutionAgent(Base):
    __tablename__ = "execution_agents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(40), nullable=False)  # browser | cli
    operating_system: Mapped[str] = mapped_column(String(80), nullable=False)
    supported_shells: Mapped[list[Any]] = mapped_column(JSONType, nullable=False, default=list)
    tags: Mapped[list[Any]] = mapped_column(JSONType, nullable=False, default=list)
    capabilities: Mapped[list[Any]] = mapped_column(JSONType, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="offline")
    version: Mapped[str] = mapped_column(String(40), nullable=False, default="1.0.0")
    current_workload: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_workload: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    profile: Mapped[str] = mapped_column(String(40), nullable=False, default="restricted")
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    agent_capabilities = relationship(
        "AgentCapability", back_populates="agent", cascade="all, delete-orphan"
    )


class AgentCapability(Base):
    __tablename__ = "agent_capabilities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("execution_agents.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)

    agent = relationship("ExecutionAgent", back_populates="agent_capabilities")


class AgentJob(Base):
    __tablename__ = "agent_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("execution_agents.id"), nullable=True, index=True
    )
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_runs.id"), nullable=False, index=True)
    node_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("node_runs.id"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="queued")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    signature: Mapped[str] = mapped_column(String(255), nullable=False)
    required_tags: Mapped[list[Any]] = mapped_column(JSONType, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
