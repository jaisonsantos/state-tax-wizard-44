# Epic 07 — Billing & Stripe Entitlements

## Context
Monetization depends on linking stores to Stripe subscriptions and exposing
plan-based entitlements within the app. The MVP currently mocks entitlements on
the backend and shows static pricing tables in the frontend.

## Current Status
- ✅ `/api/v1/billing/entitlements` returns mock plan data.
- ✅ Frontend billing page lists plans and demo history.
- ❌ No real Stripe integration (customers, subscriptions, webhooks).
- ❌ No ability to upgrade/downgrade or manage trials.

## Acceptance Criteria
1. **Stripe Customer Lifecycle**: Backend service creates Stripe customer for
   each store and stores Stripe IDs in `subscriptions` table.
2. **Checkout & Portal**: API endpoints to generate Stripe Checkout session for
   upgrades and Customer Portal link for managing subscriptions.
3. **Webhook Processing**: Handlers for `invoice.paid`,
   `customer.subscription.updated`, and `customer.subscription.deleted` updating
   local subscription state and emitting audit logs.
4. **Entitlement Enforcement**: Middleware or service ensures plan gates (e.g.,
   reports, integrations) respect subscription status (starter/pro/plus).
5. **Frontend Billing Flow**: Buttons wired to backend endpoints, showing
   real-time status and next billing date.
6. **Documentation**: `docs/billing/stripe.md` capturing environment variables,
   webhook secrets, and test card scenarios.

## Deliverables
- Stripe integration module (likely using `stripe-python`).
- Database migration to persist Stripe customer/subscription IDs.
- Frontend updates for billing interactions.
- CI secrets management plan (test mode keys only).

## Validation
- End-to-end test hitting Stripe test mode to simulate upgrade/downgrade.
- Unit tests for webhook signature validation and entitlement gating.

## Definition of Done
- Stripe test mode credentials managed via environment variables documented in
  `docs/billing/stripe.md` and referenced in deployment scripts.
- Webhook event fixtures stored under `backend/tests/fixtures/stripe/` with
  regression tests covering success and failure paths.
- Entitlement gating enforced across backend endpoints and reflected in
  frontend feature flags; `make smoke` demonstrates a plan upgrade unlocking a
  gated capability.
- Billing page UX captures real subscription state, with screenshots attached to
  the iteration review and accessible offline.
- Epic status updated with Stripe dashboard links (test mode) used for
  verification and any outstanding follow-ups.

## Dependencies
- Relies on Epic 02 for authenticated user context (who initiated upgrade).
- Coordinates with Epic 08 security (webhook signature verification).
