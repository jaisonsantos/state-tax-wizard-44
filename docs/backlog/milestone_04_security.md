# Milestone 4 — Security & Rate Limiting

## Stage Validation Summary
- **Auth foundation ready**: JWT-based authentication with session tokens persisted in `session_tokens` table, logout revokes active sessions ([`backend/app/routers/auth.py`](../../backend/app/routers/auth.py)).
- **Store scoping enforced**: All fee endpoints validate store ownership via `AuthService.validate_store_access` ([`backend/app/core/security.py`](../../backend/app/core/security.py)).
- **Observability in place**: Prometheus counters and structured logs capture fee operations and auth events ([`backend/app/observability.py`](../../backend/app/observability.py)).
- **Security slice delivered**: `/v1/fees/apply` now enforces timestamp/nonce validation, persists processed nonces, surfaces structured security logs, and exports Prometheus counters for failures/replays.
- **Secrets centralised**: Store-specific signing keys live in `store_settings.hmac_secret` with rotation timestamps managed in the same table, keeping credentials out of the legacy `stores` record.
- **Remaining gap**: Per-store rate limiting still relies on the in-memory limiter and secrets rotation SOP tooling is pending.

## Next Development Objective
Deliver **Security Hardening** by implementing HMAC signatures for webhook/plugin requests, per-store rate limiting, replay protection, and comprehensive security logging to prepare the platform for production traffic.

## Implementation Plan

### 1. HMAC Signature Verification
- Extend existing `store_settings.hmac_secret` support with a `hmac_secret_rotated_at` timestamp so rotations are auditable.
- Generate secrets during onboarding/settings update when absent and expose rotation endpoint/flow if required.
- Create `backend/app/security/hmac.py` helpers that:
  - Read `X-RDF-Signature`, `X-RDF-Timestamp`, and `X-RDF-Nonce` headers from incoming requests.
  - Validate signature against the raw request body using the store's `hmac_secret`.
  - Enforce ±5 minute timestamp tolerance (configurable) and reject stale/future requests.
- Wire the helper into `/v1/fees/apply` (and future webhook endpoints) ahead of broader middleware adoption.
- Document signature generation algorithm in `docs/security/hmac.md` with code examples for WooCommerce/Shopify integrations.

### 2. Replay Protection
- Store processed nonces in a PostgreSQL `processed_nonces` table with a 10 minute TTL (SQLite-compatible for tests).
- Validation checks nonce uniqueness before processing request and purges expired rows opportunistically.
- Return `409 Conflict` for replayed requests with clear error message.
- Add Prometheus counter `hmac_replay_attempts_total` with labels for store and endpoint.

### 3. Rate Limiting Infrastructure
- Replace the existing in-memory limiter with a distributed solution (e.g., `slowapi` or `fastapi-limiter`).
- Configure Redis backend for shared quotas across API instances and document local fallbacks.
- Implement `RateLimitMiddleware` in `backend/app/security/rate_limit.py`:
  - Per-store limits: 120 requests/minute for `/v1/fees/*` endpoints.
  - Global limits: 1000 requests/minute for authenticated endpoints, 100/minute for public endpoints.
  - Return `429 Too Many Requests` with `Retry-After` and `X-RateLimit-*` headers.
- Add Prometheus counter `rate_limit_exceeded_total` by store, endpoint, and limit type.

### 4. Security Logging & Monitoring
- Extend structured logging to capture security events:
  - `hmac_validation_failed`: Invalid signature, expired timestamp, replayed nonce.
  - `rate_limit_exceeded`: Store ID, endpoint, current limit, window.
  - `auth_token_revoked`: Session logout events.
  - `suspicious_activity`: Multiple failed auth attempts, unusual access patterns.
- Create Prometheus alerts:
  - `HighHMACFailureRate`: >10% of requests failing HMAC validation in 5-minute window.
  - `RateLimitAbusePattern`: Single store hitting rate limits >5 times in 10 minutes.
  - `TokenReuseAttempts`: Revoked tokens being reused.
- Integrate with observability dashboard (Grafana/Prometheus) per `docs/observability.md`.

### 5. Secrets Management Documentation
- Create `docs/security/secrets.md` covering:
  - **JWT Secret**: Rotation procedure (generate new secret, support dual validation period, phase out old secret).
  - **HMAC Secrets**: Per-store generation via secure random, storage encrypted at rest, rotation triggers regeneration and notification to integration.
  - **Stripe Keys**: Test vs production mode separation, webhook secret verification.
  - **Environment Variables**: Document all required secrets, recommended tools (AWS Secrets Manager, HashiCorp Vault, Kubernetes Secrets).
- Add rotation SOP (Standard Operating Procedure) with step-by-step commands and rollback plan.
- Include sample rotation exercise log for audit trail.

### 6. Database Migration
- Create Alembic migration `backend/alembic/versions/202504010001_security_hardening.py`:
  - Add `store_settings.hmac_secret_rotated_at` (timestamp with time zone, nullable) while keeping existing `hmac_secret`.
  - Ensure historical rows populate `hmac_secret_rotated_at` with `now()` when a secret exists.
  - Create table `processed_nonces`:
    ```sql
    CREATE TABLE processed_nonces (
      nonce VARCHAR(128) PRIMARY KEY,
      store_id UUID NOT NULL REFERENCES stores(id),
      processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
      expires_at TIMESTAMP WITH TIME ZONE NOT NULL
    );
    CREATE INDEX idx_processed_nonces_expires ON processed_nonces(expires_at);
    ```
  - Add periodic cleanup job for expired nonces (via cron or background task).

### 7. Integration SDK Updates
- Update `backend/app/schema/store_settings.py` to include `hmac_enabled` boolean flag.
- Create client library helpers (TypeScript/Python) for integrations:
  - `generateHMACSignature(secret, payload, timestamp, nonce)`: Produces signature string.
  - `validateHMACResponse(response)`: Checks API response signatures.
- Provide sample code snippets in `docs/integrations/hmac-client-examples.md`.

### 8. Automated Testing
- Add pytest fixtures for HMAC-signed requests in `backend/tests/conftest.py`.
- Create `backend/tests/test_hmac_security.py`:
  - Valid signature acceptance.
  - Invalid signature rejection (wrong secret, tampered body, expired timestamp).
  - Replay attack prevention (duplicate nonce).
  - Edge cases (missing headers, malformed signature).
- Create `backend/tests/test_rate_limiting.py`:
  - Successful requests within limit.
  - 429 response when exceeding limit.
  - Per-store isolation (one store's limit doesn't affect another).
  - Header validation (`X-RateLimit-Remaining`, `Retry-After`).
- Add load test using `locust` or `k6` to verify rate limiting under concurrent load.

### 9. Frontend Security Enhancements
- Update `src/lib/api.ts` to handle 429 responses with user-friendly toast messages.
- Add retry logic with exponential backoff for rate-limited requests (optional, document in settings).
- Display security status in Settings page:
  - HMAC enabled/disabled toggle.
  - Last secret rotation timestamp.
  - Button to regenerate HMAC secret (with confirmation dialog).

### 10. Operations Runbook
- Extend `docs/environment.md` with security configuration:
  - Required environment variables: `REDIS_URL`, `JWT_SECRET`, `HMAC_ALGORITHM` (default HS256).
  - Feature flags: `ENABLE_HMAC_VERIFICATION`, `ENABLE_RATE_LIMITING` (default true in production).
- Create `docs/security/incident-response.md`:
  - Playbook for compromised HMAC secret (immediate rotation, audit log review, notification to affected stores).
  - Rate limit abuse response (temporary ban, investigate store activity, contact merchant).
  - Token compromise (revoke all sessions for user, force password reset).

## Deliverable Checklist

| Area | Tasks | Owners |
| --- | --- | --- |
| Backend | HMAC middleware, rate limiting, nonce tracking, secrets generation | Security team |
| Database | Schema migration for HMAC secrets and nonces | Platform team |
| Testing | Pytest coverage for HMAC/rate limiting, load tests | QA team |
| Documentation | HMAC guide, secrets management SOP, incident response playbook | Tech writing |
| Frontend | 429 handling, security settings UI | Web team |
| Observability | Security event logging, Prometheus counters/alerts, dashboards | DevOps team |
| Integration SDK | Client libraries with HMAC helpers, sample code | Integration team |

## Exit Criteria Checklist
- [ ] HMAC middleware deployed and enforced on `/v1/fees/*` endpoints with feature flag.
- [ ] Rate limiting active with per-store quotas, 429 responses include proper headers.
- [ ] Replay protection prevents duplicate nonce processing (Redis or DB-backed).
- [ ] Security events logged with structured context and exposed via Prometheus.
- [ ] `docs/security/` directory contains HMAC guide, secrets SOP, and incident response playbook.
- [ ] Database migration tested in staging with rollback procedure validated.
- [ ] Automated tests cover HMAC validation (acceptance/rejection), rate limiting thresholds, and edge cases.
- [ ] Load test demonstrates rate limiting under 10x normal traffic without false positives.
- [ ] Settings page allows store admins to view/rotate HMAC secrets.
- [ ] Integration SDK updated with HMAC client examples and published to docs.
- [ ] Security audit log reviewed for PII leakage, all sensitive data redacted.
- [ ] Postman collection includes HMAC-signed requests for manual testing.
- [ ] CI pipeline runs security tests and fails on violations.
- [ ] Secrets rotation drill performed in staging and documented with screenshots.

## Security Validation Scenarios
1. **HMAC Success**: Valid signature with correct timestamp/nonce → 200 OK.
2. **HMAC Failure - Invalid Signature**: Tampered body or wrong secret → 401 Unauthorized.
3. **HMAC Failure - Expired Timestamp**: Request older than 5 minutes → 401 Unauthorized.
4. **HMAC Failure - Replayed Nonce**: Duplicate nonce within 10-minute window → 409 Conflict.
5. **Rate Limit - Within Quota**: 119 requests in 1 minute → All succeed.
6. **Rate Limit - Exceeded**: 121st request in 1 minute → 429 Too Many Requests.
7. **Rate Limit - Different Stores**: Store A hitting limit doesn't block Store B.
8. **Secret Rotation**: Old secret rejected after rotation grace period (5 minutes).

## Rollout Plan
1. **Week 7 Day 1-2**: HMAC middleware implementation and unit tests.
2. **Week 7 Day 3-4**: Rate limiting infrastructure and Redis integration.
3. **Week 7 Day 5**: Database migration and security logging.
4. **Week 8 Day 1-2**: Frontend security settings, integration SDK updates.
5. **Week 8 Day 3**: Load testing and Prometheus alert configuration.
6. **Week 8 Day 4**: Documentation completion and security audit.
7. **Week 8 Day 5**: Staging deployment and rotation drill.

## Dependencies
- Requires Milestone 3 completion (analytics and session management stable).
- Redis instance for rate limiting and nonce storage (or PostgreSQL fallback).
- Access to staging environment for security testing and rotation exercises.

## Success Metrics
- **HMAC Validation**: >99.9% of legitimate requests succeed, 100% of tampered requests rejected.
- **Rate Limiting**: Zero false positives (legitimate traffic under quota never blocked).
- **Security Incidents**: Response time <15 minutes from detection to secret rotation.
- **Performance Impact**: <5ms added latency for HMAC validation, <2ms for rate limit checks.

Document completion of each checklist item with PR links, test evidence (screenshots, logs, metrics snapshots), and security review sign-off attached to milestone closure notes.
