# Milestone 4 – Security Hardening Checklist

## Planning & Alignment
- [x] Update `docs/backlog/milestone_04_security.md` status section to reflect existing HMAC support and outline replay/timestamp scope.
- [x] Publish `docs/security/hmac.md` with header contract, signing examples, rotation steps, and troubleshooting tips.

## Backend Implementation
- [x] Add Alembic migration for `processed_nonces` table (nonce, store_id, processed_at, expires_at) with unique constraint.
- [x] Implement security module to validate signature, timestamp skew, and nonce uniqueness; integrate with `/v1/fees/apply`.
- [x] Persist nonce usage and purge expired entries per request.
- [x] Emit Prometheus counters (`hmac_validation_failures_total`, `hmac_replay_attempts_total`) and structured security logs.
- [x] Document new config (`HMAC_MAX_SKEW_SECONDS`, `HMAC_REPLAY_TTL_SECONDS`) in `docs/security/environment.md`.

## Frontend & UX
- [x] Surface actionable error messages for 401/403/409 HMAC failures in fee flows and settings playground.
- [x] Add help text or link in Settings page pointing to HMAC guide.
- [ ] Capture updated UI screenshot for docs (if visual changes) and attach to PR evidence.

## Data & Seeds
- [x] Ensure seed stores include `hmac_secret` and `hmac_secret_rotated_at` values for demos/tests.
- [ ] Optionally seed expiring nonces for integration tests.

## Observability
- [x] Update `docs/security/observability.md` with new counters and security log schemas.
- [ ] Verify `/metrics` exposes the new counters after a signed request.

## Automation & Tests
- [x] Extend `backend/tests/test_fee_security.py` to cover timestamp skew, nonce replay, and success cases.
- [x] Update `backend/smoke_test.py` with `--security-only` flow that signs requests and asserts replay rejection.
- [x] Add Makefile target `security-smoke` invoking the new smoke flag.
- [x] Update Postman collection with pre-request script for timestamp/nonce and negative test folder; document execution in `docs/postman/README.md`.
- [ ] Run Newman security folder locally and capture evidence path.
- [ ] Ensure Playwright/other e2e remain green (or document skip rationale).

## Validation Gates
- [x] `pytest backend/tests -q`
- [ ] `python backend/smoke_test.py --security-only`
- [ ] `newman run docs/postman/state-tax-wizard.postman_collection.json --folder "Security" --env-var base_url=...`
- [x] `npm run typecheck` (if frontend strings change)
- [ ] Confirm `/metrics` snapshot includes new counters with non-zero values after smoke test.

## Documentation & PR Hygiene
- [x] Update `README.md` testing section with `make security-smoke` guidance.
- [x] Link new docs from UI guide / API docs where relevant.
- [ ] Include test command outputs and metric evidence in PR description.
- [ ] Note any follow-up tasks (e.g., distributed rate limiting) in PR follow-ups section.

> _Smoke and Newman runs require a running backend with PostgreSQL UUID support. Locally this can be achieved via `docker-compose up -d postgres` followed by `alembic upgrade head` and `python backend/seed_data.py` before executing the commands above._
