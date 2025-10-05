# Environment Setup & Operational Runbooks

This document explains how to bootstrap the Retail Delivery Fee (RDF) stack for
local development or CI, which services are involved, and how to validate the
install with the automated smoke test.

## Prerequisites

| Tool | Version | Notes |
| ---- | ------- | ----- |
| Docker & Docker Compose | Latest stable | Required for local parity with CI. |
| Python | 3.11+ | Needed only if running the backend outside Docker. |
| Node.js & npm | Node 18+, npm 9+ | Required for frontend-only workflows. |

## Services

Docker Compose orchestrates the full stack:

| Service | Purpose | Ports |
| ------- | ------- | ----- |
| `db` | PostgreSQL 16 with persistent volume `postgres_data`. | `5432` |
| `api` | FastAPI application served by `uvicorn`. Depends on `db`. | `8000` |
| `frontend` | Vite + React application served via Nginx. Depends on `api`. | `8080` |
| `pgadmin` | Optional admin UI for PostgreSQL (enabled via `make dev-tools`). | `5050` |

## Environment variables

Most configuration is driven by the `.env` file or Compose service
configuration. The key variables are:

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `DATABASE_URL` | `postgresql+psycopg://user:pass@db:5432/rdf` | SQLAlchemy connection string for the API. |
| `JWT_SECRET` | `change-me-in-production` | Secret used to sign session tokens. Override in non-dev envs. |
| `JWT_EXPIRE_MINUTES` | `1440` | Lifetime (in minutes) for issued JWT access tokens. |
| `APP_ENV` | `dev` | Used by the backend to toggle development behaviors. |
| `VITE_API_BASE_URL` | `http://localhost:8000/api` | Frontend base URL for the API. |
| `SMOKE_API_BASE_URL` | `http://localhost:8000/api` | Optional override for `make smoke` when running outside Docker. |
| `SMOKE_EMAIL` | `smoke-tester@example.com` | User email used by the smoke test. |
| `SMOKE_PASSWORD` | `change-me` | Password used by the smoke test. |
| `SMOKE_HMAC_SECRET` | `demo-hmac-secret` | HMAC secret consumed by `make security-smoke`; override when rotating store secrets. |
| `SMOKE_BILLING_PLAN` | `pro` | Plan tier exercised by `make billing-smoke`. |
| `STRIPE_SECRET_KEY` | _(unset)_ | Enables billing endpoints; when empty the API returns `503 billing_unconfigured`. |
| `STRIPE_WEBHOOK_SECRET` | _(unset)_ | Signature used to verify Stripe webhooks. |
| `STRIPE_PRICE_ID_STARTER/PRO/PLUS` | _(unset)_ | Plan → price ID mapping used when creating Checkout sessions. |
| `HMAC_MAX_SKEW_SECONDS` | `300` | Allowed clock drift (± seconds) for signed `/v1/fees/apply` requests. |
| `HMAC_REPLAY_TTL_SECONDS` | `600` | Time-to-live for nonce records used to detect replays. |

> Copy `.env.example` to `.env` when you need to override any defaults.

## Runbook: make dev

Starts the full stack in the foreground.

1. Ensure Docker is running.
2. Execute `make dev` from the repository root.
3. Wait for the logs to show the API on `0.0.0.0:8000` and Vite assets serving on
   port `8080`.
4. Visit <http://localhost:5173> for the development frontend or
   <http://localhost:8080> for the production bundle served by Nginx.

Use `CTRL+C` to stop all containers.

## Runbook: make migrate

Applies database migrations inside the running API container.

1. Ensure the stack is running (`make up` or `make dev`).
2. Execute `make migrate`.
3. Confirm the command finishes with Alembic reporting `INFO  [alembic.runtime.migration] Running upgrade` and `OK`.
4. If errors occur, inspect API logs via `make logs-api` and re-run after
   resolving the issue.

## Runbook: make seed

Populates the database with deterministic demo data (`store_demo_1` and
`store_demo_2`, subscriptions, rule versions, etc.).

1. Ensure the stack is running and migrations are applied.
2. Execute `make seed`.
3. Verify the command prints `Database seeded successfully!`.
4. If re-running, the script is idempotent and will only insert missing records.
5. Seeded timestamp fields (e.g., subscription trials, audit logs) now return UTC
   offsets in responses such as `2024-01-01T00:00:00+00:00`.

## Runbook: make smoke

Validates the end-to-end experience using seeded data.

1. Ensure the stack is running (`make up`) and the database has been migrated &
   seeded (`make migrate && make seed`).
2. Execute `make smoke`.
3. The target will:
   - Call the login endpoint to provision or reuse a demo user.
   - Request a Minnesota quote and apply both Minnesota and Colorado fees.
   - Fetch recent audit log entries for the demo store.
   - Download both the Minnesota summary (JSON) and Colorado DR-1786 (CSV)
     reports.
4. Success output resembles:

   ```
   Smoke test completed successfully.
   MN quote lines: 1
   MN apply lines: 1
   CO apply lines: 1
   Audit events fetched: 2
   ```
5. On failure, inspect the non-zero exit message in the terminal and review API
   container logs (`make logs-api`).

## Runbook: make analytics-smoke

Validates the analytics overview endpoint and Prometheus counter snapshots.

1. Ensure the stack is running (`make up`) and seeded (`make migrate && make seed`).
2. Execute `make analytics-smoke`.
3. The target will:
   - Log in with the smoke credentials and call `/v1/analytics/overview`.
   - Assert KPI cards are returned with at least one metric.
   - Validate the recent decisions feed supplies cursor metadata.
   - Confirm Prometheus counters are included in the response payload.
4. Inspect the console output for the counter snapshot and activity feed length.

## CI usage

GitHub Actions workflows under `.github/workflows` provide parity with these
runbooks:

- `backend.yml` provisions PostgreSQL, applies migrations, seeds the database,
  copies `.env.example` to `.env` for Compose parity, and runs `pytest`.
- `frontend.yml` performs `npm install`, `npm run typecheck`, and `npm run build`.
- The smoke test can be invoked in CI by running `make up`, `make migrate`,
  `make seed`, and `make smoke` sequentially on a runner with Docker access.

## Runbook: make security-smoke

Validates HMAC signing, timestamp skew, and replay protection.

1. Ensure the stack is running and seeded (`make migrate && make seed`).
2. Export `SMOKE_HMAC_SECRET` if the seed default has been rotated.
3. Execute `make security-smoke`.
4. The target will:
   - Log in, fetch a demo store, and sign `/v1/fees/apply` payloads with timestamp + nonce headers.
   - Assert the initial apply succeeds, a replay attempt returns `409` with `detail.code = replay_detected`, and a stale timestamp yields `401`.
   - Print summary output including the replay/stale status codes.
5. On failure, inspect the exit message and check `security` logs or Prometheus counters via `/metrics`.

## Runbook: make billing-smoke

Validates billing endpoints end-to-end or emits a skip when Stripe is not configured.

1. Ensure the stack is running and seeded (`make migrate && make seed`).
2. Set `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and `STRIPE_PRICE_ID_*` when exercising the full Stripe flow. Leave them unset to confirm graceful degradation.
3. Execute `make billing-smoke`.
4. Output shows either:
   - `✓` lines summarising entitlements, usage, checkout session ID, and portal URL when Stripe is configured, or
   - `⚠ SKIP: Stripe billing not configured (billing_unconfigured returned).`
5. Evidence is written to `docs/certification/EVIDENCE/billing_smoke.txt`.
