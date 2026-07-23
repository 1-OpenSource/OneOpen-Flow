import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app


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


def test_expose_and_agentic_catalog(client: TestClient):
    headers = _auth_headers(client)
    created = client.post("/api/workflows", headers=headers, json={"name": "CI Check", "description": "d"})
    assert created.status_code == 201
    workflow_id = created.json()["id"]

    exposed = client.put(
        f"/api/workflows/{workflow_id}/expose",
        headers=headers,
        json={"enabled": True, "slug": "ci-check", "description": "for agents"},
    )
    assert exposed.status_code == 200
    assert exposed.json()["is_exposed"] is True
    assert exposed.json()["expose_slug"] == "ci-check"

    listed = client.get("/api/exposed/workflows", headers=headers)
    assert listed.status_code == 200
    assert any(w["slug"] == "ci-check" for w in listed.json())

    catalog = client.get("/api/agentic/catalog", headers=headers)
    assert catalog.status_code == 200
    body = catalog.json()
    assert any(t["name"] == "invoke_exposed_workflow" for t in body["tools"])
    assert any(w["slug"] == "ci-check" for w in body["exposed_workflows"])

    key_res = client.post(
        "/api/admin/service-accounts",
        headers=headers,
        json={
            "name": "AI Bot",
            "client_id": "svc-ai-bot",
            "scopes": ["workflows:read", "exposed:invoke", "workflows:run"],
        },
    )
    assert key_res.status_code == 201
    body = key_res.json()
    assert body["service_account"]["client_id"] == "svc-ai-bot"
    api_token = body["client_secret"] or body["token"]
    invoke = client.post(
        "/api/exposed/workflows/ci-check/invoke",
        headers={"Authorization": f"Bearer {api_token}"},
        json={"inputs": {"x": 1}},
    )
    assert invoke.status_code == 201
    assert "id" in invoke.json()


def test_admin_rbac_users_and_permissions(client: TestClient):
    headers = _auth_headers(client)
    users = client.get("/api/admin/users", headers=headers)
    assert users.status_code == 200
    assert len(users.json()) >= 1
    perms = client.get("/api/admin/permissions", headers=headers)
    assert perms.status_code == 200
    assert "owner" in perms.json()["roles"]
    assert "manage_users" in perms.json()["permissions"]

    invite = client.post(
        "/api/admin/invites",
        headers=headers,
        json={"email": "new@example.com", "role": "member"},
    )
    assert invite.status_code == 201
    token = invite.json()["accept_token"]
    accepted = client.post(
        "/api/auth/accept-invite",
        json={"token": token, "name": "New User", "password": "secret123"},
    )
    assert accepted.status_code == 200
    assert "access_token" in accepted.json()


def test_sso_config_public(client: TestClient):
    res = client.get("/api/auth/sso/config")
    assert res.status_code == 200
    assert res.json()["enabled"] is False
    assert res.json()["allow_local_login"] is True
