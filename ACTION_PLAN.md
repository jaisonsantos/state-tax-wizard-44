# Milestone 4 – Security Hardening Slice (Replay-Resistant HMAC)

## Delivery Snapshot
The replay-resistant HMAC slice is now merged. `/v1/fees/apply` enforces timestamp and nonce validation backed by a persistent replay store, smoke and pytest cover the failure paths, Prometheus surfaces security counters, and the developer experience is documented end-to-end (API docs, UI copy, Postman scripts, and the dedicated HMAC guide).

- ✅ Backend guardrails: constant-time signature comparison, timestamp skew enforcement, nonce TTL, metrics/logging, and Alembic migrations for `processed_nonces` plus `hmac_secret_rotated_at`.
- ✅ Frontend UX: actionable toast copy and settings help text linking to `docs/security/hmac.md`.
- ✅ Seeds/tooling: demo stores seeded with HMAC secrets, smoke runner signs requests, Postman scripts auto-populate headers.
- ✅ Documentation: observability guide includes new counters, environment doc covers configuration, backlog docs reflect shipped scope.
- ⚠️ Operational follow-up: security smoke/Newman folders require a running API backed by PostgreSQL UUID columns (see Checklist note) — recommend wiring into CI once infrastructure is available.

The sections below remain for reference when onboarding new contributors or expanding the slice (e.g., to additional routers or webhook consumers).

## Change Breakdown by Area

### Backend (FastAPI)
1. **Signature validation module**
   - Create `backend/app/security/hmac.py` with helpers to parse headers (`X-RDF-Signature`, `X-RDF-Timestamp`, `X-RDF-Nonce`) and perform constant-time comparisons.
   - Enforce an adjustable time skew window (default ±300s) via settings module; reject stale/future timestamps.
   - Surface structured exceptions with `detail.code` values (`missing_signature`, `stale_timestamp`, `replay_detected`).
   - Definition of Done (DoD): unit tests cover valid/invalid combinations, tolerant clock drift, and malformed headers; integration tests verify FastAPI responses for each failure path.

2. **Replay store**
   - Add SQLAlchemy model/table `processed_nonces` with `(nonce, store_id, expires_at)` and Alembic migration; use TTL cleanup query.
   - Introduce repository helper to insert nonce record atomically (unique constraint) and purge expired rows on each request.
   - DoD: migration applies cleanly on SQLite/Postgres; test ensures duplicate nonce raises `409` and expires after TTL.

3. **Router integration**
   - Replace `_enforce_hmac` in `fees.py` with new dependency that logs security events and increments counters before returning FastAPI responses.
   - Ensure `fee_reverse` (if HMAC required later) is extensible but out-of-scope for this slice.
   - DoD: `/v1/fees/apply` returns `401/403/409` for missing/invalid/replay cases; happy path still succeeds.

4. **Configuration**
   - Extend settings (`backend/app/core/config.py` or equivalent) with environment variables `HMAC_MAX_SKEW_SECONDS` (default 300) and `HMAC_REPLAY_TTL_SECONDS` (default 600).
   - Document fallback when values are not set; ensure smoke/tests can override via env var.
   - DoD: settings covered by unit tests; defaults appear in `docs/security/environment.md`.

5. **Logging & Metrics**
   - Add Prometheus counters: `hmac_validation_failures_total{reason,store_id}` and `hmac_replay_attempts_total{store_id}`.
   - Emit `security` logger events (`hmac_validation_failed`, `hmac_replay_detected`, `hmac_validation_succeeded`).
   - DoD: metrics exported under `/metrics`; structured logs recorded in tests via caplog.

### Frontend (React)
1. **Error handling**
   - Update API error surface (e.g., toast helpers) to detect 401/403/409 from HMAC and show actionable copy where relevant (Settings playground, fee apply flows if exposed).
   - DoD: manual/automated test ensures toast surfaces `Replay detected` or `Signature expired` message.

2. **Documentation link-outs**
   - Add contextual help in Settings page linking to new HMAC guide.
   - DoD: Verified via UI snapshot/screenshot; docs cross-link in UI guide.

### Data & Seeds
- Populate `hmac_secret` and `hmac_secret_rotated_at` for demo stores to unblock smoke/Postman tests.
- Seed sample processed nonces (optional) mainly for expiry tests.
- DoD: Running `python backend/seed_data.py` creates secrets and prints instructions on retrieving them.

### Observability
- Update `docs/security/observability.md` with new counters/log fields; include alerting recommendation (failure ratio, replay spikes).
- DoD: Document references match metric names; example payloads include `event=\"hmac_validation_failed\"`.

### Automation & QA
1. **Pytest**
   - Expand `test_fee_security.py` for timestamp/nonce success and failure, replay detection, and TTL expiry.
   - Add fixture for overriding skew/TTL to keep tests fast.
   - DoD: tests pass under `pytest -q`.

2. **Smoke test**
   - Update `backend/smoke_test.py` to sign `apply` payloads with timestamp/nonce using secrets from settings endpoint (or env var) and assert replay rejection when reusing nonce.
   - Add CLI options `--security-only` or reuse existing flags; new Make target `security-smoke` should call smoke with `--security-only`.
   - DoD: command exits 0 when security checks pass, non-zero with informative message otherwise.

3. **Postman/Newman**
   - Add pre-request script for fee apply that injects timestamp/nonce/signature; include negative test folder for stale timestamp/replay (skipped by default using collection variables).
   - Document `evidence_dir` outputs for security runs.
   - DoD: Collection runs locally with new scripts; README updated.

4. **Playwright**
   - Optional: add integration scenario behind flag verifying Settings displays HMAC details (can be deferred if UI change minimal).

### Documentation
- Refresh `docs/backlog/milestone_04_security.md` intro/status to acknowledge existing HMAC hook and clarify new goals (timestamp/nonce, replay store, metrics).
- Create `docs/security/hmac.md` describing header contract, sample signing code (JS/Python), rotation steps, and troubleshooting.
- Update `docs/security/ui-guide.md` session/security sections if UI surfaces HMAC status.
- DoD: Docs merged with references from PR description; links validated via `markdownlint`/manual check.

### Makefile & CI
- Add `security-smoke` target invoking `python smoke_test.py --security-only` (after updating script).
- Ensure CI instructions mention when to run (README/testing section + PR template if applicable).
- DoD: `make security-smoke` runnable locally after `make up migrate seed`.

## Definition of Done Summary
- All new counters/logs observable via `/metrics` and structured logs.
- Pytest, smoke (`--security-only`), and Newman security folder succeed locally.
- Docs/Postman/README reflect timestamp/nonce requirements.
- Seeds provide secrets for demos/tests; rotation steps documented.
- PR includes evidence snippets: pytest output, smoke command, Newman run.

## Risks & Mitigations
- **Time skew false positives**: Provide configurable skew and document syncing clocks (mention `ntpd` guidance) to reduce support load.
- **Nonce table growth**: Implement TTL cleanup per request and document periodic job/cron for production; consider asynchronous cleanup follow-up.
- **Secret exposure in logs**: Ensure logging avoids printing raw signatures/secrets; audit log statements before merge.
- **CI determinism**: Tests relying on wall clock must freeze time (use `freezegun` or manual patching) to prevent flakes.

## Validation Strategy
- `pytest backend/tests/test_fee_security.py -q`
- `python backend/smoke_test.py --security-only`
- `newman run docs/postman/state-tax-wizard.postman_collection.json --folder "Security" --env-var base_url=...`
- Frontend `npm run typecheck` if UI copy changes.
