# Incremental Delivery Checklist & Definition of Done

This guide standardizes how increments from the Retail Delivery Fee backlog are
planned, implemented, and accepted. Use it alongside each epic to ensure we
ship vertical slices that exercise real integrations (not mocks) and keep
documentation in sync with the repository.

## Delivery Principles

1. **Vertical slices first** – Every iteration should connect UI, API, data, and
docs for at least one merchant scenario (e.g., MN quote + apply).
2. **Real systems over placeholders** – Prefer wiring to the production-ready
API. Temporary mocks must be feature-flagged, documented, and carry a tracked
follow-up task before merging.
3. **Observability baked in** – Metrics, logs, and traces are part of the story.
Expose them as you build the feature, and update the observability catalog.
4. **Backlog as source of truth** – Update the corresponding epic’s *Current
Status* when scope ships so future audits reflect reality.
5. **Documentation parity** – Any new behavior must be described in operator,
QA, or integration docs in the same commit.

## Definition of Done Template

A backlog item is “done” only if all points below are satisfied:

- **Code**: Feature implemented end-to-end, feature flags defaulted to the
  production path. Dead code and TODOs resolved or tracked.
- **Tests**: Automated coverage (unit/integration/e2e as appropriate) added and
  passing in CI. Include regression tests for bugs fixed and capture Postman/Newman
  evidence per [`docs/postman/README.md`](../postman/README.md).
- **Documentation**: Relevant sections updated (`docs/`, API reference, README,
  release notes). Inline code comments explain non-obvious logic.
- **Observability**: Metrics/logs updated, alert thresholds reviewed when
  applicable. New metrics added to `docs/security/observability.md`.
- **Analytics Evidence**: Dashboard or analytics stories must attach `/v1/analytics/overview`
  payload samples (Postman/Newman output) so KPI calculations and cursors can be
  audited alongside UI changes.
- **Validation**: `make smoke` (or epic-specific script such as `make reports-smoke`)
  runs clean against a
  fresh seed database and captures test evidence in the PR description.
- **Security & Compliance**: Secrets handled via env vars, authz enforced,
  PII redacted from logs, rate limits or HMAC in place where required.
- **Session Management**: Login/logout flows persist sessions server-side,
  revoke tokens when sign-out occurs, and automated coverage proves the
  dependency rejects revoked tokens.
- **Backlog Sync**: Epic document updated with current status ✅/⚠️/❌, release
  plan milestone annotated if scope moved.
- **Rollout**: Feature toggles, migration steps, and rollback plans documented
  (if applicable) to unblock operations.

## Iteration Planning Checklist

Before starting an iteration:

- [ ] Identify target acceptance criteria from the epic and map to tasks.
- [ ] Confirm required backend/frontend touchpoints and test data.
- [ ] Document success metrics or dashboards that will prove the feature works.
- [ ] Align with QA on scenarios drawn from `docs/backlog/10_quality.md`.

## Exit Review Checklist

Use this after each iteration demo:

- [ ] Demo recorded or notes attached to the PR/epic.
- [ ] Observability dashboards/screenshots captured for verification.
- [ ] Backlog doc updated (status + links to PRs/tests).
- [ ] `make smoke` output archived in CI artifact.
- [ ] Follow-up items (if any) logged with owners and due dates.

## Mock Usage Policy

- Only permitted when a third-party dependency (e.g., Stripe) is unavailable in
the current environment.
- Must be scoped behind a feature flag defaulting to the real path in staging
  and production.
- Requires a ticket referencing the mock with a due date for removal.
- Document the rationale and removal plan in the epic under *Current Status*.

Adhering to this checklist ensures each delivery remains incremental, traceable,
and production-ready.
