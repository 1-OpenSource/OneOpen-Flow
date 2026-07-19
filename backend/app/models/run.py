import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.database import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending", index=True)
    trigger_type: Mapped[str] = mapped_column(String(60), nullable=False, default="manual")
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    environment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("environments.id"), nullable=True)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    variables: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    failure_classification: Mapped[str | None] = mapped_column(String(80), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_node_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    retry_of_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workflow_runs.id"), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workflow = relationship("Workflow", back_populates="runs")
    node_runs = relationship("NodeRun", back_populates="run", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="run", cascade="all, delete-orphan")
    workboard_links = relationship("WorkboardLink", back_populates="run", cascade="all, delete-orphan")


class NodeRun(Base):
    __tablename__ = "node_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_runs.id"), nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    node_type: Mapped[str] = mapped_column(String(80), nullable=False)
    node_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending", index=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("execution_agents.id"), nullable=True)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    outputs: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_classification: Mapped[str | None] = mapped_column(String(80), nullable=True)
    logs: Mapped[list[Any]] = mapped_column(JSONType, nullable=False, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    run = relationship("WorkflowRun", back_populates="node_runs")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_runs.id"), nullable=False, index=True)
    node_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("node_runs.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(80), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run = relationship("WorkflowRun", back_populates="artifacts")


class WorkboardLink(Base):
    __tablename__ = "workboard_links"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_runs.id"), nullable=False, index=True)
    work_item_key: Mapped[str] = mapped_column(String(80), nullable=False)
    work_item_id: Mapped[str] = mapped_column(String(80), nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="open")
    reproduction_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    auto_retest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run = relationship("WorkflowRun", back_populates="workboard_links")
