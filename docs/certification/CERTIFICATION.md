# Milestone Certification — Audit Through M4 (Security Slice)

## Summary

- Pytest suite (including new rate-limiter and rotation coverage) passes locally, confirming analytics, fee flows, HMAC edge cases, and regression guards. 【F:backend/tests/test_fee_security.py†L1-L340】【F:backend/tests/test_rate_limiter.py†L1-L40】
- Distributed rate limiting, secret rotation UX/API, and timezone-aware logging are implemented and validated by smoke tests and Prometheus counters, closing the remaining M4 follow-ups. 【F:backend/app/security/rate_limit.py†L1-L146】【F:backend/app/routers/store_settings.py†L1-L155】【F:backend/smoke_test.py†L1-L360】
- Documentation, Postman, and Makefile targets were refreshed to reflect the new workflows and CI automation. 【F:docs/security/hmac.md†L1-L120】【F:docs/postman/state-tax-wizard.postman_collection.json†L470-L540】【F:Makefile†L1-L110】

> Consulte o [STATUS.md](../../STATUS.md) e os dossiês de milestones ([Milestone 2](../backlog/12_milestone_02_next_steps.md), [Milestone 3](../backlog/13_milestone_03_frontend_polish.md), [Milestone 4](../backlog/14_milestone_04_security.md)) para contexto expandido.

## Milestone Outcomes

### Milestone 2 – Auth & Tenant **(Pass)**

- `/api/auth/login` provisions demo stores, persists session tokens with revocation metadata, and emits structured auth logs; `/api/auth/logout` revokes tokens idempotently. 【F:backend/app/routers/auth.py†L18-L169】
- `get_auth_context` validates bearer tokens against persisted sessions and `assert_store_access` enforces tenant-specific access, which the fee routers invoke ahead of every quote/apply request. 【F:backend/app/core/deps.py†L28-L140】【F:backend/app/routers/fees.py†L40-L214】
- Automated tests confirm unauthorized requests are rejected and that linked stores can quote/apply fees successfully. 【F:backend/tests/test_authz_scope.py†L20-L83】
- `STATUS.md` and the roadmap both describe Milestone 5 (Billing/Stripe) as the recommended next focus following completion of the security slice. 【F:STATUS.md†L1-L105】【F:README.md†L126-L133】

### Milestone 3 – Frontend & Analytics **(Pass)**

- `/v1/analytics/overview` assembles Prometheus counter snapshots, KPI cards, and a cursor-driven recent decisions feed, incrementing structured analytics logs. 【F:backend/app/routers/analytics.py†L6-L80】【F:backend/app/services/analytics_service.py†L31-L299】【F:backend/app/observability.py†L10-L95】
- Dashboard UI renders cards, Prometheus snapshots, and paginated audit feeds with React Query error handling and actionable quick links. 【F:src/pages/Dashboard.tsx†L1-L242】
- Reports UI supports MN CSV/JSON and CO CSV downloads, honors backend filenames, and paginates `/v1/audit?action=report_export` history with cursor-based loading. 【F:src/pages/Reports.tsx†L35-L240】
- Settings now exposes rotation tooling alongside HMAC guidance, matching the backend schema. 【F:src/pages/Settings.tsx†L16-L420】
- Tests cover analytics responses and report contracts to ensure frontend consumers stay in sync. 【F:backend/tests/test_analytics_overview.py†L19-L50】【F:backend/tests/test_report_contracts.py†L29-L135】
- Documentation and Postman guides continue to describe analytics/reporting evidence capture and execution order. 【F:docs/security/ui-guide.md†L3-L25】【F:docs/postman/README.md†L5-L62】

### Milestone 4 – Security (HMAC, Rate Limiting) **(Closed)**

- HMAC enforcement validates `X-RDF-Timestamp` (ISO/epoch), `X-RDF-Nonce`, and `X-RDF-Signature`, persists nonces only after signature verification, emits low-cardinality metrics, and logs nonce previews without leaking secrets. 【F:backend/app/security/hmac.py†L20-L168】【F:backend/app/observability.py†L10-L95】
- The rate limiter now uses Redis (with Lua-backed sliding windows), raises structured 429s, emits `rate_limit_throttles_total`, and has unit tests covering both memory and Redis paths. 【F:backend/app/security/rate_limit.py†L1-L146】【F:backend/tests/test_rate_limiter.py†L1-L40】
- `POST /v1/stores/{id}/hmac/rotate` generates and audits new secrets; the Settings UI surfaces a copy-once pane and updates rotation timestamps. 【F:backend/app/routers/store_settings.py†L1-L155】【F:src/pages/Settings.tsx†L16-L420】
- Security smoke exercises apply/replay/stale flows, forces rate-limit throttling, validates counter increments, and confirms rotated secrets invalidate previous signatures. 【F:backend/smoke_test.py†L210-L360】
- Alembic guardian migration enforces the processed nonce indexes across environments and downgrades cleanly. 【F:backend/alembic/versions/20251001_ensure_unique_nonce_index.py†L1-L40】
- HMAC guide and observability catalog document the rotation endpoint, Redis rate limits, and new Prometheus counters to avoid drift. 【F:docs/security/hmac.md†L1-L120】【F:docs/security/observability.md†L1-L160】

## Outstanding Follow-ups Before M5

- Extend ops/runbook docs with guidance on supplying `REDIS_URL`, secure secret storage, and billing environment variables ahead of the next slice. 【F:README.md†L80-L133】【F:docs/postman/README.md†L1-L140】
