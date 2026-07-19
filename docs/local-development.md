# Local development

## Prerequisites

- Python 3.12+
- Node.js 22+
- Docker Desktop (recommended)
- Optional: Playwright browsers for real browser automation

## Docker Compose

```bash
docker compose up --build
docker compose exec backend python -m app.scripts.seed
```

Open http://localhost:5173

## Environment variables

Copy `.env.example` to `.env`:

- `SECRET_KEY` — JWT signing
- `ENCRYPTION_KEY` — secret encryption
- `DATABASE_URL` — Postgres or SQLite
- `REDIS_URL` / `CELERY_*` — orchestration
- `WORKBOARD_API_URL` — Workboard API base
- `STORAGE_LOCAL_PATH` — artifact root

## Tests

```bash
# Backend
cd backend
pip install -r requirements-dev.txt
pytest -q

# Frontend
cd frontend
npm install
npm test

# Browser agent helpers
cd agents/browser
npm install
npm test

# CLI agent
cd agents/cli
pytest -q
```

## Stable locator contract

```html
<button data-oneopen-id="customer.save">Save</button>
```

```html
<asp:Button ID="SaveButton" ClientIDMode="Static" runat="server"
  Text="Save" data-oneopen-id="customer.save" />
```
