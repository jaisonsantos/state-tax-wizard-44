# Secrets Management Guide

This guide documents how the State Tax Wizard platform stores, rotates, and audits
secrets across environments. It complements the operational runbooks in
[`docs/security/environment.md`](environment.md) and the HMAC client reference in
[`docs/security/hmac.md`](hmac.md).

## Secrets inventory

| Secret | Where it lives | Primary consumers | Notes |
| --- | --- | --- | --- |
| **JWT signing secret** (`JWT_SECRET`) | Application config (`backend/app/core/config.py`) | Auth router when issuing/verifying access tokens | Required in all environments. Rotate proactively every 90 days or immediately after incidents. |
| **Store HMAC secrets** (`store_settings.hmac_secret`) | Database row per store (`StoreSetting`) | `/v1/fees/apply`, integration webhooks | Seeded with `demo-hmac-secret` for demos; rotate per-store and record the timestamp in `hmac_secret_rotated_at`. |
| **Stripe keys** (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_*`) | Environment variables | Billing router & Stripe webhooks | Omit in environments that should skip billing; endpoints respond with `billing_unconfigured` when unset. |
| **Redis URL** (`REDIS_URL`) | Environment variables | Rate limiter (`backend/app/security/rate_limit.py`) | Optional. When absent the in-memory limiter is used for local/dev workloads. |
| **Database credentials** (`DATABASE_URL`) | Environment variables / connection strings | Alembic, SQLAlchemy session factory | Use separate credentials per environment; avoid embedding secrets in `.env` checked into source control. |

## Storage and distribution

1. **Centralise in a secrets manager** – Store production credentials (JWT,
   Stripe, Redis, database) in Vault, AWS Secrets Manager, or equivalent. Avoid
   exporting secrets directly in CI job logs or Terraform plans.
2. **Template configuration** – Keep `.env.example` as the authoritative list of
   required variables. Never commit populated `.env` files.
3. **Least privilege** – Provision database accounts with minimal grants and
   restrict Stripe webhooks to test/prod keys per environment.
4. **Rotation cadence** – Establish a cadence (e.g., quarterly) for JWT/Stripe
   keys and ad-hoc rotations after incidents or suspected leakage.

## Rotation procedures

### JWT secret rotation

1. Generate a new secret (`openssl rand -hex 32`).
2. Deploy the application with **both** old and new secrets accepted. Use
   `settings.jwt_secret_secondary` (if configured) or roll out in blue/green
   fashion by first updating token verification to accept both values.
3. Rotate the signing secret used for issuing tokens (`JWT_SECRET`).
4. Force-logout all existing sessions by clearing or revoking rows in
   `session_tokens` (see `backend/app/models/models.py`).
5. Remove the old secret from configuration once traffic is using the new
   signing key.

### Store HMAC secret rotation

1. Trigger the rotation via the Settings UI ("Rotate HMAC Secret") or API.
   Successful responses include the new secret once. 【F:src/pages/Settings.tsx†L210-L288】
2. Copy the secret into your secrets manager immediately; it is not persisted in
   logs or subsequent API responses.
3. Update integrations (WooCommerce, Shopify, custom clients) to use the new
   secret when signing `/v1/fees/apply` payloads.
4. Monitor `hmac_validation_failures_total{reason="invalid_signature"}` and
   `hmac_replay_attempts_total` for spikes during the rollout.
5. Verify the rotation timestamp (`hmac_secret_rotated_at`) via the Settings UI
   or API to confirm the change. 【F:backend/app/models/models.py†L57-L110】【F:backend/app/security/hmac.py†L83-L179】

### Stripe credential rotation

1. Create new Stripe API keys and webhook secret in the Stripe dashboard.
2. Update the environment variables (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`,
   `STRIPE_PRICE_ID_*`) via your secrets manager or deployment pipeline.
3. Restart the API so `settings.stripe_secret_key` is reloaded before serving
   new requests. 【F:backend/app/services/stripe_service.py†L15-L120】
4. Replay key webhooks (`stripe trigger customer.subscription.updated`) in test
   mode to validate signature verification and subscription sync.
5. Update the Postman/Newman environment file if local QA suites depend on the
   rotated credentials.

## Audit and monitoring

- HMAC rotations emit `store_secret.rotated` entries in the audit log and
  increment security counters/logs. 【F:backend/app/security/hmac.py†L83-L179】
- Rate limiter incidents record `rate_limit_throttle` events and increment
  `rate_limit_throttles_total{route}`. 【F:backend/app/security/rate_limit.py†L34-L116】
- Billing credential issues surface as `billing_unconfigured` logs and 503
  responses, ensuring downstream automation fails gracefully. 【F:backend/app/routers/billing.py†L19-L84】

Review these signals regularly to spot unauthorised access or misconfigurations.
