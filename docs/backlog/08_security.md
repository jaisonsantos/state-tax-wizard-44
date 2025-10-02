# Epic 08 — Security Hardening (HMAC, Rate Limiting, Secrets)

## Context

To operate in production, the platform must verify requests, resist abuse, and
secure sensitive data. The MVP currently trusts clients and lacks rate limits
or webhook signing.

## Current Status

- ⚠️ JWT-based auth exists but without store claim enforcement (see Epic 02).
- ❌ No HMAC signatures for plugin/webhook calls.
- ❌ No rate limiting on `/fees/quote` or `/fees/apply`.
- ⚠️ Secrets stored in environment variables but without rotation guidelines.

## Acceptance Criteria

1. **HMAC Signatures**: Implement shared secret per store with header
   verification for `/fees/apply`, `/fees/quote`, and webhook endpoints. Reject
   unsigned or invalid requests.
2. **Replay Protection**: Include timestamp/nonce in signed headers with
   configurable tolerance (e.g., ±5 minutes).
3. **Rate Limiting**: Apply per-store rate limits (e.g., 120 requests/minute) on
   fee endpoints. Exceeding limits returns 429 with retry info.
4. **Secrets Management Doc**: Guidance on storing/rotating JWT secret, HMAC
   keys, Stripe keys (`docs/security/secrets.md`).
5. **Logging & Alerting**: Security-relevant logs (failed auth, rate limit
   breaches) emitted with structured context and counted via Prometheus
   counters.

## Deliverables

- Security middleware/dependencies (FastAPI) for HMAC and rate limiting.
- Store settings migration to persist HMAC secret + rotation timestamps.
- Documentation under `docs/security/`.

## Validation

- Automated tests verifying HMAC signature acceptance/rejection.
- Load test (locust or k6) confirming rate limiting thresholds.
- Manual rotation exercise documented.

## Definition of Done

- HMAC secrets generated per store, stored encrypted, and rotation SOP added to
  `docs/security/secrets.md` with confirmation from operations stakeholders.
- Rate limit metrics (429 counts, tokens remaining) exposed and charted on the
  observability dashboard with alert thresholds defined.
- Failing signature/rate-limit scenarios captured in integration tests (e.g.,
  Woo/Shopify) to prevent regressions.
- Security logs reviewed to ensure no sensitive data leak; sanitized examples
  attached to the iteration exit notes.
- Epic status updated detailing the rotation drill performed and next scheduled
  review.

## Dependencies

- Builds on Epic 02 (auth) and Epic 03 (store settings usage).
