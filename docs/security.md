# Security

## Permissions

- View workflows
- Edit workflows
- Run workflows
- Run browser nodes
- Run CLI nodes
- Run privileged CLI nodes
- Manage agents
- Manage secrets
- Approve healed locators
- Create Workboard defects

## Secrets

- Encrypted at rest (Fernet derived from `ENCRYPTION_KEY`)
- Masked in logs and CLI output
- Never returned to the frontend after creation
- Never included in exported workflow JSON

## CLI execution

- No direct shell execution on the FastAPI server for production agent mode
- Development fallback uses isolated temp workspaces
- Agents authenticate with hashed tokens
- Jobs are HMAC-signed

## Audit log

Records workflow create/modify/execute/cancel, CLI execution, secret usage (not values), agent register/disable, locator heal/approve/reject, defect creation, and evidence download.
