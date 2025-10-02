# Decision Log — Milestone Alignment (M2 → M5)

## Milestone status

- **LAST_COMPLETED_MILESTONE:** M4 — Security & Rate Limiting. HMAC enforcement, replay storage, and Redis-backed rate limiting are implemented and covered by tests. Evidence: `backend/app/security/hmac.py†L1-L190`, `backend/app/security/rate_limit.py†L1-L210`, `backend/tests/test_fee_security.py†L1-L210`.
- **CURRENT_ACTIVE_MILESTONE:** M5 — Billing & Stripe Integration (blocked). Billing routes return `billing_unconfigured`, migrations crash, and ORM/tests reference fields that do not exist. Evidence: `backend/app/routers/billing.py†L35-L190`, `backend/app/schema/billing.py†L1-L9`, `backend/alembic/versions/20251001_ensure_unique_nonce_index.py†L1-L24`, `backend/tests/test_entitlements.py†L80-L196`.
- **NEXT_SLICE (1–2 weeks):** Unblock Billing/Stripe by repairing the Alembic chain, finishing the billing data model/services, and delivering automated evidence (billing smoke + Newman + metrics + UI screenshots). Track execution via `ACTION_PLAN.md` and `CHECKLIST.md`.

## Key findings

- **Migration failure:** `20251001_ensure_unique_nonce_index.py` references revision `202503150001_hmac_replay_protection`, but the actual migration ID is `202503150001`, so `alembic upgrade head` crashes and the Docker API container never starts. Evidence: `docs/certification/EVIDENCE/api_logs.txt†L1-L60`.
- **Schema gaps:** `backend/app/schema/billing.py` defines only `Entitlements`; other request/response models imported by the router are missing, leading to runtime errors. Evidence: `backend/app/schema/billing.py†L1-L9`, `backend/app/routers/billing.py†L84-L144`.
- **ORM / service drift:** `StripeService` expects `store.email`, `store.stripe_customer_id`, and subscription fields that are absent from the ORM. `Subscription` lacks `plan_tier`, `stripe_customer_id`, and `stripe_subscription_id`, so entitlement enforcement cannot succeed. Evidence: `backend/app/services/stripe_service.py†L106-L169`, `backend/app/models/models.py†L128-L140`.
- **Tests misaligned:** `backend/tests/test_entitlements.py` instantiates `OrderFee(fee_amount=...)` and `Subscription(plan_tier=...)` fields that are not present, so pytest cannot run even after dependencies install. Evidence: `backend/tests/test_entitlements.py†L80-L196`, `docs/certification/EVIDENCE/pytest.txt†L1-L40`.
- **Frontend/doc drift:** The billing UI and Postman collection describe fully functional upgrade flows that do not exist yet. Evidence: `src/pages/Billing.tsx†L1-L260`, `docs/postman/README.md†L60-L110`.

## Risks & dependencies

- **Stripe access:** Test keys and (optionally) `stripe listen` must be available in CI to exercise checkout/webhooks; otherwise billing automation will remain flaky.
- **Database consistency:** Repairing the revision chain must be coordinated with existing environments to avoid orphaned migrations.
- **Security posture:** Billing introduces new secrets (`STRIPE_SECRET_KEY`, webhook secret). Documentation and ops runbooks need guidance on storing/rotating them alongside existing HMAC secrets.
- **Evidence expectations:** Certification requires smoke outputs, Newman reports, metrics dumps, and UI screenshots. Without a working backend these artifacts cannot be produced, which blocks milestone closure.

## API / documentation divergences (top 6)

1. `docs/api/billing.md` documents successful responses, but `/v1/billing/entitlements` and `/v1/billing/usage` currently return `503 billing_unconfigured`. 【F:docs/api/billing.md†L12-L80】【F:backend/app/routers/billing.py†L35-L80】
2. `docs/billing/stripe.md` claims webhook processing and metrics exist; in reality migrations fail before webhooks start and no billing metrics are exported. 【F:docs/billing/stripe.md†L120-L170】【F:backend/alembic/versions/20251001_ensure_unique_nonce_index.py†L1-L24】
3. Postman "Billing" folder expects entitlements usage to succeed, but the collection currently fails because the API short-circuits. 【F:docs/postman/state-tax-wizard.postman_collection.json†L1-L120】【F:backend/app/routers/billing.py†L35-L96】
4. `docs/certification/M5_COMPLETION.md` previously marked the milestone as complete despite failing migrations/tests; updated to blocked in this pass. 【F:docs/certification/M5_COMPLETION.md†L1-L120】【F:docs/certification/EVIDENCE/api_logs.txt†L1-L60】
5. `backend/tests/test_entitlements.py` assumes columns (`fee_amount`, `plan_tier`) that the ORM does not provide, so the documented test coverage does not exist. 【F:backend/tests/test_entitlements.py†L80-L196】【F:backend/app/models/models.py†L128-L140】
6. `docs/api/billing.md` omits the current disabled behaviour (503) and lacks guidance on feature flags; router logic requires explicit handling. 【F:docs/api/billing.md†L12-L160】【F:backend/app/routers/billing.py†L35-L144】

## Impact

- Until migrations and services are fixed, billing cannot be demonstrated, certified, or deployed.
- Frontend billing UX remains a demo shell, and customer-facing upgrade/portal flows are blocked.
- Observability lacks the counters referenced by ops documents, so monitoring/alerting cannot be validated.

See `ACTION_PLAN.md` and `CHECKLIST.md` for the recovery steps and objective gates to close M5.
