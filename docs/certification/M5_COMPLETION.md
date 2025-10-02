# Milestone 5 – Billing/Stripe Integration (In Progress)

## Status: ❌ Blocked — backend wiring and evidence incomplete

Milestone 5 has not shipped. The codebase contains scaffolding for Stripe
customers, subscriptions, and entitlement enforcement, but the implementation is
broken end-to-end:

- API handlers immediately return `503 billing_unconfigured` and reference Pydantic
  models that do not exist. 【F:backend/app/routers/billing.py†L35-L190】【F:backend/app/schema/billing.py†L1-L9】
- Alembic migrations reference a revision identifier
  (`202503150001_hmac_replay_protection`) that does not match the actual file,
  causing the API container to crash during startup. 【F:backend/alembic/versions/20251001_ensure_unique_nonce_index.py†L1-L24】【F:docs/certification/EVIDENCE/api_logs.txt†L1-L60】
- `Subscription` ORM definitions and tests expect Stripe-specific columns
  (`plan_tier`, `stripe_customer_id`, usage counters) that have not been added to
  the model, so entitlement checks cannot run. 【F:backend/app/models/models.py†L128-L140】【F:backend/tests/test_entitlements.py†L80-L196】
- `StripeService` depends on store fields that do not exist (`store.email`) and
  never surfaces metrics/logging promised in the docs. 【F:backend/app/services/stripe_service.py†L106-L169】
- Frontend/Postman flows document upgrade and portal journeys, but every request
  fails because billing is still disabled at runtime. 【F:src/pages/Billing.tsx†L1-L260】【F:docs/postman/README.md†L60-L110】

## What exists today

| Area     | Notes                                                                                                                                     |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Router   | Routes for `entitlements`, `usage`, checkout/portal, and webhooks exist but short-circuit or call incomplete services.                    |
| Services | Placeholder `StripeService`, `WebhookService`, and `EntitlementService` files define desired behaviour without working data layer wiring. |
| Database | Migration stubs try to add Stripe columns but the revision chain is corrupted, so no database can be migrated successfully.               |
| Frontend | Billing UI renders plan cards, usage meter, and buttons; all rely on API responses that currently fail.                                   |
| Docs     | `docs/billing/stripe.md` and `docs/api/billing.md` describe the target architecture, not the current behaviour.                           |

## Blockers to call M5 complete

1. Fix the Alembic revision IDs and ensure migrations add the Stripe columns
   and indexes referenced by the ORM. 【F:backend/alembic/versions/202510020001_billing_stripe_integration.py†L1-L60】
2. Extend `Subscription`, `Store`, and related models with the Stripe fields used
   by services/tests (`plan_tier`, `stripe_customer_id`, `stripe_subscription_id`,
   `cancel_at_period_end`, `updated_at`). 【F:backend/app/models/models.py†L128-L140】
3. Implement schema classes (`CheckoutSessionRequest`, `CheckoutSessionResponse`,
   `PortalSessionResponse`, `UsageResponse`) and update routers to handle
   configured/disabled states explicitly. 【F:backend/app/schema/billing.py†L1-L9】
4. Rework `StripeService` to avoid nonexistent store fields and add logging,
   metrics, and error handling that match the documentation. 【F:backend/app/services/stripe_service.py†L106-L169】
5. Add passing automated coverage (pytest + smoke + Newman) that exercises
   entitlements, upgrade, portal, and webhook flows using Stripe test mode. 【F:docs/certification/EVIDENCE/pytest.txt†L1-L40】【F:docs/certification/EVIDENCE/security_smoke.txt†L1-L5】
6. Update documentation/Postman to reflect the real behaviour once the API
   succeeds, attaching evidence artifacts (`billing_smoke.txt`, Newman reports,
   UI screenshots) in `docs/certification/EVIDENCE/`.

## Evidence collected

| Artifact                                        | Outcome                                                                                             |
| ----------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `docs/certification/EVIDENCE/billing_smoke.txt` | Smoke skipped; Stripe not configured and API container down.                                        |
| `docs/certification/EVIDENCE/api_logs.txt`      | Alembic raises `KeyError: '202503150001_hmac_replay_protection'`, preventing the API from starting. |
| `docs/certification/EVIDENCE/pytest.txt`        | Pytest aborts during settings load; billing tests have not executed.                                |

Milestone 5 will remain blocked until the backend can migrate successfully, the
Stripe services/tests pass locally, and evidence (smoke runs, Newman exports,
UI screenshots) is captured alongside updated documentation.
