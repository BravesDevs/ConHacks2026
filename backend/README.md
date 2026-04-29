# Backend (FastAPI)

This folder contains the FastAPI backend.

## Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Configure

Set environment variables (or create a local `.env` file):

- `APP_ENV=local|staging|prod`
- `DATABASE_URL=postgresql://...`
- `CORS_ORIGINS=https://...` (comma-separated; optional)
- `GITHUB_WEBHOOK_SECRET=...`
- `INTERNAL_JOB_TOKEN=...` (for `POST /jobs/optimize`)
- `MANUAL_TRIGGER_TOKEN=...` (for `POST /jobs/optimize/manual`)
- `SCHEDULER_ENABLED=true|false`

## Run

```bash
PYTHONPATH=. DATABASE_URL='postgresql://...' .venv/bin/python -m uvicorn app.main:app --reload
```

## API

- `GET /healthz`
- `POST /webhooks/github`
- `POST /jobs/optimize`
- `POST /jobs/optimize/manual`
- `GET /runs/latest?repo=...`
- `GET /runs/{run_id}`
- `GET /runs?repo=...&limit=...`
- `GET /ws`
