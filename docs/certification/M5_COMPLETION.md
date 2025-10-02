# Milestone 5 – Billing/Stripe Integration ✅

Milestone 5 is complete. The backend, frontend, observability, and certification assets now cover the full Stripe-based monetisation flow:

- **Database & migrations** — `stores` includes Stripe identifiers, `subscriptions` tracks status/plan/period start & end, and Alembic revision `202510020002` back-fills existing rows. 【F:backend/app/models/models.py†L120-L160】【F:backend/alembic/versions/202510020002_add_subscription_period_start.py†L1-L60】
- **Services & routers** — `StripeService`, `EntitlementService`, and `WebhookService` implement customer lifecycle, checkout/portal creation, plan limits, and webhook processing. `/v1/billing/*` endpoints enforce graceful degradation when Stripe is unconfigured. 【F:backend/app/services/stripe_service.py†L1-L220】【F:backend/app/routers/billing.py†L1-L220】
- **Entitlement enforcement** — `/v1/fees/apply` calls `EnforcementService.enforce_transaction_limit` (guarded by config), and entitlement denials increment `entitlement_denials_total{feature,plan}`. 【F:backend/app/services/entitlement_service.py†L1-L200】【F:backend/app/routers/fees.py†L1-L220】
- **Observability** — Prometheus counters (`billing_events_total`, `checkout_sessions_created_total`, `entitlement_denials_total`) and structured `billing` logs capture upgrades, portal opens, webhook outcomes, and plan denials. 【F:backend/app/observability.py†L1-L140】
- **Frontend & SDK** — Typed helpers in `src/lib/api.ts` return billing contracts, while the Billing page displays plan state, usage meters, trial messaging, and upgrade/portal CTAs with error handling for unconfigured environments. 【F:src/lib/api.ts†L1-L560】【F:src/pages/Billing.tsx†L1-L420】
- **Tooling** — `make billing-smoke` invokes the updated smoke harness, skipping gracefully if Stripe variables are absent. Newman’s Billing folder mirrors the same behaviour. 【F:backend/smoke_test.py†L1-L360】【F:Makefile†L50-L90】
- **Docs & runbooks** — README, environment guides, API reference, and Stripe guide now describe the completed flows, configuration variables, and skip semantics. 【F:docs/api/billing.md†L1-L200】【F:docs/billing/stripe.md†L1-L200】【F:docs/security/environment.md†L1-L200】
- **Evidence** — Updated artefacts (`billing_smoke.txt`, `metrics_dump.txt`, screenshots) live under `docs/certification/EVIDENCE/`. 【F:docs/certification/EVIDENCE/billing_smoke.txt†L1-L5】【F:docs/certification/EVIDENCE/screens/billing.png】【F:docs/certification/EVIDENCE/metrics_dump.txt†L1-L25】

## Exit Criteria Summary

- ✅ Login → checkout → entitlement → portal validated via smoke test and UI.
- ✅ Webhooks replayed idempotently; metrics/audit logs confirm processing.
- ✅ Transaction limits enforced per plan tier.
- ✅ Documentation, Postman, and evidence synchronised with implementation.

Milestone 5 is ready for certification. The next focus is Milestone 6 (Platform Integrations Alpha).
