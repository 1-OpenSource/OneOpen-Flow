# Workboard integration

OneOpen Flow integrates with OneOpen Workboard for defect management.

## Create defect from failed run

`POST /api/runs/{run_id}/create-work-item`

Payload includes workflow name/version, execution ID, failed node, classification, expected/actual values, environment evidence references, and a reproduction URL.

When `WORKBOARD_API_URL` and `project_id` are set, Flow creates a Workboard `BUG` and attaches screenshots/traces when possible. Otherwise a local link record is stored.

## Run Reproduction

Open the run details page and use **Retry** / **Retry failed node**.

## Auto-retest

When a linked Workboard item moves to **Ready for Testing** (mapped to Workboard `IN_REVIEW`), call:

```bash
POST /api/triggers/workboard-status
{
  "work_item_key": "FLOW-ABC123",
  "status": "IN_REVIEW"
}
```

On pass, Flow marks the link verified and can attach evidence / verification comments when the Workboard API is available.
