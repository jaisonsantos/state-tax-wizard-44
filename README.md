# State Tax Wizard

State Tax Wizard is a full-stack demo application for configurable U.S. state fee rules, auditability, billing, webhooks, and operational controls.

The project combines a FastAPI backend with a React/TypeScript frontend and models fee calculation as a production-style workflow with persistence, replay protection, observability, and integration boundaries.

## Why this project

Rules-heavy domains are rarely just about calculating a number. They also need versioned rules, audit trails, idempotency, security, reporting, and safe integrations. State Tax Wizard explores those concerns in one compact system.

## Engineering highlights

- **FastAPI backend** with JWT authentication and Alembic migrations.
- **Configurable fee rules** for Minnesota and Colorado.
- **Idempotent fee application** with persisted `OrderFee` records.
- **Structured audit logging** for rule decisions and operational events.
- **HMAC request signing** with replay protection on sensitive endpoints.
- **Prometheus metrics** and JSON logs enriched with request, store, and security context.
- **Outbound webhooks** with signatures, retries, dead-letter handling, and administrative replay.
- **Stripe billing flows** with multiple pricing tiers and graceful degradation when billing is not configured.
- **WooCommerce and Shopify integration connectors** guarded by feature flags.
- **Shared TypeScript SDK** for integration consumers.
- **React/Vite frontend** with fee playground, logs, CSV export, and store switching.
- **GitHub Actions CI** for backend migrations/tests and frontend typechecking/builds.

## Architecture

```text
                   ┌──────────────────┐
                   │ React / Vite UI  │
                   └────────┬─────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │    FastAPI    │
                    ├───────────────┤
                    │ auth / fees   │
                    │ audit / HMAC  │
                    │ billing       │
                    │ webhooks      │
                    │ integrations  │
                    └───────┬───────┘
                            │
            ┌───────────────┼────────────────┐
            ▼               ▼                ▼
       PostgreSQL        Prometheus        Stripe
            │
            ├── OrderFee
            ├── AuditLog
            ├── billing state
            └── webhook state
```

## Core capabilities

- State-specific rule evaluation.
- Idempotent fee application.
- Audit trail and CSV export.
- HMAC signing and replay prevention.
- Billing tiers and usage monitoring.
- Signed outbound webhook delivery.
- Retry, DLQ, and replay flows.
- WooCommerce and Shopify connector boundaries.
- Prometheus metrics and structured logging.

## Tech stack

- **Backend:** FastAPI, Python, Alembic
- **Frontend:** React, TypeScript, Vite, Tailwind
- **Database:** PostgreSQL; SQLite support for tests
- **Cache / rate limiting:** Redis
- **Billing:** Stripe
- **Observability:** Prometheus, JSON logs
- **Testing:** Pytest, smoke tests, Playwright
- **CI:** GitHub Actions

## Project structure

```text
backend/                FastAPI app, migrations, tests, seed scripts
src/                    React frontend
.github/workflows/      CI pipelines
docs/                   API, security, observability and product docs
docker-compose.yml      Local development stack
```

## Quick start

```bash
make dev
make migrate
make seed
```

Frontend: `http://localhost:5173`

API: `http://localhost:8000`

API docs: `http://localhost:8000/api/docs`

Stop the stack with:

```bash
make down
```

## Local backend development

```bash
pip install -r backend/requirements.txt
export DATABASE_URL=sqlite:///./dev.db
alembic upgrade head
python backend/seed_data.py
uvicorn backend.app.main:app --reload
```

## Frontend development

```bash
npm install
npm run dev
```

The frontend reads the API location from `VITE_API_URL`.

## Security model

Sensitive fee requests can be protected with HMAC signing. The implementation includes configurable clock-skew tolerance and replay TTLs so the same signed request cannot be reused indefinitely.

Relevant settings include:

```env
JWT_SECRET=<application-secret>
SMOKE_HMAC_SECRET=<test-only-secret>
HMAC_MAX_SKEW_SECONDS=<seconds>
HMAC_REPLAY_TTL_SECONDS=<seconds>
```

Real credentials should be supplied through local environment files or deployment secrets rather than committed source files.

## Billing

Stripe integration is optional and fails explicitly when it is not configured.

```env
STRIPE_SECRET_KEY=<your-stripe-secret-key>
STRIPE_WEBHOOK_SECRET=<your-webhook-signing-secret>
STRIPE_PRICE_ID_STARTER=<price-id>
STRIPE_PRICE_ID_PRO=<price-id>
STRIPE_PRICE_ID_PLUS=<price-id>
```

The project also models plan limits, usage thresholds, and enterprise tiers.

## Webhooks

Outbound Taxo webhooks cover events such as fee application, skipped fees, report readiness, and HMAC rotation. Delivery includes signing, retry scheduling, metrics, dead-letter handling, and administrative replay.

## Testing

```bash
pytest -q
npm run typecheck
npm run build
make reports-smoke
make security-smoke
make billing-smoke
make webhooks-smoke
make integrations-smoke
make woocommerce-test
make shopify-test
make sdk-test
```

Optional Playwright report-download flow:

```bash
ENABLE_REPORT_DOWNLOAD_TEST=1 npm run test:e2e
```

## CI

GitHub Actions includes separate backend and frontend workflows. Backend CI applies migrations and runs tests against PostgreSQL; frontend CI performs TypeScript checks and production builds.

## Documentation

Useful references:

- [`docs/postman/README.md`](docs/postman/README.md)
- [`docs/observability.md`](docs/observability.md)
- [`docs/security/hmac.md`](docs/security/hmac.md)
- [`docs/backlog/README.md`](docs/backlog/README.md)
- [`docs/reports/co_dr1786.md`](docs/reports/co_dr1786.md)

## Scope

State Tax Wizard is a demo/portfolio system rather than tax advice or a production tax engine. Its purpose is to demonstrate backend architecture for a rules-heavy domain with persistence, auditability, integrations, billing, observability, and security controls.
