import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.engine.graph import resolve_variables, validate_workflow_graph, build_variable_context
from app.schemas import WorkflowDefinition
from app.core.security import encrypt_secret, decrypt_secret, mask_secrets
from app.services.workboard import WorkboardIntegrationService
from app.models import Workflow, WorkflowRun, NodeRun
from uuid import uuid4
from datetime import UTC, datetime


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _auth_headers(client: TestClient) -> dict[str, str]:
    client.post("/api/auth/register", json={"name": "Owner", "email": "a@b.com", "password": "secret123"})
    token = client.post("/api/auth/login", json={"email": "a@b.com", "password": "secret123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_workflow_crud(client: TestClient):
    headers = _auth_headers(client)
    created = client.post(
        "/api/workflows",
        headers=headers,
        json={"name": "Demo", "description": "d"},
    )
    assert created.status_code == 201
    workflow_id = created.json()["id"]
    listed = client.get("/api/workflows", headers=headers)
    assert listed.status_code == 200
    assert any(w["id"] == workflow_id for w in listed.json())
    detail = client.get(f"/api/workflows/{workflow_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["definition"]["nodes"]


def test_graph_validation_rejects_missing_start():
    definition = WorkflowDefinition(
        name="bad",
        nodes=[{"id": "1", "type": "end", "name": "End", "config": {}, "position": {"x": 0, "y": 0}}],
        edges=[],
    )
    result = validate_workflow_graph(definition)
    assert result.valid is False
    assert any(i.code == "start_required" for i in result.issues)


def test_variable_resolution():
    context = build_variable_context(
        variables={"baseUrl": "http://localhost"},
        secrets={"LOGIN_PASSWORD": "hidden"},
        node_outputs={"build": {"output": {"version": "1.2.3"}, "version": "1.2.3"}},
    )
    assert resolve_variables("{{variable.baseUrl}}/x", context) == "http://localhost/x"
    assert resolve_variables("{{secret.LOGIN_PASSWORD}}", context) == "hidden"
    assert resolve_variables("{{node.build.output.version}}", context) == "1.2.3"


def test_secret_masking_and_encryption():
    token = encrypt_secret("super-secret")
    assert decrypt_secret(token) == "super-secret"
    assert "***" in mask_secrets("value=super-secret", ["super-secret"])


def test_agent_registration_and_heartbeat(client: TestClient):
    reg = client.post(
        "/api/agents/register",
        json={
            "name": "cli-1",
            "agent_type": "cli",
            "operating_system": "windows",
            "supported_shells": ["powershell"],
            "tags": ["windows", "powershell"],
        },
    )
    assert reg.status_code == 201
    data = reg.json()
    beat = client.post(
        "/api/agents/heartbeat",
        headers={"X-Agent-Id": data["id"], "X-Agent-Token": data["token"]},
        json={"status": "idle", "current_workload": 0},
    )
    assert beat.status_code == 200


def test_workboard_defect_payload():
    workflow = Workflow(
        id=uuid4(),
        name="Demo",
        description="",
        current_version=1,
        owner_id=uuid4(),
        tags=[],
        trigger_type="manual",
    )
    run = WorkflowRun(
        id=uuid4(),
        workflow_id=workflow.id,
        version=1,
        status="failed",
        trigger_type="manual",
        inputs={},
        variables={},
        failure_classification="assertion_failure",
        failure_message="mismatch",
        recommended_action="fix assertion",
        created_at=datetime.now(UTC),
    )
    run.node_runs = [
        NodeRun(
            id=uuid4(),
            run_id=run.id,
            node_id="n1",
            node_type="assert_text",
            node_name="Assert",
            status="failed",
            attempt=1,
            inputs={},
            outputs={"expected": "A", "actual": "B"},
            result={},
            error="mismatch",
            logs=[],
        )
    ]
    run.artifacts = []
    service = WorkboardIntegrationService(db=None)  # type: ignore[arg-type]
    payload = service.build_defect_payload(run, workflow)
    assert payload["type"] == "BUG"
    assert "executionId" in payload["metadata"]
    assert payload["metadata"]["expectedValue"] == "A"
