# Milestone 3 — Frontend Polish & Analytics

_[← Milestone 2 — Next Steps](12_milestone_02_next_steps.md) • [Milestone 4 — Security →](14_milestone_04_security.md)_

## Stage Validation Summary

- **Reporting confidence shipped**: `ReportService.observe_export` captures success
  and failure telemetry and persists audit rows for each export
  ([`backend/app/services/report_service.py`](../../backend/app/services/report_service.py)).
- **Frontend export UX is live**: the Reports page hydrates history from
  `/v1/audit`, renders loading skeletons, and surfaces toast notifications for
  success/failure states ([`src/pages/Reports.tsx`](../../src/pages/Reports.tsx)).
- **Logs view wired to API**: `/v1/audit` data powers filtering, CSV export, and
  refresh states in the Logs page ([`src/pages/Logs.tsx`](../../src/pages/Logs.tsx)).
- **Operator guidance updated**: the UI guide documents export behavior and
  account logout flows ([`docs/security/ui-guide.md`](../security/ui-guide.md)).
- **Automation hook in place**: `make reports-smoke` exercises the export flow in
  CI/local pipelines ([`Makefile`](../../Makefile)).
- **Remaining gap**: Future iterations can add trend visualizations and alerts,
  but the initial KPI, analytics, and session metadata slices are now live in the
  dashboard and header.

## Status Update

Milestone 3 core scope shipped: the dashboard now consumes live analytics
telemetry, account/session metadata renders in the header, and automation covers
analytics smoke flows. The notes below capture the historical plan and can be
used for future enhancements (trend visualisations, alerting, etc.).

## Remaining Enhancements

Future iterations can build on this foundation by layering trend
visualisations, alerting, or deeper analytics exploration. The historical plan
is retained below as guidance when prioritising follow-up work.

## Historical Implementation Notes

### 1. Backend Analytics Surface

- Introduce `/v1/analytics/overview` router that aggregates fee counts, absorbed
  totals, and recent audit activity per store by querying `OrderFee` and
  `AuditLog` data and snapshotting Prometheus counters for exports.
- Extend `backend/app/schema` models with typed responses (e.g.
  `AnalyticsOverviewResponse`) and back them with repository helpers in
  `backend/app/services/analytics_service.py`.
- Add pagination cursor support to `AuditLogRepository` so the Reports history
  can request subsequent pages without re-querying from offset zero.
- Wire Prometheus counter snapshots (fees applied/absorbed, report exports) via
  dependency injection to avoid scraping `/metrics` directly.

### 2. Frontend Dashboard & Session Polish

- Replace the hard-coded KPI array in `src/pages/Dashboard.tsx` with data fetched
  from the new analytics endpoint (using React Query hooks inside
  `src/lib/api.ts`).
- Render trendlines, deltas, and loading/empty/error states for KPI cards and the
  “Recent Fee Decisions” list, using audit cursor metadata to drive pagination.
- Enrich the account dropdown with the active session identifier, issued-at,
  last-activity timestamp, and store scope drawn from `GET /api/me` (extended to
  include session metadata).
- Add contextual helper text/tooltips linking to observability dashboards and the
  updated docs.

### 3. Data & Seeding

- Update `backend/seed_data.py` so demo stores include enough fee/audit history
  for dashboard visualizations (e.g., multiple days of activity, absorbed vs
  shown counts).
- Ensure seeds create representative `report_export` audit rows to populate the
  history pagination.

### 4. Observability & Metrics

- Expand `docs/security/observability.md` with the analytics payload contract and the
  Prometheus counters that back each dashboard widget.
- Emit structured logs (`analytics_dashboard_loaded`) whenever the frontend
  queries the analytics endpoint to support troubleshooting.
- Consider adding histogram buckets for dashboard response times if latency is a
  concern.

### 5. Automation & QA

- Add backend pytest coverage for the analytics service (per-store filtering,
  cursor behavior, Prometheus counter snapshots, authorization failures).
- Extend Playwright to capture dashboard load, KPI refresh, and history
  pagination (enable via `ENABLE_REPORT_DOWNLOAD_TEST=1` until always-on).
- Update the Newman collection with the analytics endpoint (request + schema
  assertions) and export evidence paths for the new responses.
- Refresh `tests/smoke_test.py` (invoked by `make reports-smoke`) or add a new
  `make analytics-smoke` target that calls the analytics API and validates JSON
  structure, wiring it into CI once stable.

### 6. Documentation & Enablement

- Document dashboard usage patterns and session metadata in `docs/security/ui-guide.md`
  with fresh screenshots (capture via the frontend once the feature ships).
- Add API contract details to `docs/api` (e.g., new `analytics.md`) describing
  request/response fields, auth requirements, and pagination semantics.
- Update `README.md` roadmap/status to point to this milestone document and note
  the availability of analytics telemetry.
- Revise `docs/backlog/11_iteration_checklist.md` to include evidence expectations
  for analytics UI/endpoint changes.

### 7. Operations & Rollout

- Provide a short operations runbook entry (`docs/security/environment.md`) describing
  feature flags (if any), environment variables required for analytics, and how
  to backfill historical counters.
- Confirm migrations (if needed for aggregates) are idempotent and documented in
  release notes.

## Deliverable Checklist

| Area | Tasks | Owners |
| --- | --- | --- |
| Backend | Analytics router/service, schema validation, pagination cursors, Prometheus snapshots | API team |
| Frontend | Dashboard data hooks, KPI/recents UI states, account session details, toast/tooltip polish | Web team |
| Data & Seeds | Backfill analytics fixtures and audit rows | Platform |
| Automation | Pytest + Playwright + Newman updates, new smoke target | QA team |
| Documentation | UI guide screenshots, observability catalog, API docs, roadmap update | Tech writing |
| Operations | Runbook updates, deployment steps, monitoring alerts | DevOps |

## Exit Criteria Checklist

- [x] `/v1/analytics/overview` documented, tested, and guarded by tenant auth.
- [x] Dashboard renders live data with explicit loading, empty, and error states.
- [x] Account dropdown surfaces session metadata sourced from `session_tokens`.
- [x] Seeds + fixtures provide deterministic analytics data for local/CI runs.
- [x] Playwright + Newman scripts archive evidence for analytics responses.
- [x] Docs (`README`, `docs/security/ui-guide.md`, `docs/security/observability.md`, Postman guide)
  reference the new analytics surface.
- [x] Makefile (or equivalent automation) exposes a repeatable analytics smoke
  test consumed by CI.

Document completion of each checklist item in the PR description for the slice
that implements it so auditors can trace evidence quickly.
