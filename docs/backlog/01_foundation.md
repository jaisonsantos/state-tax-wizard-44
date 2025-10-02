# Epic 01 — Platform Foundations & Observability

## Context

The MVP requires a stable foundation: reproducible environments, seeded data,
and baseline observability (health, metrics, structured logs). This epic groups
the work needed to guarantee developers and operators can reliably run the
stack and inspect system health.

## Current Status

- ✅ Docker Compose definitions for API, frontend, and Postgres.
- ✅ Alembic migrations + deterministic `seed_data.py` covering demo stores,
  users, rules, and subscriptions.
- ✅ `/healthz` and `/metrics` endpoints with Prometheus counters/histograms.
- ✅ Structured logging helper in `observability.py`.
- ✅ Consolidated environment, data model, and observability documentation under
  `docs/`.
- ✅ `make smoke` runbook and automation validating login, quote, apply, audit,
  and report flows.

## Acceptance Criteria

1. **Environment Guide**: `docs/security/environment.md` (or equivalent) explains how to
   bootstrap dev and CI environments, including environment variables,
   migrations, and seed expectations.
2. **Data Contract Reference**: Logical model diagram/table referencing all
   Alembic tables, key columns, and relationships (can reuse section 3 of the
   provided brief but formalized into a document).
3. **Observability Catalog**: Document describing each Prometheus metric and
   log event schema, including sample payloads and when they fire.
4. **Operational Checklists**: Step-by-step runbooks for `make dev`, `make
   migrate`, `make seed`, and smoke tests.
5. **Validation Automation**: Add a `make smoke` target (or shell script)
   exercising login, quote, apply, audit, and reports to prove the environment
   works end-to-end using seeded data.

## Deliverables

- `docs/security/environment.md`
- `docs/security/data-model.md`
- `docs/security/observability.md`
- Updated `Makefile` targets and documentation references.

## Validation

- Run `make smoke` successfully against a fresh database.
- Link to documentation reviewed/approved by stakeholders.

## Definition of Done

- `docs/security/environment.md`, `docs/security/data-model.md`, and `docs/security/observability.md`
  checked into source control with diagrams or tables as applicable.
- `make smoke` target (and CI equivalent) executes end-to-end without manual
  setup, producing logs stored with the PR or release notes.
- Observability catalog updated to describe any new metrics/log schemas added
  while implementing the epic.
- Epic status and release plan milestone updated to reflect completion and link
  to validation evidence.

## Dependencies

- None; this epic underpins all others and should be executed first.
