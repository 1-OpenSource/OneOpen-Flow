# Architecture

```text
┌──────────────────┐     SSE/HTTP      ┌─────────────────────┐
│  Flow Studio UI  │ ◄───────────────► │  FastAPI Backend    │
│  React + RF      │                   │  Workflow Engine    │
└──────────────────┘                   └─────────┬───────────┘
                                                 │
                         ┌───────────────────────┼───────────────────────┐
                         │                       │                       │
                         ▼                       ▼                       ▼
                   ┌──────────┐           ┌────────────┐          ┌────────────┐
                   │ Postgres │           │   Redis    │          │  Storage   │
                   │ metadata │           │ Celery/SSE │          │ artifacts  │
                   └──────────┘           └────────────┘          └────────────┘
                                                 │
                         ┌───────────────────────┼───────────────────────┐
                         ▼                       ▼                       ▼
                  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
                  │ Browser Agent│       │  CLI Agent   │       │ Workboard API│
                  │ Playwright   │       │ Bash/PS/CMD  │       │ defects      │
                  └──────────────┘       └──────────────┘       └──────────────┘
```

## Execution model

1. Studio saves a versioned workflow JSON definition.
2. Run API validates the graph and creates `WorkflowRun` + `NodeRun` rows.
3. The orchestrator walks the DAG, resolves `{{variable.*}}` / `{{secret.*}}` / `{{node.*}}` expressions, and dispatches nodes.
4. Logic/API/DB/validation nodes execute in-process via pluggable executors.
5. Browser/CLI nodes enqueue signed agent jobs (or run local inline executors in development).
6. Live events stream to the UI over SSE (`GET /api/runs/{id}/events`).
7. Artifacts and an evidence ZIP are stored via the storage abstraction.

## Design principles

- Workflow definitions are language-agnostic JSON.
- Node executors are registered plugins — the orchestrator does not hardcode node logic.
- Secrets are encrypted at rest and masked in logs.
- Locator healing is controlled, never silent below the confidence threshold.
