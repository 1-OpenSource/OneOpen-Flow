from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Artifact, NodeRun, WorkboardLink, Workflow, WorkflowRun
from app.services.audit import AuditService


class WorkboardIntegrationService:
    """Creates OneOpen Workboard defects from failed workflow runs."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.audit = AuditService(db)

    def build_defect_payload(self, run: WorkflowRun, workflow: Workflow) -> dict[str, Any]:
        failed_nodes = [nr for nr in run.node_runs if nr.status == "failed"]
        failed = failed_nodes[0] if failed_nodes else None
        screenshots = [
            a for a in run.artifacts if a.artifact_type == "screenshot"
        ]
        return {
            "title": f"[OneOpen Flow] {workflow.name} failed"
            + (f" — {failed.node_name}" if failed else ""),
            "type": "BUG",
            "priority": "HIGH",
            "description": self._description(run, workflow, failed),
            "labels": ["oneopen-flow", "automation", run.failure_classification or "failure"],
            "metadata": {
                "workflowName": workflow.name,
                "workflowVersion": run.version,
                "executionId": str(run.id),
                "failedNode": failed.node_id if failed else None,
                "failureClassification": run.failure_classification,
                "errorMessage": run.failure_message or (failed.error if failed else None),
                "expectedValue": (failed.outputs or {}).get("expected") if failed else None,
                "actualValue": (failed.outputs or {}).get("actual") if failed else None,
                "screenshotCount": len(screenshots),
            },
        }

    def create_work_item(
        self,
        *,
        run: WorkflowRun,
        workflow: Workflow,
        actor_id: UUID | None,
        project_id: str | None = None,
        title: str | None = None,
        additional_notes: str | None = None,
        auth_token: str | None = None,
    ) -> WorkboardLink:
        payload = self.build_defect_payload(run, workflow)
        if title:
            payload["title"] = title
        if additional_notes:
            payload["description"] += f"\n\n## Notes\n{additional_notes}"

        work_item_id = f"local-{run.id.hex[:8]}"
        work_item_key = f"FLOW-{run.id.hex[:6].upper()}"
        remote_status = "created-local"

        if self.settings.workboard_enabled and project_id:
            try:
                headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
                with httpx.Client(timeout=30) as client:
                    response = client.post(
                        f"{self.settings.workboard_api_url}/projects/{project_id}/work-items",
                        json={
                            "title": payload["title"],
                            "description": payload["description"],
                            "type": "BUG",
                            "priority": payload.get("priority", "HIGH"),
                            "labels": payload.get("labels") or [],
                        },
                        headers=headers,
                    )
                    if response.is_success:
                        data = response.json()
                        work_item_id = str(data.get("id") or work_item_id)
                        work_item_key = str(data.get("key") or data.get("display_id") or work_item_key)
                        remote_status = "created"
                        # Attach evidence files when possible
                        for artifact in run.artifacts:
                            if artifact.artifact_type in {"screenshot", "trace", "stdout", "stderr"}:
                                self._attach_evidence(client, work_item_id, artifact, headers)
            except Exception as exc:  # noqa: BLE001
                remote_status = f"local-fallback:{exc}"

        reproduction_url = f"/runs/{run.id}?reproduce=1"
        link = WorkboardLink(
            run_id=run.id,
            work_item_key=work_item_key,
            work_item_id=work_item_id,
            project_id=project_id,
            status=remote_status,
            reproduction_url=reproduction_url,
            payload=payload,
        )
        self.db.add(link)
        self.audit.record(
            action="defect.created",
            resource_type="workboard_link",
            resource_id=str(link.id) if link.id else work_item_key,
            actor_id=actor_id,
            details={"runId": str(run.id), "workItemKey": work_item_key},
        )
        self.db.commit()
        self.db.refresh(link)
        return link

    def handle_status_change(self, work_item_key: str, new_status: str) -> WorkflowRun | None:
        """When Workboard item moves to Ready for Testing / IN_REVIEW, rerun workflow."""
        link = (
            self.db.query(WorkboardLink)
            .filter(WorkboardLink.work_item_key == work_item_key)
            .order_by(WorkboardLink.created_at.desc())
            .first()
        )
        if not link or not link.auto_retest:
            return None
        normalized = new_status.upper().replace(" ", "_")
        if normalized not in {"READY_FOR_TESTING", "IN_REVIEW"}:
            return None
        from app.engine.orchestrator import WorkflowEngine
        from app.models import Workflow, WorkflowVersion

        run = self.db.get(WorkflowRun, link.run_id)
        if not run:
            return None
        workflow = self.db.get(Workflow, run.workflow_id)
        version = (
            self.db.query(WorkflowVersion)
            .filter(
                WorkflowVersion.workflow_id == run.workflow_id,
                WorkflowVersion.version == run.version,
            )
            .one()
        )
        engine = WorkflowEngine(self.db)
        new_run = engine.start_run(
            workflow=workflow,  # type: ignore[arg-type]
            version=version,
            triggered_by=None,
            inputs=run.inputs,
            trigger_type="workboard",
            retry_of_run_id=run.id,
        )
        if new_run.status == "passed":
            link.status = "verified"
            self.db.add(link)
            self.db.commit()
        return new_run

    def _description(self, run: WorkflowRun, workflow: Workflow, failed: NodeRun | None) -> str:
        return f"""## OneOpen Flow Failure

| Field | Value |
|---|---|
| Workflow | {workflow.name} |
| Version | {run.version} |
| Execution ID | `{run.id}` |
| Failed node | {failed.node_name if failed else 'n/a'} |
| Classification | {run.failure_classification or 'n/a'} |
| Error | {run.failure_message or (failed.error if failed else 'n/a')} |
| Expected | {(failed.outputs or {}).get('expected') if failed else 'n/a'} |
| Actual | {(failed.outputs or {}).get('actual') if failed else 'n/a'} |

### Recommended action
{run.recommended_action or 'Review execution evidence and retry the failed node.'}

### Reproduction
Use **Run Reproduction** in OneOpen Flow for execution `{run.id}`.
"""

    def _attach_evidence(
        self,
        client: httpx.Client,
        work_item_id: str,
        artifact: Artifact,
        headers: dict[str, str],
    ) -> None:
        try:
            from pathlib import Path

            path = Path(artifact.storage_path)
            if not path.exists():
                return
            files = {"file": (artifact.name, path.read_bytes())}
            client.post(
                f"{self.settings.workboard_api_url}/work-items/{work_item_id}/attachments",
                files=files,
                headers=headers,
            )
        except Exception:  # noqa: BLE001
            return
