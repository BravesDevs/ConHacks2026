# Backend (FastAPI)

This folder contains the FastAPI backend for **InfraBott** — a Terraform optimization service that ingests infrastructure-as-code via GitHub webhooks, queues optimization runs, and streams progress to clients over WebSockets.

## Project info

- **Stack**: Python 3.11+, FastAPI, async SQLAlchemy 2.x + asyncpg, Alembic, pydantic-settings.
- **Layout**: routers under `app/api/routers/`, models under `app/models/`, in-process pub/sub in `app/services/events.py`, settings in `app/core/config.py`.
- **Entrypoints**: `POST /webhooks/github` (snapshot ingest), `POST /jobs/optimize` (scheduler) / `POST /jobs/optimize/manual` (manual trigger), `GET /runs/*` (read), `GET /ws` (live updates).
- **Database**: managed Postgres (provisioned by the sibling `terraform/` stack). The connection string from `terraform output -raw postgres_uri` plugs straight into `DATABASE_URL` — `app/db/session.py` rewrites the `postgresql://` prefix to `postgresql+asyncpg://` automatically.

## Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Configure

Set environment variables (or create a local `.env` file):

### Required for local development

- `DATABASE_URL=postgresql://user:pass@host:5432/dbname` — Postgres connection string. Used by the app and by Alembic. The sibling `terraform/` stack outputs this as `postgres_uri`.
- `GITHUB_CLIENT_ID=...` — GitHub OAuth App client ID.
- `GITHUB_CLIENT_SECRET=...` — GitHub OAuth App client secret.
- `GITHUB_REDIRECT_URI=http://localhost:8000/auth/github/callback` — OAuth redirect URI registered on the GitHub OAuth App; must match exactly.
- `GITHUB_TOKEN_ENCRYPTION_KEY=...` — Fernet key used to encrypt GitHub access tokens at rest. Generate one with:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

### Other settings

- `APP_ENV=local|staging|prod`
- `CORS_ORIGINS=https://...` (comma-separated; optional)
- `GITHUB_WEBHOOK_SECRET=...`
- `INTERNAL_JOB_TOKEN=...` (for `POST /jobs/optimize`)
- `MANUAL_TRIGGER_TOKEN=...` (for `POST /jobs/optimize/manual`)
- `SCHEDULER_ENABLED=true|false`

## Database migrations

Schema is managed with **Alembic** (config in `alembic.ini`, env in `alembic/env.py`). `DATABASE_URL` must be set — Alembic reads it from the environment (or `.env`) and rewrites the driver to `asyncpg` automatically.

```bash
# Apply all pending migrations
.venv/bin/alembic upgrade head

# Create a new auto-generated migration after editing models in app/models/
.venv/bin/alembic revision --autogenerate -m "describe change"

# Roll back one revision
.venv/bin/alembic downgrade -1

# Show current DB revision / full history
.venv/bin/alembic current
.venv/bin/alembic history
```

Run `alembic upgrade head` once after first checkout, and again whenever you pull new revisions under `alembic/versions/`.

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
