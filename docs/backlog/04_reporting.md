# Epic 04 — Reporting & Compliance Exports

## Context
Compliance for MN and CO hinges on accurate CSV/JSON exports. While endpoints
exist, gaps remain in JSON output, validations, and documentation for auditors.

## Current Status
- ✅ `/api/v1/reports/co/dr1786` returns CSV aggregations.
- ✅ `/api/v1/reports/mn/summary` returns CSV.
- ✅ MN JSON format now returns structured output with parity checks captured in [`backend/tests/test_mn_report_json.py`](../../backend/tests/test_mn_report_json.py) and aligned to the documented schema in [`docs/reports/mn_summary.md`](../reports/mn_summary.md).
- ✅ CSV/JSON contract coverage is enforced via [`backend/tests/test_report_contracts.py`](../../backend/tests/test_report_contracts.py), which exercises the published schema references in [`docs/reports/mn_summary.md`](../reports/mn_summary.md).
- ✅ Frontend downloads now wire the export history table to live `/v1/audit` data, drop unsupported XLSX options, and surface inline loading/error states alongside toast notifications. A Playwright smoke test triggers CSV and JSON downloads when enabled.
- ✅ Audit trail coverage: every export persists a `report_export` audit row, emits a structured log via `observability.log_report_event`, and increments the `report_exports_total{jurisdiction,format}` counter. Invalid formats return a `422` with validation-style details.
- ✅ Invalid-format attempts now emit failure telemetry/audit rows, and JSON downloads ship with `Content-Disposition` filenames so browsers store them consistently.

## Acceptance Criteria
1. **JSON Output**: `/reports/mn/summary?format=json` returns structured JSON
   matching documented schema (counts, totals, absorbed metrics).
2. **Schema Documentation**: Publish CSV column dictionaries and JSON schema
   under `docs/reports/` for MN and CO.
3. **Contract Tests**: Backend tests verify CSV headers and sample data; JSON
   responses validated against Pydantic models.
4. **Frontend UX**: Reports page surfaces last export timestamp and exposes both
   CSV and JSON download buttons with error handling.
5. **Auditability**: Audit log entry created when a report is generated,
   capturing user and filters.

## Deliverables
- Backend schema updates in `schemas/reports.py`.
- Documentation: [`docs/reports/mn_summary.md`](../reports/mn_summary.md),
  [`docs/reports/co_dr1786.md`](../reports/co_dr1786.md).
- Playwright (or Vitest) test to ensure download button triggers API call.

## Validation
- Automated tests run in CI verifying CSV and JSON outputs.
- Manual verification using QA matrix sample dates.

## Definition of Done
- CSV/JSON schemas versioned in `docs/reports/` with examples generated from the
  seeded database and linked from release notes.
- Contract tests fail if headers or JSON keys regress; CI pipeline blocks merge
  on mismatch.
- Audit logs confirmed to include report requests with filters/user info, and
  observability catalog updated if new metrics added.
- Frontend download flow captured in automated UI test evidence (video or
  screenshot) stored with iteration exit artifacts.
- Epic status updated, citing the test fixtures used for validation.

## Dependencies
- Depends on Epic 02 for authenticated audit trail and user attribution.
