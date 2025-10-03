# Milestone 5 — Billing & Stripe Integration ✅

_[← Milestone 4 — Security](14_milestone_04_security.md) • [Milestone 6 — Integrations →](16_milestone_06_integrations.md)_

## Stage Validation Summary

- ✅ Stripe-backed `/v1/billing/entitlements` and `/v1/billing/usage` return live plan metadata, features, and usage limits with graceful `503 billing_unconfigured` handling.
- ✅ Checkout & Customer Portal flows call Stripe in test mode and surface session IDs/URLs (`portal_session_id`) to the UI and tooling, with `stripe_customer_missing` covering stores without Stripe metadata.
- ✅ Webhooks (subscription created/updated/deleted, invoice paid/failed) update the `subscriptions` table, emit audit logs, and increment Prometheus counters.
- ✅ Entitlement enforcement guards fee application, analytics/reports, and metrics track denials per feature/plan.
- ✅ Tooling (smoke tests, Newman, Postman, docs) aligned with real behaviour, skipping cleanly when Stripe variables are unset.

## Delivered artefacts

| Area | Highlights |
| ---- | ---------- |
| Backend | `StripeService`, `EntitlementService`, `WebhookService`, billing router, Prometheus counters, migration `202510020002`. |
| Data | `stores` now stores Stripe IDs, `subscriptions` tracks plan tier/status/period dates, seeds provide deterministic demo data. |
| Tooling | `make billing-smoke`, Newman Billing folder, Playwright screenshots for Billing & Settings/HMAC rotation. |
| Frontend | Billing page consumes live API, displays plan badges, usage meter, trial messaging, upgrade/portal buttons with error handling. |
| Docs | README, API reference, Stripe guide, runbooks, backlog, and certification write-up updated with configuration instructions and evidence locations. |
| Evidence | `docs/certification/EVIDENCE/*` refreshed (pytest, smokes, metrics, Newman, screenshots). |

## Post-completion notes

- Keep Stripe credentials in `.env` for environments that should exercise billing; unset them to run in mock mode.
- Metrics to monitor: `billing_events_total`, `checkout_sessions_created_total`, `entitlement_denials_total`, transaction limit warnings in logs.
- The Postman collection and smoke tests automatically skip billing flows when `billing_unconfigured` is returned, preventing false alarms in environments without Stripe keys.

Next milestone: [Milestone 6 — Platform Integrations Alpha](16_milestone_06_integrations.md).
