import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.database import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    tags: Mapped[list[Any]] = mapped_column(JSONType, nullable=False, default=list)
    trigger_type: Mapped[str] = mapped_column(String(60), nullable=False, default="manual")
    is_exposed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expose_slug: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True, index=True)
    expose_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    owner = relationship("User", back_populates="workflows")
    versions = relationship("WorkflowVersion", back_populates="workflow", cascade="all, delete-orphan")
    runs = relationship("WorkflowRun", back_populates="workflow", cascade="all, delete-orphan")
    triggers = relationship("WorkflowTrigger", back_populates="workflow", cascade="all, delete-orphan")
    variables = relationship("WorkflowVariable", back_populates="workflow", cascade="all, delete-orphan")


class WorkflowVersion(Base):
    __tablename__ = "workflow_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workflow = relationship("Workflow", back_populates="versions")
    nodes = relationship("WorkflowNode", back_populates="version", cascade="all, delete-orphan")
    edges = relationship("WorkflowEdge", back_populates="version", cascade="all, delete-orphan")


class WorkflowNode(Base):
    __tablename__ = "workflow_nodes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_versions.id"), nullable=False, index=True
    )
    node_key: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    position_x: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    position_y: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    version = relationship("WorkflowVersion", back_populates="nodes")


class WorkflowEdge(Base):
    __tablename__ = "workflow_edges"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_versions.id"), nullable=False, index=True
    )
    edge_key: Mapped[str] = mapped_column(String(120), nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    target: Mapped[str] = mapped_column(String(120), nullable=False)
    source_handle: Mapped[str | None] = mapped_column(String(80), nullable=True)
    target_handle: Mapped[str | None] = mapped_column(String(80), nullable=True)
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)

    version = relationship("WorkflowVersion", back_populates="edges")


class WorkflowVariable(Base):
    __tablename__ = "workflow_variables"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[Any] = mapped_column(JSONType, nullable=True)
    is_secret_ref: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    workflow = relationship("Workflow", back_populates="variables")


class WorkflowTrigger(Base):
    __tablename__ = "workflow_triggers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id"), nullable=False, index=True)
    trigger_type: Mapped[str] = mapped_column(String(60), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workflow = relationship("Workflow", back_populates="triggers")
