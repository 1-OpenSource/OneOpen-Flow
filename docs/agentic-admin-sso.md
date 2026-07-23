# Agentic API, RBAC & SSO

```{seealso}
**Service accounts for AI:** :doc:`service-accounts`  
Agentic systems must use a service account token, not a human login.
```

OneOpen Flow exposes the same capabilities as the UI over HTTP so Agentic AI,
CI, and integrations can operate the platform without the browser.

## Agentic catalog

```text
GET /api/agentic/catalog
Authorization: Bearer <service_account_secret>
```

Returns:

- **tools** — method, path, permission, and body schema for every UI-equivalent operation
- **exposed_workflows** — published workflows ready to invoke by slug
- **auth** — how to authenticate (**service account** recommended; human JWT for operators)

## Authentication

| Identity | Header | Intended for |
|----------|--------|----------------|
| **Service account** | `Authorization: Bearer oof_…` or `X-API-Key: oof_…` | Agentic AI, CI, bots |
| Human JWT | `Authorization: Bearer <jwt>` | Studio UI operators |
| SSO (OIDC) | Browser redirect → JWT | Enterprise human login |

Create service accounts under **Admin → Service accounts** or
``POST /api/admin/service-accounts``.

Scopes: `workflows:read`, `workflows:run`, `exposed:invoke`, or `*`.

## Expose a workflow

From the studio toolbar use **Expose** (optional slug), or:

```text
PUT /api/workflows/{id}/expose
{"enabled": true, "slug": "build-validate", "description": "CI build check"}
```

Then a service account can:

```text
GET  /api/exposed/workflows
GET  /api/exposed/workflows/build-validate
POST /api/exposed/workflows/build-validate/invoke
{"inputs": {"branch": "main"}}
```

## Full API surface (UI parity)

Workflows: create, list, get, update, delete, validate, run, clone, import, export, expose  
Runs: list, get, cancel, retry, retry-from-node, provide-input, events (SSE), evidence, create-work-item  
Agents: list, patch (enable/tags), revoke  
Secrets: create, list, update, delete  
Environments: create, list, update, delete  
Admin: users, invites, permissions matrix, SSO, **service accounts**

Interactive docs: http://localhost:8000/docs

## RBAC (human operators)

Roles: `owner`, `admin`, `member`, `viewer`.

| Permission | owner/admin | member | viewer |
|------------|-------------|--------|--------|
| view/edit/run workflows | ✓ | ✓ | view |
| expose workflows | ✓ | ✓ | |
| manage secrets/agents | ✓ | | |
| manage users / SSO / service accounts | ✓ | | |

Admin UI: **/admin** (owner or admin).

```text
GET  /api/admin/users
PATCH /api/admin/users/{id}   {"role":"member","is_active":true}
GET  /api/admin/permissions
POST /api/admin/invites       {"email":"a@b.com","role":"member"}
```

## SSO (OIDC)

Configure under **Admin → SSO**, or via environment:

```bash
OIDC_ENABLED=true
OIDC_ISSUER=https://your-idp.example.com
OIDC_CLIENT_ID=...
OIDC_CLIENT_SECRET=...
OIDC_REDIRECT_URI=http://localhost:8000/api/auth/sso/callback
FRONTEND_URL=http://localhost:5173
```

Flow:

1. `GET /api/auth/sso/config` — public `{ enabled, authorize_url }`
2. Browser → `/api/auth/sso/authorize` → IdP
3. Callback → redirect to frontend with `?sso_token=…`

You can keep local login alongside SSO (`allow_local_login`).

```{note}
SSO authenticates **human** operators into the UI. Agentic AI still uses a
**service account** even when SSO is enabled for people.
```
