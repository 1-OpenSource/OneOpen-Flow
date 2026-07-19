# OneOpen Flow

Open-source visual workflow orchestration and validation for the OneOpenSource platform.

OneOpen Flow automates complete technical workflows across browsers, CLI commands, REST APIs, databases, files, and Docker — with first-class support for dynamic ASPX and React applications.

## Modules

- **OneOpen Flow Studio** — React Flow visual designer
- **OneOpen Workflow Engine** — FastAPI + Celery graph orchestration
- **OneOpen Browser Agent** — Playwright (Node.js)
- **OneOpen CLI Agent** — Bash / PowerShell / CMD (Python)
- **OneOpen API Agent** — REST request + assertion nodes
- **OneOpen Database Agent** — PostgreSQL query/assert nodes
- **OneOpen Execution Evidence** — screenshots, traces, logs, ZIP packages
- **OneOpen Workboard Integration** — defect creation and reproduction reruns

## Quick start (Docker Compose)

```bash
docker compose up --build
```

Services:

| Service | URL / port |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Postgres | localhost:5433 |
| Redis | localhost:6379 |

Seed a demo account and workflow:

```bash
docker compose exec backend python -m app.scripts.seed
```

Default login after seed:

- Email: `owner@oneopen.local`
- Password: `ChangeMe123!`

## Local development (without Docker for app processes)

### Backend

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate   # Windows
pip install -r requirements-dev.txt
set DATABASE_URL=sqlite:///./oneopen_flow.db
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Agents (optional — local inline execution works without them)

```bash
# CLI agent
cd agents/cli
pip install httpx
set FLOW_API_URL=http://localhost:8000
python src/main.py

# Browser agent
cd agents/browser
npm install
npx playwright install chromium
set FLOW_API_URL=http://localhost:8000
npm run dev
```

## Example workflow

Import `examples/build-start-validate.json` from Flow Studio, or run the seed script.

It performs:

Start → CLI build → CLI start → wait → health API → assert 200 → open app → login → wait for React/ASPX → assert dashboard → extract build version → compare with CLI output → screenshot → End

## Documentation

Markdown guides live in `docs/`. Sphinx HTML docs (Furo theme):

```bash
pip install -r docs/requirements-docs.txt
sphinx-build -b html docs docs/_build/html
```

Open `docs/_build/html/index.html`.

Guide index:

- [Architecture](docs/architecture.md)
- [Workflow schema](docs/workflow-schema.md)
- [Browser locators](docs/browser-locators.md)
- [ASPX support](docs/aspx-support.md)
- [React support](docs/react-support.md)
- [CLI agent](docs/cli-agent.md)
- [Security](docs/security.md)
- [Workboard integration](docs/workboard-integration.md)
- [Local development](docs/local-development.md)

## API examples

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"owner@oneopen.local\",\"password\":\"ChangeMe123!\"}"

# List workflows
curl http://localhost:8000/api/workflows -H "Authorization: Bearer <token>"

# Run workflow
curl -X POST http://localhost:8000/api/workflows/<id>/run \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d "{\"inputs\":{}}"
```

## Workboard integration

Set `WORKBOARD_API_URL` to your OneOpen Workboard API (default `http://localhost:8001/api`). Failed runs can create Workboard defects with evidence and a **Run Reproduction** link. When a linked item moves to Ready for Testing / `IN_REVIEW`, POST to `/api/triggers/workboard-status` to auto-retest.

## License

Part of the OneOpenSource ecosystem.
