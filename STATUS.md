# Project Status Report

> Consulte o [backlog consolidado](docs/backlog/README.md) para dependências detalhadas e milestones futuros.

## Backend

- `/v1/analytics/overview` aggregates transactional data, audit cursors, and Prometheus counter snapshots, and emits structured logs plus the `analytics_dashboard_loaded_total` counter. 【F:backend/app/routers/analytics.py†L1-L69】【F:backend/app/services/analytics_service.py†L20-L205】【F:backend/app/observability.py†L5-L73】
- Webhook ingestion persists Stripe events in `processed_webhooks`, enforces idempotency/DLQ, exposes replay API, and records audit logs. 【F:backend/app/services/webhook_service.py†L40-L220】【F:backend/app/routers/billing.py†L200-L270】【F:backend/app/models/models.py†L220-L260】
- Fee endpoints enforce tenant access, track latency histograms, apply a Redis-backed distributed rate limiter, and validate replay-resistant HMAC signatures with nonce persistence and low-cardinality security logging. 【F:backend/app/routers/fees.py†L1-L214】【F:backend/app/security/hmac.py†L1-L168】【F:backend/app/security/rate_limit.py†L1-L146】
- Authentication/session APIs persist tokens and expose session metadata consumed by the frontend. 【F:backend/app/models/models.py†L1-L168】【F:src/context/AuthContext.tsx†L1-L108】
- Seeds create demo stores, analytics-ready fee history, reversal data, and report export audit logs for dashboards/tests. 【F:backend/seed_data.py†L1-L213】
- Billing endpoints implement Stripe-backed entitlements, usage, checkout, portal, and webhook flows with graceful degradation (`503 billing_unconfigured`) when keys are absent. Stores without Stripe metadata now return `400 stripe_customer_missing`, and portal responses expose `portal_session_id` for the frontend and tooling. 【F:backend/app/routers/billing.py†L1-L220】【F:backend/app/services/stripe_service.py†L1-L230】【F:backend/app/schema/billing.py†L39-L52】
- Integrations router supplies feature-flag awareness, provider install endpoints, and Prometheus counters (`integrations_requests_total`, `integrations_errors_total`) consumed by connectors. 【F:backend/app/routers/integrations.py†L1-L170】【F:backend/app/observability.py†L59-L150】

## Frontend

- Dashboard fetches analytics overview via React Query, renders KPI cards, Prometheus snapshots, and a paginated recent decisions feed with load-more handling. 【F:src/pages/Dashboard.tsx†L1-L242】
- Global layout displays store selector, session metadata, and logout controls using AuthContext. 【F:src/components/layout/AppLayout.tsx†L1-L125】
- Reports and Logs pages (not shown here) rely on `/v1/audit` and report endpoints already validated by smoke/Playwright tests. 【F:tests/e2e/reports-download.spec.ts†L1-L56】【F:backend/smoke_test.py†L1-L880】
- Settings now surfaces integration provider state (enabled/disabled/connected) by consuming `/v1/integrations/status` so operators know which connector is active. 【F:src/pages/Settings.tsx†L1-L220】
- Settings adds an operator-facing HMAC rotation control with copy-to-clipboard helper and integrates security error guidance surfaced from the backend schema. 【F:src/pages/Settings.tsx†L16-L420】【F:src/lib/api.ts†L1-L220】

## Data & Seeds

- `seed_data.py` backfills fee history for two demo stores, including absorbed vs. shown lines, reversals, and report export audits to support analytics slices. 【F:backend/seed_data.py†L72-L173】
- Rule versions for MN/CO are ensured with effective dates and parameters for deterministic fee calculations. 【F:backend/seed_data.py†L174-L212】

## Observability

- Prometheus counters and histograms exist for fee decisions, report exports, auth events, analytics dashboard loads, security failures/replays, rate-limit throttles, integration providers (`integrations_*`), and webhook ingestion (`webhooks_received_total`, `webhooks_processed_total`, `webhook_processing_latency_ms`). Docs include usage examples. 【F:backend/app/observability.py†L5-L160】【F:docs/security/observability.md†L1-L60】
- Structured logging helpers (`log_fee_event`, `log_report_event`, `log_analytics_event`, `log_security_event`) are invoked from routers/services. 【F:backend/app/observability.py†L92-L133】【F:backend/app/routers/analytics.py†L45-L68】【F:backend/app/security/hmac.py†L67-L160】
- Billing metrics (`billing_events_total`, `checkout_sessions_created_total`, `entitlement_denials_total`) capture subscription lifecycle events, upgrade attempts, and plan gating outcomes. 【F:backend/app/observability.py†L5-L140】【F:docs/certification/EVIDENCE/metrics_dump.txt†L1-L18】

## Automation & QA

- Pytest suite covers analytics responses, replay-resistant HMAC enforcement, rate limiting, fee flows, and reporting contracts. 【F:backend/tests/test_analytics_overview.py†L1-L43】【F:backend/tests/test_fee_security.py†L1-L176】【F:backend/tests/test_report_contracts.py†L1-L120】
- Smoke test exercises login, settings update, fee quote/apply, audit history, report exports, metrics endpoint, and now supports analytics-only, reports-only, and security-only modes. 【F:backend/smoke_test.py†L1-L280】
- Playwright e2e specs validate analytics dashboard rendering and report downloads (flagged via env vars), while Makefile exposes `smoke`, `reports-smoke`, and `analytics-smoke` targets. 【F:tests/e2e/analytics-dashboard.spec.ts†L1-L45】【F:tests/e2e/reports-download.spec.ts†L1-L56】【F:Makefile†L1-L160】
- Webhook smoke (`make webhooks-smoke`) signs Stripe payloads, validates DLQ/replay endpoints, and asserts new Prometheus counters appear. Postman folder **Webhooks** covers processed/invalid signature flows. 【F:backend/smoke_test.py†L800-L940】【F:docs/postman/state-tax-wizard.postman_collection.json†L1700-L1900】

## Documentation & Tooling

- API references exist for analytics, fees, and store settings, aligned with implemented endpoints. 【F:docs/api/analytics.md†L1-L80】【F:docs/api/fees.md†L1-L80】【F:docs/api/store-settings.md†L1-L120】
- UI guide documents analytics dashboard behavior, session metadata, and export flows. 【F:docs/security/ui-guide.md†L1-L80】
- Postman README/collection includes analytics/report evidence logging, automated HMAC signing, replay/stale timestamp scenarios, and a new **Integrations** folder covering status + negative install behaviour. 【F:docs/postman/README.md†L1-L160】【F:docs/postman/state-tax-wizard.postman_collection.json†L1-L200】
- WooCommerce and Shopify connectors live under `integrations/`, leverage the shared TypeScript SDK, and ship with PHPUnit/Jest suites plus packaging scripts documented for operators. 【F:integrations/woocommerce/state-tax-wizard.php†L1-L120】【F:integrations/shopify/src/server.ts†L1-L40】【F:integrations/sdk/typescript/src/index.ts†L1-L60】
- Dedicated HMAC signing guide documents headers, examples, and rotation guidance. 【F:docs/security/hmac.md†L1-L120】

## Divergences & Gaps

- Operations runbooks should call out required environment variables (`REDIS_URL`, `SMOKE_HMAC_SECRET`) and storage expectations for rotated secrets when deploying outside Docker demos. 【F:README.md†L80-L130】【F:docs/postman/README.md†L1-L140】
- Order lifecycle webhooks for Shopify/WooCommerce plus fee reversal automation remain backlog items for M8. 【F:docs/backlog/17_milestone_07_webhooks.md†L200-L360】【F:docs/backlog/18_milestone_08_launch.md†L1-L200】
- Alembic revisions `202510010001`→`202510010002` now execute the dedupe pass before recreating the unique nonce indexes; long-lived databases must run `alembic upgrade head` so the new ordering cleans duplicates before the constraint is reapplied. 【F:backend/alembic/versions/202510010001_ensure_processed_nonce_indexes.py†L1-L90】【F:backend/alembic/versions/202510010002_ensure_unique_nonce_index.py†L1-L70】

## Recommended Next Step (Milestone Alignment)

- **NEXT_SLICE: Launch Readiness (M8)** — focus on observability hardening, runbook/dashboards, and reporting parity to prepare for go-live. 【F:docs/backlog/18_milestone_08_launch.md†L1-L200】
