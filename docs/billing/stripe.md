# Stripe Billing Integration

This guide documents how the application integrates with Stripe for subscription lifecycle management, how to configure environments, and how to validate the flows in test mode.

## Products, prices & environment variables

1. Create three recurring products in the Stripe Dashboard: **Starter**, **Pro**, and **Plus**.
2. Create monthly prices for each product and capture their price IDs.
3. Populate the following environment variables (see `.env.example` for placeholders):

   ```bash
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   STRIPE_PRICE_ID_STARTER=price_...
   STRIPE_PRICE_ID_PRO=price_...
   STRIPE_PRICE_ID_PLUS=price_...
   ```

4. Restart the API container after updating the `.env` file so settings reload. Without these values the API returns `503 billing_unconfigured` and the billing smoke skips automatically.

## Test-mode workflow

1. Launch the stack: `make up migrate seed`.
2. Run `make billing-smoke`:
   - With Stripe configured it validates entitlements, usage, checkout session creation, and portal session creation.
   - Without Stripe variables it prints `⚠ SKIP: Stripe billing not configured`.
3. Use Stripe test cards (e.g., `4242 4242 4242 4242`, any future expiry/CVC) when completing Checkout Sessions.
4. The Customer Portal allows upgrades/downgrades and cancellation in test mode. Changes propagate immediately to `subscriptions` and surface via the `/v1/billing/entitlements` endpoint.
5. Replay webhooks with the Stripe CLI if required:

   ```bash
   stripe listen --forward-to localhost:8000/api/v1/billing/webhooks/stripe
   ```

   The application verifies signatures with `STRIPE_WEBHOOK_SECRET` and updates metrics/audit logs for every processed event.

## Observability

Billing activity emits metrics and logs alongside the existing fee/security signals:

- `billing_events_total{event}` tracks checkout sessions, portal sessions, webhook outcomes, and skips.
- `checkout_sessions_created_total{plan_tier}` increments on successful upgrade requests.
- `entitlement_denials_total{feature,plan}` captures plan gated features (advanced reports, unlimited transactions, etc.).
- Structured `billing` logs detail checkout sessions, portal hand-offs, webhook processing, and transaction limit violations.

All billing metrics appear in `/metrics` and are captured in `docs/certification/EVIDENCE/metrics_dump.txt`.

## Frontend & Postman

- The Billing page (`/billing`) consumes `/v1/billing/entitlements` and `/v1/billing/usage` to render the plan card, usage meter, trial banner, and CTA buttons. Errors from Stripe (including `billing_unconfigured`) are surfaced to the operator with actionable messaging.
- The Postman collection contains a **Billing** folder that exercises entitlements, usage, checkout, portal, and webhook sample requests. When Stripe is unconfigured the tests echo `BILLING_SKIPPED=true` so CI can treat the run as informational.

## Evidence & automation

- `make billing-smoke` stores console output in `docs/certification/EVIDENCE/billing_smoke.txt`.
- When the Newman billing folder is executed with local Stripe credentials, capture the CLI transcript manually (e.g., `newman_billing.txt`). The file is ignored by default via `.gitignore`, so attach it explicitly in certification packs when available.
- UI screenshots for billing and Settings/HMAC rotation are stored under `docs/certification/EVIDENCE/screens/`.

With these steps Milestone 5 (Billing/Stripe) is fully operational in test mode and ready for sandboxes or pilot stores.
