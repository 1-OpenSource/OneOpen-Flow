from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decrypt_secret
from app.engine.events import event_broker
from app.engine.failures import classify_failure
from app.engine.graph import (
    build_variable_context,
    resolve_variables,
    validate_workflow_graph,
)
from app.executors.base import registry
from app.executors.builtin import register_builtin_executors
from app.models import (
    Artifact,
    NodeRun,
    Secret,
    Workflow,
    WorkflowRun,
    WorkflowVersion,
)
from app.schemas import WorkflowDefinition
from app.services.agents import AgentJobService
from app.services.audit import AuditService
from app.storage.service import StorageService

register_builtin_executors()

CLI_NODE_TYPES = {
    "cli",
    "run_bash",
    "run_powershell",
    "run_cmd",
    "run_python_script",
    "run_node_command",
    "run_custom_executable",
}

BROWSER_NODE_TYPES = {
    "browser",
    "open_url",
    "click",
    "fill_input",
    "select_option",
    "press_key",
    "wait_for_element",
    "wait_for_page_state",
    "wait_for_aspx_postback",
    "wait_for_react_render",
    "wait_for_element_stability",
    "wait_for_network_response",
    "wait_for_loading_indicator",
    "wait_for_route_change",
    "extract_text",
    "extract_attribute",
    "take_screenshot",
    "upload_file",
    "download_file",
    "switch_tab",
    "close_tab",
    "assert_visible",
    "assert_hidden",
    "assert_text",
    "assert_url",
    "assert_element_count",
    "assert_field_value",
    "execute_javascript",
}


class WorkflowEngine:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.storage = StorageService()
        self.audit = AuditService(db)
        self.agent_jobs = AgentJobService(db)

    def start_run(
        self,
        *,
        workflow: Workflow,
        version: WorkflowVersion,
        triggered_by: UUID | None,
        inputs: dict[str, Any],
        trigger_type: str = "manual",
        environment_variables: dict[str, Any] | None = None,
        retry_of_run_id: UUID | None = None,
        start_from_node: str | None = None,
    ) -> WorkflowRun:
        definition = WorkflowDefinition.model_validate(version.definition)
        validation = validate_workflow_graph(definition)
        if not validation.valid:
            raise ValueError("; ".join(i.message for i in validation.issues if i.severity == "error"))

        run = WorkflowRun(
            workflow_id=workflow.id,
            version=version.version,
            status="queued",
            trigger_type=trigger_type,
            triggered_by=triggered_by,
            inputs=inputs,
            variables={**(definition.variables or {}), **(environment_variables or {}), **inputs},
            retry_of_run_id=retry_of_run_id,
        )
        self.db.add(run)
        self.db.flush()

        for node in definition.nodes:
            node_run = NodeRun(
                run_id=run.id,
                node_id=node.id,
                node_type=node.type,
                node_name=node.name,
                status="pending" if not start_from_node or node.id == start_from_node else "skipped",
            )
            self.db.add(node_run)

        workflow.last_run_at = datetime.now(UTC)
        workflow.last_status = "queued"
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(run)

        self.audit.record(
            action="workflow.executed",
            resource_type="workflow_run",
            resource_id=str(run.id),
            actor_id=triggered_by,
            details={"workflowId": str(workflow.id), "version": version.version},
        )
        self.db.commit()

        # Execute synchronously for MVP reliability; Celery task wraps the same method.
        self.execute_run(run.id, start_from_node=start_from_node)
        return self.db.get(WorkflowRun, run.id)  # type: ignore[return-value]

    def cancel_run(self, run_id: UUID) -> WorkflowRun:
        run = self.db.get(WorkflowRun, run_id)
        if not run:
            raise ValueError("Run not found")
        if run.status in {"passed", "failed", "cancelled"}:
            return run
        run.status = "cancelled"
        run.ended_at = datetime.now(UTC)
        for node_run in run.node_runs:
            if node_run.status in {"pending", "queued", "running", "waiting", "retrying", "approval_required"}:
                node_run.status = "cancelled"
                self.db.add(node_run)
        self.db.add(run)
        self.db.commit()
        event_broker.publish_sync(
            run_id,
            {"type": "run.cancelled", "runId": str(run_id), "status": "cancelled"},
        )
        self.audit.record(
            action="workflow.cancelled",
            resource_type="workflow_run",
            resource_id=str(run_id),
        )
        self.db.commit()
        return run

    def execute_run(
        self,
        run_id: UUID,
        start_from_node: str | None = None,
        resume_after_node: str | None = None,
    ) -> None:
        run = self.db.get(WorkflowRun, run_id)
        if not run:
            return
        workflow = self.db.get(Workflow, run.workflow_id)
        version = (
            self.db.query(WorkflowVersion)
            .filter(
                WorkflowVersion.workflow_id == run.workflow_id,
                WorkflowVersion.version == run.version,
            )
            .one()
        )
        definition = WorkflowDefinition.model_validate(version.definition)

        run.status = "running"
        run.started_at = run.started_at or datetime.now(UTC)
        self.db.add(run)
        self.db.commit()
        event_broker.publish_sync(run_id, {"type": "run.started", "runId": str(run_id)})

        adjacency: dict[str, list[tuple[str, str | None]]] = {n.id: [] for n in definition.nodes}
        for edge in definition.edges:
            adjacency[edge.source].append((edge.target, edge.sourceHandle))

        node_map = {n.id: n for n in definition.nodes}
        node_run_map = {nr.node_id: nr for nr in run.node_runs}
        secrets = self._load_secrets()
        node_outputs: dict[str, Any] = {}
        previous_result: dict[str, Any] = {}

        # Seed outputs from already-passed nodes (resume / retry-from-node)
        for nr in run.node_runs:
            if nr.status == "passed":
                outputs = nr.outputs or {}
                node_outputs[nr.node_id] = {"output": outputs, **outputs}
                previous_result = nr.result or {"status": "passed", "outputs": outputs}

        start_nodes = [n for n in definition.nodes if n.type == "start"]
        if not start_nodes:
            self._fail_run(run, "workflow_configuration_error", "Missing start node")
            return

        visited: set[str] = {nr.node_id for nr in run.node_runs if nr.status == "passed"}
        if resume_after_node:
            queue: list[str] = [target for target, _ in adjacency.get(resume_after_node, [])]
            visited.add(resume_after_node)
        else:
            queue = [start_from_node or start_nodes[0].id]
        stopped = False

        while queue and not stopped:
            self.db.refresh(run)
            if run.status == "cancelled":
                return

            node_id = queue.pop(0)
            if node_id in visited:
                continue
            visited.add(node_id)
            node = node_map[node_id]
            node_run = node_run_map[node_id]
            if node_run.status == "skipped" and start_from_node and node_id != start_from_node:
                continue
            if node_run.status == "passed" and resume_after_node:
                continue

            run.current_node_id = node_id
            self.db.add(run)
            self.db.commit()

            result = self._execute_node(
                run=run,
                node=node,
                node_run=node_run,
                secrets=secrets,
                node_outputs=node_outputs,
                previous_result=previous_result,
            )
            previous_result = result
            outputs = result.get("outputs") or {}
            node_outputs[node.id] = {"output": outputs, **outputs}

            if result.get("stop"):
                stopped = True

            if result.get("status") in {"waiting", "approval_required"} or result.get("pause"):
                pause_status = result.get("status") if result.get("status") in {"waiting", "approval_required"} else "approval_required"
                node_run.status = pause_status
                self.db.add(node_run)
                run.status = pause_status
                self.db.add(run)
                if workflow:
                    workflow.last_status = pause_status
                    self.db.add(workflow)
                self.db.commit()
                event_broker.publish_sync(
                    run_id,
                    {
                        "type": "run.waiting",
                        "runId": str(run_id),
                        "status": pause_status,
                        "nodeId": node.id,
                        "prompt": outputs.get("prompt"),
                        "inputType": outputs.get("inputType") or "otp",
                    },
                )
                return

            if result.get("status") == "failed":
                classification = result.get("failure_classification") or "infrastructure_error"
                info = classify_failure(classification, result.get("error") or "Node failed")
                self._fail_run(run, info.code, info.message, info.recommended_action)
                workflow.last_status = "failed"  # type: ignore[union-attr]
                self.db.add(workflow)
                self.db.commit()
                return

            # Branch selection for if/else
            next_handle = None
            if node.type == "if_else":
                next_handle = "true" if outputs.get("branch") == "true" else "false"

            for target, handle in adjacency.get(node_id, []):
                if next_handle and handle and handle != next_handle:
                    continue
                if target not in visited:
                    queue.append(target)

        # Mark untouched nodes skipped (only pending ones never visited)
        for nr in run.node_runs:
            if nr.status == "pending" and nr.node_id not in visited:
                nr.status = "skipped"
                self.db.add(nr)

        run.status = "passed"
        run.ended_at = datetime.now(UTC)
        if run.started_at:
            started = run.started_at if run.started_at.tzinfo else run.started_at.replace(tzinfo=UTC)
            run.duration_ms = int((run.ended_at - started).total_seconds() * 1000)
        workflow.last_status = "passed"  # type: ignore[union-attr]
        self.db.add(run)
        self.db.add(workflow)
        self.db.commit()
        event_broker.publish_sync(
            run_id,
            {"type": "run.completed", "runId": str(run_id), "status": "passed"},
        )

    def provide_input(self, run_id: UUID, payload: dict[str, Any]) -> WorkflowRun:
        """Complete a human-in-the-loop / waiting node and resume execution."""
        run = self.db.get(WorkflowRun, run_id)
        if not run:
            raise ValueError("Run not found")
        if run.status not in {"waiting", "approval_required"}:
            raise ValueError("Run is not waiting for input")

        waiting = next(
            (nr for nr in run.node_runs if nr.status in {"waiting", "approval_required"}),
            None,
        )
        if not waiting:
            raise ValueError("No waiting node found")

        value = payload.get("otp") or payload.get("value")
        extras = dict(payload.get("inputs") or {})
        outputs = {
            **(waiting.outputs or {}),
            **extras,
        }
        if value is not None:
            outputs["otp"] = str(value)
            outputs["value"] = str(value)
            outputs["providedByHuman"] = True

        waiting.status = "passed"
        waiting.outputs = outputs
        waiting.result = {
            **(waiting.result or {}),
            "status": "passed",
            "outputs": outputs,
            "resumed": True,
        }
        waiting.ended_at = datetime.now(UTC)
        self.db.add(waiting)
        run.status = "running"
        self.db.add(run)
        self.db.commit()

        event_broker.publish_sync(
            run_id,
            {
                "type": "run.resumed",
                "runId": str(run_id),
                "nodeId": waiting.node_id,
                "status": "running",
            },
        )
        self.execute_run(run_id, resume_after_node=waiting.node_id)
        refreshed = self.db.get(WorkflowRun, run_id)
        return refreshed  # type: ignore[return-value]

    def _execute_node(
        self,
        *,
        run: WorkflowRun,
        node: Any,
        node_run: NodeRun,
        secrets: dict[str, str],
        node_outputs: dict[str, Any],
        previous_result: dict[str, Any],
    ) -> dict[str, Any]:
        attempts = int(node.config.get("retryCount", 0)) + 1
        last_result: dict[str, Any] = {}
        for attempt in range(1, attempts + 1):
            node_run.status = "retrying" if attempt > 1 else "running"
            node_run.attempt = attempt
            node_run.started_at = datetime.now(UTC)
            self.db.add(node_run)
            self.db.commit()
            event_broker.publish_sync(
                run.id,
                {
                    "type": "node.started",
                    "runId": str(run.id),
                    "nodeId": node.id,
                    "attempt": attempt,
                    "name": node.name,
                },
            )

            context = build_variable_context(
                variables=run.variables,
                secrets=secrets,
                node_outputs=node_outputs,
                runtime={"environment": "local", "runId": str(run.id)},
            )
            resolved_config = resolve_variables(node.config, context)
            started = time.perf_counter()

            try:
                if node.type in CLI_NODE_TYPES or node.type.startswith("cli"):
                    result = self._execute_via_agent(
                        run=run,
                        node=node,
                        node_run=node_run,
                        job_type="cli",
                        config=resolved_config,
                        secrets=secrets,
                    )
                elif node.type in BROWSER_NODE_TYPES or node.type.startswith("browser"):
                    result = self._execute_via_agent(
                        run=run,
                        node=node,
                        node_run=node_run,
                        job_type="browser",
                        config=resolved_config,
                        secrets=secrets,
                    )
                else:
                    executor = registry.get(node.type)
                    if not executor:
                        result = {
                            "status": "failed",
                            "failure_classification": "workflow_configuration_error",
                            "error": f"No executor registered for node type '{node.type}'",
                        }
                    else:
                        result = executor.execute(
                            config=resolved_config,
                            context={
                                "node_type": node.type,
                                "node_id": node.id,
                                "run_id": run.id,
                                "secrets": secrets,
                                "previous_result": previous_result,
                                "resolved": resolved_config,
                            },
                        )
            except Exception as exc:  # noqa: BLE001
                result = {
                    "status": "failed",
                    "failure_classification": "infrastructure_error",
                    "error": str(exc),
                }

            duration_ms = int((time.perf_counter() - started) * 1000)
            result.setdefault("durationMs", duration_ms)
            last_result = result

            # Persist artifacts metadata
            for artifact in result.get("artifacts") or []:
                path = artifact.get("path")
                if not path and artifact.get("content") is not None:
                    import json

                    rel = f"artifacts/{run.id}/{node.id}/{artifact.get('name', uuid4().hex)}"
                    content = artifact["content"]
                    data = (
                        content
                        if isinstance(content, (bytes, bytearray))
                        else json.dumps(content, default=str).encode("utf-8")
                    )
                    path = self.storage.save_bytes(relative_path=rel, data=data)
                if path:
                    self.db.add(
                        Artifact(
                            run_id=run.id,
                            node_run_id=node_run.id,
                            name=artifact.get("name") or "artifact",
                            artifact_type=artifact.get("type") or "file",
                            storage_path=path,
                            content_type=artifact.get("contentType"),
                            meta=artifact,
                        )
                    )

            node_run.outputs = result.get("outputs") or {}
            node_run.result = result
            node_run.error = result.get("error")
            node_run.failure_classification = result.get("failure_classification")
            node_run.logs = list(node_run.logs or []) + list(result.get("logs") or [])
            node_run.ended_at = datetime.now(UTC)
            node_run.duration_ms = duration_ms
            node_run.status = result.get("status") or "failed"
            self.db.add(node_run)
            self.db.commit()

            event_broker.publish_sync(
                run.id,
                {
                    "type": "node.completed",
                    "runId": str(run.id),
                    "nodeId": node.id,
                    "status": node_run.status,
                    "durationMs": duration_ms,
                    "outputs": node_run.outputs,
                    "error": node_run.error,
                },
            )

            if node_run.status == "passed":
                return result
            if node_run.status in {"waiting", "approval_required"} or result.get("pause"):
                return result

        return last_result

    def _execute_via_agent(
        self,
        *,
        run: WorkflowRun,
        node: Any,
        node_run: NodeRun,
        job_type: str,
        config: dict[str, Any],
        secrets: dict[str, str],
    ) -> dict[str, Any]:
        selector = config.get("agentSelector") or {}
        required_tags = list(selector.get("requiredTags") or [])
        agent = self.agent_jobs.select_agent(agent_type=job_type, required_tags=required_tags)

        # Fallback local inline execution when no agent is registered (dev mode).
        if agent is None:
            if job_type == "cli":
                from app.executors.local_cli import execute_local_cli

                return execute_local_cli(config=config, secrets=secrets, storage=self.storage, run_id=run.id)
            if job_type == "browser":
                from app.executors.local_browser import execute_local_browser

                return execute_local_browser(config=config, node_type=node.type, secrets=secrets, storage=self.storage, run_id=run.id, node_id=node.id)

        # Never send raw secrets beyond masked names in audit; agents get injected values in payload.
        injected_secrets = {
            key: secrets[key]
            for key in (config.get("secretKeys") or list(secrets.keys()))
            if key in secrets
        }
        payload = {
            "nodeType": node.type,
            "nodeName": node.name,
            "config": config,
            "secrets": injected_secrets,
            "runId": str(run.id),
            "nodeId": node.id,
        }
        job = self.agent_jobs.enqueue_job(
            run_id=run.id,
            node_run=node_run,
            job_type=job_type,
            payload=payload,
            required_tags=required_tags,
            agent=agent,
        )
        self.db.commit()
        timeout = float(config.get("timeoutSeconds", 600))
        completed = self.agent_jobs.wait_for_job(job.id, timeout_seconds=timeout + 30)
        result = completed.result or {}
        if "status" not in result:
            result["status"] = "passed" if completed.status == "completed" else "failed"
        return result

    def _load_secrets(self) -> dict[str, str]:
        secrets = (
            self.db.query(Secret).filter(Secret.deleted_at.is_(None)).all()
        )
        loaded: dict[str, str] = {}
        for secret in secrets:
            try:
                loaded[secret.name] = decrypt_secret(secret.encrypted_value)
            except Exception:  # noqa: BLE001
                continue
        return loaded

    def _fail_run(
        self,
        run: WorkflowRun,
        code: str,
        message: str,
        recommended_action: str | None = None,
    ) -> None:
        info = classify_failure(code, message)
        run.status = "failed"
        run.failure_classification = info.code
        run.failure_message = info.message
        run.recommended_action = recommended_action or info.recommended_action
        run.ended_at = datetime.now(UTC)
        if run.started_at:
            started = run.started_at if run.started_at.tzinfo else run.started_at.replace(tzinfo=UTC)
            run.duration_ms = int((run.ended_at - started).total_seconds() * 1000)
        self.db.add(run)
        self.db.commit()
        event_broker.publish_sync(
            run.id,
            {
                "type": "run.failed",
                "runId": str(run.id),
                "status": "failed",
                "failureClassification": info.code,
                "message": info.message,
                "recommendedAction": run.recommended_action,
            },
        )
