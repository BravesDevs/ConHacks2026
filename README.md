<div align="center">

# InfraBott

### Terraform optimization, on autopilot.

InfraBott watches your infrastructure-as-code, learns from real usage metrics, and proposes
right-sized Terraform changes as pull requests — so cloud spend and capacity stay in step with reality.

<br />

![Terraform](https://img.shields.io/badge/Terraform-7B42BC?style=for-the-badge&logo=terraform&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![DigitalOcean](https://img.shields.io/badge/DigitalOcean-0080FF?style=for-the-badge&logo=digitalocean&logoColor=white)

</div>

---

## What it does

<table>
<tr>
<td width="33%" valign="top" align="center">

<img src="https://cdn.simpleicons.org/terraform/7B42BC" width="48" height="48" alt="Terraform" />

### Terraform-aware

Ingests your `.tf` snapshots through GitHub webhooks, fingerprints them by SHA, and tracks every revision as a first-class artifact.

</td>
<td width="33%" valign="top" align="center">

<img src="https://cdn.simpleicons.org/claude" width="48" height="48" alt="AI Agent" />

### AI Agent

An optimization agent reads each snapshot alongside live metrics, then drafts a `suggested_config` — instance sizes, replica counts, storage tiers — with the reasoning attached.

</td>
<td width="33%" valign="top" align="center">

<img src="https://cdn.simpleicons.org/githubactions/2088FF" width="48" height="48" alt="GitHub" />

### PR-native

Suggestions land where engineers already review code: a pull request on the source repo, ready to merge, reject, or tweak.

</td>
</tr>
</table>

---

## Architecture

```
        ┌─────────────────┐                    ┌──────────────────┐
        │  GitHub Repo    │  webhook (push)    │  FastAPI Backend │
        │  *.tf files     │ ─────────────────▶ │   /webhooks/...  │
        └─────────────────┘                    └────────┬─────────┘
                                                        │
                                       snapshot + event │ (in-process pub/sub)
                                                        ▼
        ┌─────────────────┐                    ┌──────────────────┐
        │   React UI      │ ◀── WebSocket ──── │  Optimization    │
        │  live run feed  │                    │  Run + AI Agent  │
        └─────────────────┘                    └────────┬─────────┘
                                                        │
                                              suggested │ config
                                                        ▼
                                               ┌──────────────────┐
                                               │  GitHub PR       │
                                               └──────────────────┘
```

The system models a single end-to-end flow: **detect a Terraform change → snapshot it → run an
optimization pass → stream progress → open a PR**. Every stage is observable; nothing is a black box.

---

## Project layout

<table>
<tr>
<td width="33%" valign="top">

### <img src="https://cdn.simpleicons.org/react/61DAFB" width="20" height="20" align="center" /> &nbsp; `frontend/`

The operator console — a Vite + React + TypeScript dashboard built on Radix UI and shadcn primitives.
Connects to the backend WebSocket to render run state in real time, lets you trigger manual
optimization passes, and previews the diff that will become a PR.

**Stack:** React, TypeScript, Vite, Tailwind, Radix UI, shadcn/ui, MUI, Supabase client.

</td>
<td width="33%" valign="top">

### <img src="https://cdn.simpleicons.org/fastapi/009688" width="20" height="20" align="center" /> &nbsp; `backend/`

The brains — a FastAPI service that owns webhook ingest, run orchestration, persistence, and the
event bus that powers live updates. Bearer-token gated job endpoints separate scheduled runs
from manual triggers.

**Stack:** Python 3.11+, FastAPI, async SQLAlchemy 2.x, asyncpg, Alembic, pydantic-settings, Postgres.

</td>
<td width="33%" valign="top">

### <img src="https://cdn.simpleicons.org/terraform/7B42BC" width="20" height="20" align="center" /> &nbsp; `terraform/`

Infrastructure for InfraBott itself — DigitalOcean managed Postgres (and an optional Redis cluster
for future cross-worker fan-out). Outputs `postgres_uri` / `redis_uri` plug straight into the
backend's `DATABASE_URL` / `REDIS_URL`.

**Stack:** Terraform, DigitalOcean provider, managed Postgres, managed Redis.

</td>
</tr>
</table>

---

## Core concepts

| Concept | What it is |
|---|---|
| **`TerraformSnapshot`** | An immutable record of a `.tf` tree at a given commit SHA. Every webhook delivery becomes one. |
| **`MetricsSnapshot`** | A point-in-time capture of runtime telemetry the agent reasons over alongside the Terraform. |
| **`OptimizationRun`** | The unit of work. Has a status enum (`queued → running → suggestion_ready → pr_opened`), inputs (the two snapshots), constraints, and the agent's `suggested_config`. |
| **`WebhookDelivery`** | Idempotency record. A unique constraint on `(delivery_id, repo, event_type)` makes GitHub retries safe. |
| **Event bus** | An in-process asyncio pub/sub. Topics: `terraform.updated`, `run.queued`, `run.running`, `run.suggestion_ready`, `run.pr_opened`, `run.failed`. The WebSocket endpoint subscribes clients to this set. |

---

## API surface

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/webhooks/github` | Ingest a Terraform change. HMAC-validated, deduped. |
| `POST` | `/jobs/optimize` | Scheduler-triggered run across the latest snapshot. |
| `POST` | `/jobs/optimize/manual` | Operator-triggered run for a specific repo / SHA. |
| `GET`  | `/runs/latest?repo=…` | Most recent run for a repo. |
| `GET`  | `/runs/{id}` | A specific run. |
| `GET`  | `/runs?repo=…&limit=…` | Run history. |
| `WS`   | `/ws` | Live event stream — drives the UI. |
| `GET`  | `/healthz` | Liveness. |

---

<div align="center">

Built at **ConHacks 2026** &nbsp;·&nbsp; Crafted with <img src="https://cdn.simpleicons.org/terraform/7B42BC" width="14" height="14" align="center" /> &nbsp;and a small army of agents.

</div>
