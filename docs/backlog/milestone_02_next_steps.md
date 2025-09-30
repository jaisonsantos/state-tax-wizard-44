## Current Stage Assessment
- Milestone 2 — Reporting Confidence is fully closed. Failure-path telemetry now records unsupported export attempts, JSON downloads advertise attachment filenames, and the `/v1/audit` endpoint filters in SQL with a dedicated Postgres expression index.
- Session persistence for Epic 02 remains stable with the new `session_tokens` migration, and smoke tests can point at explicit Prometheus hosts via `SMOKE_METRICS_URL`.
- Documentation, Postman, and frontend integrations all reflect the completed scope, so the release plan can advance to Milestone 3.

## Completion Update — Milestone 2
- `ReportService.observe_export` now logs failure outcomes for MN summary exports that request invalid formats, and the router persists matching audit rows with structured error metadata.
- JSON exports respond with `Content-Disposition` headers and the React client parses those filenames so operators download artifacts that mirror the requested date range.
- Alembic migration `202503010001_session_tokens_and_audit_index` creates the `session_tokens` table (with unique `jti` enforcement) and installs the `idx_audit_logs_store_action_ts` expression index for efficient tenant filtering.
- Smoke and Postman suites gained guards for metrics URLs, attachment headers, and 422 scenarios, ensuring CI and manual evidence cover the new telemetry surface.

## Next Iteration Goal — Milestone 3 Kickoff
Deliver the first slice of **Milestone 3 — Frontend Polish & Analytics** by wiring dashboard telemetry, extending report history usability, and tightening automation to cover the richer UI states. The detailed kickoff plan lives in [`milestone_03_frontend_polish.md`](./milestone_03_frontend_polish.md).

## Planned Changes
### Frontend
1. Add pagination and empty-state messaging to the Reports history table, aligning with backend totals.
2. Introduce dashboard cards for key Prometheus counters (fees applied/absorbed, report exports) using the authenticated API as a data source.
3. Refine the account menu to surface session details (e.g., last login, active store) leveraging the new `session_tokens` metadata.

### Backend
1. Expose lightweight analytics endpoints (or extend `/api/me`) to feed dashboard metrics without scraping Prometheus directly.
2. Enrich audit payloads with pagination cursors to support “load more” UI affordances.
3. Backfill sample data or seeds needed for dashboard visualizations and update rule fixtures where necessary.

### Tooling & Tests
- Extend Playwright coverage to capture the refreshed dashboard KPIs and report history pagination.
- Update Newman scripts to export dashboard evidence and verify the new analytics endpoints.
- Add pytest cases for the analytics endpoint payloads, including multi-store authorization checks.

### Documentation & Enablement
- Refresh `docs/ui-guide.md` with dashboard screenshots and pagination usage notes once built.
- Document the analytics endpoint contract in `docs/observability.md` and `docs/postman/README.md` so operators know where to pull metrics.
- Update iteration and release checklists to reflect Milestone 3 objectives and link to new evidence requirements.

## Cross-functional Checklist
| Area | Owner | Tasks |
| --- | --- | --- |
| Frontend | Web team | History pagination, dashboard telemetry cards, account menu session details, updated UI guide. |
| Backend | API team | Analytics endpoints, audit cursor support, data seeds, contract tests. |
| QA/Automation | QA team | Playwright/dashboard coverage, Newman analytics assertions, pagination regression tests. |
| Documentation | Tech writing | UI screenshots, observability catalog additions, checklist updates, release notes. |
| DevOps | Platform | Coordinate deployment of the new migration, monitor Prometheus dashboards for the added counters, document metrics URL overrides. |
