# Service accounts (Agentic AI)

```{important}
**Agentic AI must authenticate as a service account.**  
Do not use a human user’s email/password JWT for automation. Create a dedicated
service account under **Admin → Service accounts** and store the client secret
in your agent vault / environment.
```

A **service account** is a non-human identity used by Agentic AI, CI pipelines,
and integrations to call the OneOpen Flow HTTP API with scoped permissions.

## Concepts

| Term | Meaning |
|------|---------|
| **Service account** | Machine identity (`client_id` like `svc-ai-orchestrator`) |
| **Client secret** | One-time token (`oof_…`) shown at creation — treat like a password |
| **Scopes** | What the account may do (`workflows:read`, `workflows:run`, `exposed:invoke`, `*`) |
| **Human user** | Operator login (JWT / SSO) for the UI |

```{mermaid}
flowchart LR
  AI[Agentic AI] -->|Bearer oof_…| API[OneOpen Flow API]
  Human[Human admin] -->|JWT / SSO| UI[Flow Studio]
  UI --> API
  AI -->|discover| Catalog["GET /api/agentic/catalog"]
  AI -->|invoke| Exposed["POST /api/exposed/workflows/{slug}/invoke"]
```

## Create a service account

### From the UI

1. Sign in as **owner** or **admin**.
2. Open **Admin → Service accounts**.
3. Enter a display name (e.g. `AI Orchestrator`).
4. Optionally set a `client_id` (defaults to `svc-<slug>`).
5. Create — **copy the client secret immediately** (shown once).

### From the API

```bash
# Admin JWT
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@oneopen.local","password":"ChangeMe123!"}' \
  | jq -r .access_token)

curl -s -X POST http://localhost:8000/api/admin/service-accounts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AI Orchestrator",
    "client_id": "svc-ai-orchestrator",
    "description": "Primary agentic runner",
    "scopes": ["workflows:read", "workflows:run", "exposed:invoke"]
  }'
```

Response (secret only once):

```json
{
  "service_account": {
    "id": "…",
    "name": "AI Orchestrator",
    "client_id": "svc-ai-orchestrator",
    "scopes": ["workflows:read", "workflows:run", "exposed:invoke"],
    "prefix": "oof_…"
  },
  "client_secret": "oof_xxxxxxxx",
  "token": "oof_xxxxxxxx"
}
```

```{warning}
Store ``client_secret`` in a secrets manager. It cannot be retrieved again.
Revoke and rotate if leaked.
```

## Authenticate as the AI

```bash
export OOF_SERVICE_TOKEN=oof_xxxxxxxx

# Preferred for agents
curl -s http://localhost:8000/api/agentic/catalog \
  -H "Authorization: Bearer $OOF_SERVICE_TOKEN"

# Equivalent
curl -s http://localhost:8000/api/agentic/catalog \
  -H "X-API-Key: $OOF_SERVICE_TOKEN"
```

## Typical AI loop

1. ``GET /api/agentic/catalog`` — discover tools + exposed workflows  
2. ``GET /api/exposed/workflows`` — list published workflows  
3. ``GET /api/exposed/workflows/{slug}`` — read input schema  
4. ``POST /api/exposed/workflows/{slug}/invoke`` — start a run  
5. ``GET /api/runs/{id}`` — poll status / results  
6. ``POST /api/runs/{id}/provide-input`` — if HITL OTP pause  

## Scopes

| Scope | Allows |
|-------|--------|
| ``workflows:read`` | List/get workflows, catalog, exposed schemas |
| ``workflows:run`` | Start runs by workflow id |
| ``exposed:invoke`` | Invoke exposed workflows by slug |
| ``*`` | All service-account scopes |

Admins manage which scopes a service account receives at creation time.

## Revoke

```bash
curl -s -X DELETE http://localhost:8000/api/admin/service-accounts/{id} \
  -H "Authorization: Bearer $ADMIN_JWT"
```

Or use **Revoke** in the Admin UI. Revoked accounts return ``401`` immediately.

## Endpoints

.. list-table::
   :header-rows: 1
   :widths: 15 45 40

   * - Method
     - Path
     - Description
   * - ``GET``
     - ``/api/admin/service-accounts``
     - List service accounts (admin)
   * - ``POST``
     - ``/api/admin/service-accounts``
     - Create service account + secret
   * - ``DELETE``
     - ``/api/admin/service-accounts/{id}``
     - Revoke service account

Aliases ``/api/admin/api-keys`` remain for compatibility.
