from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.engine.graph import validate_workflow_graph
from app.models import Workflow, WorkflowEdge, WorkflowNode, WorkflowVariable, WorkflowVersion
from app.schemas import WorkflowDefinition
from app.services.audit import AuditService


class WorkflowService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditService(db)

    def create(self, *, owner_id: UUID, payload: dict[str, Any]) -> Workflow:
        definition = payload.get("definition") or self._default_definition(payload["name"])
        if isinstance(definition, WorkflowDefinition):
            definition_data = definition.model_dump()
        else:
            definition_data = WorkflowDefinition.model_validate(definition).model_dump()

        workflow = Workflow(
            name=payload["name"],
            description=payload.get("description"),
            owner_id=owner_id,
            tags=payload.get("tags") or [],
            trigger_type=payload.get("trigger_type") or "manual",
            current_version=1,
        )
        self.db.add(workflow)
        self.db.flush()
        definition_data["id"] = str(workflow.id)
        definition_data["version"] = 1
        self._persist_version(workflow, definition_data, owner_id, changelog="Initial version")
        self.audit.record(
            action="workflow.created",
            resource_type="workflow",
            resource_id=str(workflow.id),
            actor_id=owner_id,
            details={"name": workflow.name},
        )
        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def list_workflows(self) -> list[Workflow]:
        return (
            self.db.query(Workflow)
            .filter(Workflow.deleted_at.is_(None))
            .order_by(Workflow.updated_at.desc())
            .all()
        )

    def get(self, workflow_id: UUID) -> Workflow | None:
        workflow = self.db.get(Workflow, workflow_id)
        if not workflow or workflow.deleted_at:
            return None
        return workflow

    def get_definition(self, workflow: Workflow) -> WorkflowDefinition:
        version = (
            self.db.query(WorkflowVersion)
            .filter(
                WorkflowVersion.workflow_id == workflow.id,
                WorkflowVersion.version == workflow.current_version,
            )
            .one()
        )
        return WorkflowDefinition.model_validate(version.definition)

    def update(self, *, workflow: Workflow, actor_id: UUID, payload: dict[str, Any]) -> Workflow:
        if payload.get("name") is not None:
            workflow.name = payload["name"]
        if payload.get("description") is not None:
            workflow.description = payload["description"]
        if payload.get("tags") is not None:
            workflow.tags = payload["tags"]
        if payload.get("trigger_type") is not None:
            workflow.trigger_type = payload["trigger_type"]

        if payload.get("definition") is not None:
            definition = WorkflowDefinition.model_validate(payload["definition"]).model_dump()
            workflow.current_version += 1
            definition["id"] = str(workflow.id)
            definition["version"] = workflow.current_version
            definition["name"] = workflow.name
            self._persist_version(
                workflow,
                definition,
                actor_id,
                changelog=f"Version {workflow.current_version}",
            )

        workflow.updated_at = datetime.now(UTC)
        self.db.add(workflow)
        self.audit.record(
            action="workflow.modified",
            resource_type="workflow",
            resource_id=str(workflow.id),
            actor_id=actor_id,
        )
        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def soft_delete(self, workflow: Workflow, actor_id: UUID) -> None:
        workflow.deleted_at = datetime.now(UTC)
        self.db.add(workflow)
        self.audit.record(
            action="workflow.deleted",
            resource_type="workflow",
            resource_id=str(workflow.id),
            actor_id=actor_id,
        )
        self.db.commit()

    def clone(self, workflow: Workflow, actor_id: UUID) -> Workflow:
        definition = self.get_definition(workflow).model_dump()
        definition["name"] = f"{workflow.name} (Copy)"
        return self.create(
            owner_id=actor_id,
            payload={
                "name": definition["name"],
                "description": workflow.description,
                "definition": definition,
                "tags": workflow.tags,
                "trigger_type": workflow.trigger_type,
            },
        )

    def export(self, workflow: Workflow) -> dict[str, Any]:
        definition = self.get_definition(workflow).model_dump()
        # Strip secret values; keep secret references only
        variables = {}
        for key, value in (definition.get("variables") or {}).items():
            if isinstance(value, str) and value.startswith("{{secret."):
                variables[key] = value
            elif "password" in key.lower() or "secret" in key.lower():
                variables[key] = "{{secret.REDACTED}}"
            else:
                variables[key] = value
        definition["variables"] = variables
        return definition

    def import_definition(self, actor_id: UUID, definition: dict[str, Any]) -> Workflow:
        parsed = WorkflowDefinition.model_validate(definition)
        return self.create(
            owner_id=actor_id,
            payload={
                "name": parsed.name,
                "description": parsed.description,
                "definition": parsed,
                "tags": parsed.tags,
                "trigger_type": parsed.trigger_type,
            },
        )

    def validate(self, workflow: Workflow) -> Any:
        return validate_workflow_graph(self.get_definition(workflow))

    def _persist_version(
        self,
        workflow: Workflow,
        definition: dict[str, Any],
        actor_id: UUID,
        changelog: str,
    ) -> WorkflowVersion:
        version = WorkflowVersion(
            workflow_id=workflow.id,
            version=workflow.current_version,
            definition=definition,
            changelog=changelog,
            created_by=actor_id,
        )
        self.db.add(version)
        self.db.flush()
        for node in definition.get("nodes") or []:
            self.db.add(
                WorkflowNode(
                    version_id=version.id,
                    node_key=node["id"],
                    type=node["type"],
                    name=node["name"],
                    config=node.get("config") or {},
                    position_x=node.get("position", {}).get("x", 0),
                    position_y=node.get("position", {}).get("y", 0),
                )
            )
        for edge in definition.get("edges") or []:
            self.db.add(
                WorkflowEdge(
                    version_id=version.id,
                    edge_key=edge["id"],
                    source=edge["source"],
                    target=edge["target"],
                    source_handle=edge.get("sourceHandle"),
                    target_handle=edge.get("targetHandle"),
                    label=edge.get("label"),
                )
            )
        for key, value in (definition.get("variables") or {}).items():
            self.db.add(
                WorkflowVariable(
                    workflow_id=workflow.id,
                    key=key,
                    value=value,
                    is_secret_ref=isinstance(value, str) and "secret." in value,
                )
            )
        return version

    def _default_definition(self, name: str) -> dict[str, Any]:
        start_id = f"node-{uuid4().hex[:8]}"
        end_id = f"node-{uuid4().hex[:8]}"
        return {
            "name": name,
            "version": 1,
            "description": "",
            "variables": {},
            "nodes": [
                {
                    "id": start_id,
                    "type": "start",
                    "name": "Start",
                    "config": {},
                    "position": {"x": 80, "y": 120},
                },
                {
                    "id": end_id,
                    "type": "end",
                    "name": "End",
                    "config": {},
                    "position": {"x": 420, "y": 120},
                },
            ],
            "edges": [
                {
                    "id": f"edge-{uuid4().hex[:8]}",
                    "source": start_id,
                    "target": end_id,
                }
            ],
            "tags": [],
            "trigger_type": "manual",
        }
