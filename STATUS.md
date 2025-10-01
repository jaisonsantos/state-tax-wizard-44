# Project Status Report

> Consulte o [backlog consolidado](docs/backlog/README.md) para dependências detalhadas e milestones futuros.

## Backend
- `/v1/analytics/overview` aggregates transactional data, audit cursors, and Prometheus counter snapshots, and emits structured logs plus the `analytics_dashboard_loaded_total` counter. 【F:backend/app/routers/analytics.py†L1-L69】【F:backend/app/services/analytics_service.py†L20-L205】【F:backend/app/observability.py†L5-L73】
- Fee endpoints enforce tenant access, track latency histograms, apply a Redis-backed distributed rate limiter, and validate replay-resistant HMAC signatures with nonce persistence and low-cardinality security logging. 【F:backend/app/routers/fees.py†L1-L214】【F:backend/app/security/hmac.py†L1-L168】【F:backend/app/security/rate_limit.py†L1-L146】
- Authentication/session APIs persist tokens and expose session metadata consumed by the frontend. 【F:backend/app/models/models.py†L1-L168】【F:src/context/AuthContext.tsx†L1-L108】
- Seeds create demo stores, analytics-ready fee history, reversal data, and report export audit logs for dashboards/tests. 【F:backend/seed_data.py†L1-L213】

## Frontend
- Dashboard fetches analytics overview via React Query, renders KPI cards, Prometheus snapshots, and a paginated recent decisions feed with load-more handling. 【F:src/pages/Dashboard.tsx†L1-L242】
- Global layout displays store selector, session metadata, and logout controls using AuthContext. 【F:src/components/layout/AppLayout.tsx†L1-L125】
- Reports and Logs pages (not shown here) rely on `/v1/audit` and report endpoints already validated by smoke/Playwright tests. 【F:tests/e2e/reports-download.spec.ts†L1-L56】【F:backend/smoke_test.py†L1-L170】
- Settings adds an operator-facing HMAC rotation control with copy-to-clipboard helper and integrates security error guidance surfaced from the backend schema. 【F:src/pages/Settings.tsx†L16-L420】【F:src/lib/api.ts†L1-L220】

## Data & Seeds
- `seed_data.py` backfills fee history for two demo stores, including absorbed vs. shown lines, reversals, and report export audits to support analytics slices. 【F:backend/seed_data.py†L72-L173】
- Rule versions for MN/CO are ensured with effective dates and parameters for deterministic fee calculations. 【F:backend/seed_data.py†L174-L212】

## Observability
- Prometheus counters and histograms exist for fee decisions, report exports, auth events, analytics dashboard loads, security failures/replays, and rate-limit throttles; observability docs describe these signals. 【F:backend/app/observability.py†L5-L95】【F:docs/security/observability.md†L1-L160】
- Structured logging helpers (`log_fee_event`, `log_report_event`, `log_analytics_event`, `log_security_event`) are invoked from routers/services. 【F:backend/app/observability.py†L92-L133】【F:backend/app/routers/analytics.py†L45-L68】【F:backend/app/security/hmac.py†L67-L160】

## Automation & QA
- Pytest suite covers analytics responses, replay-resistant HMAC enforcement, rate limiting, fee flows, and reporting contracts. 【F:backend/tests/test_analytics_overview.py†L1-L43】【F:backend/tests/test_fee_security.py†L1-L176】【F:backend/tests/test_report_contracts.py†L1-L120】
- Smoke test exercises login, settings update, fee quote/apply, audit history, report exports, metrics endpoint, and now supports analytics-only, reports-only, and security-only modes. 【F:backend/smoke_test.py†L1-L280】
- Playwright e2e specs validate analytics dashboard rendering and report downloads (flagged via env vars), while Makefile exposes `smoke`, `reports-smoke`, and `analytics-smoke` targets. 【F:tests/e2e/analytics-dashboard.spec.ts†L1-L45】【F:tests/e2e/reports-download.spec.ts†L1-L56】【F:Makefile†L1-L55】

## Documentation & Tooling
- API references exist for analytics, fees, and store settings, aligned with implemented endpoints. 【F:docs/api/analytics.md†L1-L80】【F:docs/api/fees.md†L1-L80】【F:docs/api/store-settings.md†L1-L120】
- UI guide documents analytics dashboard behavior, session metadata, and export flows. 【F:docs/security/ui-guide.md†L1-L80】
- Postman README/collection includes analytics/report evidence logging, automated HMAC signing, and replay/stale timestamp scenarios. 【F:docs/postman/README.md†L1-L140】【F:docs/postman/state-tax-wizard.postman_collection.json†L1-L200】
- Dedicated HMAC signing guide documents headers, examples, and rotation guidance. 【F:docs/security/hmac.md†L1-L120】

## Divergences & Gaps
- Operations runbooks should call out required environment variables (`REDIS_URL`, `SMOKE_HMAC_SECRET`) and storage expectations for rotated secrets when deploying outside Docker demos. 【F:README.md†L80-L130】【F:docs/postman/README.md†L1-L140】
- Security smoke/Newman flows currently assume a PostgreSQL backend because the schema relies on native UUID types; local runs need Dockerised Postgres (see checklist note) until SQLite UUID shims are introduced. 【F:CHECKLIST.md†L47-L60】【F:backend/alembic/versions/202501010000_initial_schema.py†L13-L120】

## Recommended Next Step (Milestone Alignment)
- **NEXT_SLICE: Billing/Stripe (M5)** — connect the storefront to Stripe billing (subscription sync, entitlement gating) now that security hardening is complete; document required webhooks and update smoke tests to cover billing toggles.
