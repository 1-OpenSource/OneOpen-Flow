# CLI agent

The CLI agent executes commands outside the FastAPI process.

## Registration

```bash
POST /api/agents/register
{
  "name": "windows-build-agent",
  "agent_type": "cli",
  "operating_system": "windows",
  "supported_shells": ["powershell", "cmd"],
  "tags": ["windows", "powershell"],
  "profile": "restricted"
}
```

Store the returned token securely. Heartbeat with `X-Agent-Id` and `X-Agent-Token`.

## Job lifecycle

1. Claim signed job
2. Create isolated workspace
3. Inject permitted variables/secrets
4. Execute command
5. Stream/capture stdout & stderr
6. Collect artifacts
7. Scrub secrets and clean workspace
8. Complete job with structured result

## Targeting

```json
{
  "agentSelector": {
    "requiredTags": ["windows", "powershell"]
  }
}
```

## Security controls

Workspace isolation, allowlists, CPU/memory/timeout/output limits, path restrictions, secret masking, audit logging, and privileged profiles with approval requirements.
