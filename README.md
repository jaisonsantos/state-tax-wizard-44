# State Tax Wizard

State Tax Wizard is a full-stack demo application that showcases a configurable fee engine for U.S. state taxes. It combines a FastAPI backend with a React frontend to simulate fee calculations, audit logging, and observability for demo stores.

## Features

- **FastAPI backend** with JWT authentication, seeded demo data, idempotent fee application, and replay-protected HMAC signing on `/v1/fees/apply`.
- **Fee rules for Minnesota and Colorado** that persist `OrderFee` records and structured `AuditLog` entries.
- **Observability** via Prometheus metrics (`/metrics`) and JSON logs enriched with request, store, and security context.
- **React frontend** with a fee playground, audit log viewer, CSV export powered by a shared API client, and a persistent header menu for store switching and logout.
- **Continuous integration** workflows that run backend migrations/tests and frontend typechecking/builds.

## Project structure

```
backend/                # FastAPI application, Alembic migrations, tests, and seed script
src/                    # React frontend (Vite + TypeScript + Tailwind)
docker-compose.yml      # Local development stack (API, Postgres, frontend, Prometheus)
.github/workflows/      # GitHub Actions pipelines for backend and frontend
```

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- Docker & Docker Compose (for the recommended local stack)

## Getting started (Docker Compose)

1. Copy `.env.example` to `.env` if you need to override defaults.
2. Start the stack:

   ```sh
   make dev
   ```
   This launches the API, frontend, and supporting services. The frontend is available at <http://localhost:5173>, and the API at <http://localhost:8000>.
3. Apply database migrations and seed demo data (the login flow will also ensure the seed store exists):

   ```sh
   make migrate
   make seed
   ```
4. Stop the stack when you are done:

   ```sh
   make down
   ```

## Backend development

1. Create and activate a virtual environment.
2. Install dependencies:

   ```sh
   pip install -r backend/requirements.txt
   ```
3. Set `DATABASE_URL` (defaults to PostgreSQL when running via Docker; SQLite is supported for tests):

   ```sh
   export DATABASE_URL=sqlite:///./dev.db
   ```
4. Run migrations and seed data:

   ```sh
   alembic upgrade head
   python backend/seed_data.py
   ```
5. Start the FastAPI server:

   ```sh
   uvicorn backend.app.main:app --reload
   ```

### Prometheus metrics & logs

- Prometheus metrics are exposed at `/metrics`.
- Application logs are JSON-formatted and include fields such as `request_id`, `store_id`, `jurisdiction`, and `reason_codes`.

### Environment variables

- `DATABASE_URL`, `APP_ENV`, `JWT_SECRET`, and `SMOKE_HMAC_SECRET` retain their previous behaviour. The security smoke defaults to `demo-hmac-secret` but you should override it once secrets are rotated.
- `REDIS_URL` (optional) configures the distributed rate limiter. When running via Docker Compose the API service automatically connects to the bundled Redis container; set `REDIS_URL=redis://redis:6379/0` if you provision Redis yourself.
- `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` enable live billing flows; when unset the API returns `503` with `code="billing_unconfigured"`. If a store lacks Stripe metadata the portal endpoint responds with `400` (`code="stripe_customer_missing"`). Smokes/Newman exit gracefully in both cases.
- `STRIPE_PRICE_ID_STARTER`, `STRIPE_PRICE_ID_PRO`, and `STRIPE_PRICE_ID_PLUS` map plan tiers to Stripe price IDs. Populate them once products exist in your Stripe dashboard.
- `SMOKE_BILLING_PLAN` selects which plan tier the billing smoke exercises (defaults to `pro`).
- `HMAC_MAX_SKEW_SECONDS` and `HMAC_REPLAY_TTL_SECONDS` remain tunable via `.env`.

## Frontend development

1. Install dependencies:

   ```sh
   npm install
   ```
2. Start the development server:

   ```sh
   npm run dev
   ```
3. The React app consumes the backend API at `VITE_API_URL` (configure via `.env` or defaults to `/api`).

## Testing

- Backend tests:

  ```sh
  pytest -q
  ```
  Ensure `APP_ENV=dev` (default) so SQLite-based tests auto-create tables, or
  pre-create the schema when running against another environment.
- Frontend type-check:

  ```sh
  npm run typecheck
  ```
- Frontend build:

  ```sh
  npm run build
  ```
- Report export smoke (requires Docker services running):

  ```sh
  make reports-smoke
  ```
  Set `SMOKE_METRICS_URL` when the Prometheus endpoint is exposed on a separate
  host; otherwise the smoke test derives `/metrics` from `SMOKE_API_BASE_URL`.
- Security smoke (validates HMAC signing and replay protection):

  ```sh
  make security-smoke
  ```
  Run against any API instance (Docker Compose or local `uvicorn`) with migrations/seeds applied; SQLite and PostgreSQL are both supported after the GUID shim. Configure `SMOKE_HMAC_SECRET` if you rotate the seed secret; defaults to `demo-hmac-secret`.
- Billing smoke (Stripe checkout/portal & graceful degradation):

  ```sh
  make billing-smoke
  ```
  When Stripe variables are unset the script prints `⚠ SKIP: billing_unconfigured`; otherwise it asserts entitlements, usage, checkout (with `portal_session_id`), and portal APIs respond successfully. Stores without Stripe metadata return `400` with `code="stripe_customer_missing"`.
- Newman billing folder (optional, requires Postman env JSON with Stripe keys):

  ```sh
  make newman-billing
  ```
  Skips automatically when `docs/postman/local.postman_environment.json` is absent or Stripe credentials are not configured.
- Playwright download smoke (opt-in; requires frontend + API running and Chromium dependencies):

  ```sh
  ENABLE_REPORT_DOWNLOAD_TEST=1 npm run test:e2e
  ```

The Playwright script is disabled by default so CI pipelines can opt in once headless downloads are stable. When the environment variable is not set the command exits early after printing a skip message.

## Continuous integration

GitHub Actions workflows are provided under `.github/workflows/`:
- `backend.yml` spins up PostgreSQL with Docker Compose, installs backend dependencies, applies migrations, and runs `pytest`.
- `frontend.yml` installs Node dependencies, runs the TypeScript type-check, and builds the production bundle.

## Additional resources

- API reference: visit <http://localhost:8000/api/docs> for the automatically generated Swagger UI (the legacy `/docs` path now redirects here).
- Seed script: running `python backend/seed_data.py` guarantees the presence of the demo store and rule versions for Minnesota and Colorado.
- Audit logs: accessible through the `/v1/audit` endpoint and the frontend Logs page.
- Postman collection: follow [`docs/postman/README.md`](docs/postman/README.md) for setup, execution order, and Newman automation tips when importing `docs/postman/state-tax-wizard.postman_collection.json`.
- Backlog overview: explore [`docs/backlog/README.md`](docs/backlog/README.md) for milestone context, dependencies, and iteration checklists.
- Colorado DR 1786 CSV dictionary: see [`docs/reports/co_dr1786.md`](docs/reports/co_dr1786.md) for column definitions and reversal handling.
- Postman collection: import `docs/postman/state-tax-wizard.postman_collection.json` (schema v2.1) e execute uma request de login para preencher automaticamente `token`, `store_id` e configure `hmac_secret` antes de testar as rotas assinadas. Finalize com **Auth / Logout** para revogar a sessão e limpar as variáveis antes do próximo ciclo.
- Guia de segurança HMAC: [`docs/security/hmac.md`](docs/security/hmac.md) detalha o algoritmo de assinatura, exemplos de código e estratégias de rotação.
- Guia de interface: consulte [`docs/security/ui-guide.md`](docs/security/ui-guide.md) para entender estados de carregamento/erro na tela de reports e recomendações de acessibilidade.

## Roadmap status

- **Current stage**: Milestone 5 — Billing/Stripe integration is complete (subscriptions, usage enforcement, checkout/portal flows, and billing telemetry ship with evidence).
- **Next focus**: Milestone 6 — Platform integrations alpha (WooCommerce/Shopify connectors and SDK hardening). Track progress in the release plan backlog as items graduate to in-progress. 【F:docs/backlog/00_release_plan.md†L120-L190】
