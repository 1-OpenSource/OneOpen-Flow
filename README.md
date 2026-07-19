<p align="center">
  <img src="docs/logo.svg" alt="OneOpen Flow" width="96" height="96">
</p>

<h1 align="center">OneOpen Flow</h1>

<p align="center">
  <strong>Open-source visual workflow orchestration &amp; validation</strong><br>
  Combine browser, CLI, API, database, and auth steps in one executable workflow graph.
</p>

<p align="center">
  <a href="https://github.com/1-OpenSource/OneOpen-Flow"><img alt="Status" src="https://img.shields.io/badge/status-MVP-e6b422?style=flat-square"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache%202.0-blue?style=flat-square"></a>
  <a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white"></a>
  <a href="https://react.dev/"><img alt="React" src="https://img.shields.io/badge/react-19-61DAFB?style=flat-square&logo=react&logoColor=black"></a>
  <a href="https://fastapi.tiangolo.com/"><img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.138-009688?style=flat-square&logo=fastapi&logoColor=white"></a>
  <a href="https://oneopensource.org"><img alt="OneOpenSource" src="https://img.shields.io/badge/part%20of-OneOpenSource-14b8a6?style=flat-square"></a>
</p>

<p align="center">
  <a href="#features">Features</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#documentation">Docs</a> ·
  <a href="#contributing">Contributing</a>
</p>

---

## Why OneOpen Flow?

Most automation tools focus on a single surface (browser *or* CI *or* API). Real validation work crosses all of them:

```text
Build → Start app → Health check → Login (email OTP / TOTP) → Assert UI
     → Compare with CLI output → Screenshot → Open Workboard defect
```

OneOpen Flow is a **visual orchestration studio** for those end-to-end technical workflows — with first-class support for **dynamic ASPX** and **React** apps where IDs and CSS hashes change between builds.

## Features

| Area | What you get |
|------|----------------|
| **Studio** | Drag-and-drop React Flow canvas, node palette, Monaco config, live run panel |
| **Browser** | Playwright agent, semantic locators, fingerprints, controlled healing (threshold 90) |
| **CLI** | Bash / PowerShell / CMD via isolated agents — never shell out from the API process |
| **API & DB** | REST requests/assertions, PostgreSQL query & assert nodes |
| **Auth** | Wait for email, extract OTP/link, TOTP, human-in-the-loop OTP entry |
| **Evidence** | Screenshots, traces, console/network logs, stdout/stderr, downloadable ZIP |
| **Workboard** | Create defects from failures, attach evidence, reproduction reruns |
| **Security** | Encrypted secrets, masked logs, permissions, audit trail |

## Modules

```text
OneOpen Flow Studio
OneOpen Workflow Engine
OneOpen Browser Agent      (Playwright / Node.js)
OneOpen CLI Agent          (Python)
OneOpen API Agent
OneOpen Database Agent
OneOpen Execution Evidence
OneOpen Workboard Integration
```

## Quick start

### Docker Compose (recommended)

```bash
git clone https://github.com/1-OpenSource/OneOpen-Flow.git
cd OneOpen-Flow
docker compose up --build
```

| Service | URL |
|---------|-----|
| **Studio** | http://localhost:5173 |
| **API** | http://localhost:8000 |
| **API docs** | http://localhost:8000/docs |
| Postgres | `localhost:5433` |
| Redis | `localhost:6379` |

Seed the demo user and sample workflow:

```bash
docker compose exec backend python -m app.scripts.seed
```

| | |
|--|--|
| Email | `owner@oneopen.local` |
| Password | `ChangeMe123!` |

### Local (SQLite + Vite)

**Backend**

```bash
cd backend
python -m venv .venv
# Windows: .\.venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=sqlite:///./oneopen_flow.db   # Windows: set DATABASE_URL=...
alembic upgrade head
python -m app.scripts.seed
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

Agents are optional in development — CLI and browser nodes fall back to local inline executors when no agent is registered.

## Example workflow

Ship includes **Build, Start and Validate Dynamic Application**
(`examples/build-start-validate.json`):

```text
Start
  → CLI build
  → CLI start
  → Wait / health API
  → Assert status 200
  → Open app → login
  → Wait for React render / ASPX postback
  → Assert dashboard
  → Extract build version → compare with CLI output
  → Screenshot → End
```

Variables such as `applicationType` (`react` | `aspx`), `baseUrl`, and credentials are configurable. Passwords use `{{secret.*}}`.

## Architecture

```text
┌──────────────────┐     SSE / HTTP     ┌─────────────────────┐
│  Flow Studio UI  │ ◄────────────────► │  FastAPI Backend    │
│  React + RF      │                    │  Workflow Engine    │
└──────────────────┘                    └──────────┬──────────┘
                                                   │
                    ┌──────────────────────────────┼──────────────────────────────┐
                    ▼                              ▼                              ▼
              PostgreSQL                         Redis                      Artifact storage
                    │                              │
        ┌───────────┴───────────┐      ┌───────────┴───────────┐
        ▼                       ▼      ▼                       ▼
 Browser Agent            CLI Agent   Celery worker      Workboard API
 (Playwright)           (Bash/PS/CMD)
```

Workflows are **versioned JSON**, independent of agent language. Node executors are plugins — the orchestrator does not hardcode node logic.

## Auth & OTP

| Node | Purpose |
|------|---------|
| Wait for Email | IMAP poll for verification mail |
| Extract OTP / Link | Parse codes and verify URLs |
| Generate / Verify TOTP | Authenticator apps via `pyotp` |
| Human OTP Input | Pause run until an operator submits a code |
| Fill OTP Field | Type the code into the browser |

See [docs/auth-verification.md](docs/auth-verification.md).

## API sketch

```bash
# Login
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@oneopen.local","password":"ChangeMe123!"}'

# Run a workflow
curl -s -X POST http://localhost:8000/api/workflows/<id>/run \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"inputs":{}}'

# Resume after human OTP
curl -s -X POST http://localhost:8000/api/runs/<run_id>/provide-input \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"otp":"123456"}'
```

Interactive OpenAPI: http://localhost:8000/docs

## Documentation

| Guide | |
|-------|--|
| [Architecture](docs/architecture.md) | System design |
| [Workflow schema](docs/workflow-schema.md) | JSON model & variables |
| [Browser locators](docs/browser-locators.md) | Fingerprints & healing |
| [ASPX support](docs/aspx-support.md) | Web Forms postbacks |
| [React support](docs/react-support.md) | Dynamic SPA waits |
| [Auth verification](docs/auth-verification.md) | Email / OTP / TOTP / HITL |
| [CLI agent](docs/cli-agent.md) | Registration & security |
| [Security](docs/security.md) | Permissions & secrets |
| [Workboard](docs/workboard-integration.md) | Defects & retest |
| [Local development](docs/local-development.md) | Setup details |

Build Sphinx HTML (Furo theme):

```bash
pip install -r docs/requirements-docs.txt
sphinx-build -b html docs docs/_build/html
# open docs/_build/html/index.html
```

## Project layout

```text
OneOpen-Flow/
├── frontend/          # React Studio (Vite)
├── backend/           # FastAPI + Celery + Alembic
├── agents/
│   ├── browser/       # Playwright agent
│   └── cli/           # Shell agent
├── docs/              # Guides + Sphinx
├── examples/          # Sample workflows
└── docker-compose.yml
```

## Tests

```bash
# Backend
cd backend && pip install -r requirements-dev.txt && pytest -q

# Frontend
cd frontend && npm test

# Browser agent helpers
cd agents/browser && npm test

# CLI agent
cd agents/cli && pytest -q
```

## Configuration

Copy [`.env.example`](.env.example) to `.env`. Important keys:

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | JWT signing |
| `ENCRYPTION_KEY` | Secret encryption at rest |
| `DATABASE_URL` | Postgres or SQLite |
| `REDIS_URL` / `CELERY_*` | Broker & results |
| `WORKBOARD_API_URL` | OneOpen Workboard API |
| `STORAGE_LOCAL_PATH` | Artifacts root |

## Contributing

1. Fork and create a feature branch
2. Keep changes focused; match existing module boundaries
3. Add/adjust tests for engine, agents, or Studio behavior
4. Open a PR against `main` with a clear summary

Issues and ideas are welcome in [GitHub Issues](https://github.com/1-OpenSource/OneOpen-Flow/issues).

## Part of OneOpenSource

OneOpen Flow sits alongside [Annotator](https://github.com/1-OpenSource/OneOpen-Annotator), Workboard, and other open tools at [oneopensource.org](https://oneopensource.org).

<p align="center">
  <img src="docs/logo-banner.svg" alt="OneOpen Flow" width="320">
</p>

## License

Licensed under the [Apache License 2.0](LICENSE).
