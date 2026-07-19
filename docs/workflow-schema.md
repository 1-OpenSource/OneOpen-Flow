# Workflow schema

Workflows are versioned JSON documents:

```json
{
  "id": "workflow-id",
  "name": "Build and validate application",
  "version": 1,
  "description": "...",
  "variables": { "baseUrl": "http://localhost:3000" },
  "nodes": [
    {
      "id": "node-1",
      "type": "run_powershell",
      "name": "Build application",
      "config": {
        "shell": "powershell",
        "command": "npm run build",
        "timeoutSeconds": 600,
        "allowedExitCodes": [0]
      },
      "position": { "x": 100, "y": 100 }
    }
  ],
  "edges": [
    { "id": "edge-1", "source": "node-1", "target": "node-2" }
  ]
}
```

## Variable syntax

- `{{variable.baseUrl}}`
- `{{secret.loginPassword}}`
- `{{node.build.output.version}}`
- `{{loop.currentItem}}`
- `{{runtime.environment}}`

## Validation rules

- Exactly one `start` node
- At least one `end` node
- Edges must reference existing nodes
- Cycles are rejected unless represented by loop/retry/for_each nodes
- CLI nodes require a command

Exported JSON never includes decrypted secret values.
