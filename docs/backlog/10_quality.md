# Epic 10 — Quality Engineering & Continuous Delivery

## Context
The MVP ships with backend pytest coverage and basic frontend build checks, but
lacks comprehensive automated testing, contract validation, and release
confidence tooling.

## Current Status
- ✅ GitHub Actions run backend pytest and frontend build/typecheck.
- ⚠️ No Playwright/Cypress end-to-end coverage.
- ⚠️ No contract tests for CSV/JSON reports or plugin payloads.
- ❌ No QA checklist document beyond the briefed matrices.
- ❌ No automated dependency vulnerability scanning.

## Acceptance Criteria
1. **Automated QA Checklist**: Convert the QA matrices into actionable test
   cases with status tracking (`docs/qa/checklist.md`).
2. **End-to-End Suite**: Playwright (or Cypress) tests covering login, quote,
   apply, audit view, report download, and billing page access.
3. **Contract Tests**: Snapshot/regression tests verifying CSV column headers,
   JSON schema, and webhook payloads.
4. **Dependency Scanning**: Integrate Dependabot (or Renovate) plus security
   scanners (e.g., `pip-audit`, `npm audit`) into CI with thresholds.
5. **Release Automation**: Documented release checklist plus GitHub workflow for
   tagging releases and publishing Docker images.

## Deliverables
- New tests under `backend/tests/` and `src/tests/` (or `tests/e2e/`).
- CI workflow updates adding e2e job and security scanning.
- Documentation for QA processes.

## Validation
- CI must pass with new jobs enabled.
- QA checklist reviewed and signed off prior to release.

## Definition of Done
- QA checklist lives in source control with version history and is referenced in
  each milestone’s exit criteria.
- E2E suite recorded in CI artifacts (videos/logs) and required for merge via
  status checks.
- Contract tests run as part of `make smoke` to ensure parity between manual and
  automated validation.
- Security scans configured with severity thresholds; failures block release and
  generate follow-up tickets when exceptions are needed.
- Release automation script exercised in staging, producing a tagged build whose
  artifact links are captured in the iteration exit review.
- Epic status updated with coverage metrics and open follow-ups (if any).

## Dependencies
- Depends on Epic 04 reporting output and Epic 05 frontend stability for e2e
  coverage.
