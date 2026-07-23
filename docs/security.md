# Security

## Identities

| Kind | How they authenticate | Used for |
|------|----------------------|----------|
| Human user | Password JWT or OIDC SSO | Flow Studio UI |
| **Service account** | Client secret (`oof_…`) | Agentic AI, CI, automation |
| Execution agent | Agent registration token | Browser / CLI workers |

```{important}
Never share a human password or personal JWT with an AI agent.
Create a dedicated :doc:`service-accounts` with least-privilege scopes.
```

## Human permissions (RBAC)

- View / edit / run workflows
- Expose workflows for agentic invoke
- Run browser / CLI / privileged CLI nodes
- Manage agents
- Manage secrets
- Approve healed locators
- Create Workboard defects
- Manage users, SSO, and service accounts (owner/admin)

Roles: `owner`, `admin`, `member`, `viewer`. See :doc:`agentic-admin-sso`.

## Service account scopes

- `workflows:read` — catalog, list/get workflows and runs
- `workflows:run` — start runs by id
- `exposed:invoke` — invoke published workflows by slug
- `*` — all of the above

## Secrets

- Encrypted at rest (Fernet derived from `ENCRYPTION_KEY`)
- Masked in logs and CLI output
- Never returned to the frontend after creation
- Never included in exported workflow JSON
- Service account client secrets are shown **once** at creation

## CLI execution

- No direct shell execution on the FastAPI server for production agent mode
- Development fallback uses isolated temp workspaces
- Agents authenticate with hashed tokens
- Jobs are HMAC-signed

## Audit log

Records workflow create/modify/execute/cancel, CLI execution, secret usage (not values),
agent register/disable, locator heal/approve/reject, defect creation, evidence download,
SSO changes, and **service account create/revoke**.
