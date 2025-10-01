# Milestone 5 — Billing & Stripe Integration

_[← Milestone 4 — Security](14_milestone_04_security.md) • [Milestone 6 — Integrations →](16_milestone_06_integrations.md)_

## Stage Validation Summary
- **Mock billing endpoint live**: `/v1/billing/entitlements` returns hardcoded plan data for UI development ([`backend/app/routers/billing.py`](../../backend/app/routers/billing.py)).
- **Frontend billing page exists**: Displays static pricing tables and mock subscription history ([`src/pages/Billing.tsx`](../../src/pages/Billing.tsx)).
- **Auth foundation ready**: User context available for linking subscriptions to stores ([`backend/app/core/security.py`](../../backend/app/core/security.py)).
- **Remaining gap**: Real Stripe integration (customers, subscriptions, webhooks), entitlement enforcement, and Customer Portal links are not implemented.

## Next Development Objective
Deliver **Monetization via Stripe** by implementing full subscription lifecycle management, webhook processing for billing events, entitlement enforcement across API/UI, and self-service upgrade/downgrade flows.

## Implementation Plan

### 1. Stripe Customer Lifecycle
- Install `stripe` Python package in `backend/requirements.txt`.
- Add Stripe configuration to `backend/app/core/config.py`:
  - `STRIPE_SECRET_KEY` (env var, separate test/prod keys).
  - `STRIPE_WEBHOOK_SECRET` for signature verification.
  - `STRIPE_PUBLISHABLE_KEY` (exposed via `/v1/billing/config` for frontend).
- Create `backend/app/services/stripe_service.py`:
  - `create_customer(store_id, email, name)`: Creates Stripe customer, stores `customer_id` in `stores` table.
  - `get_or_create_customer(store_id)`: Idempotent customer retrieval/creation.
  - `sync_subscription_status(store_id)`: Fetches latest subscription from Stripe, updates local `subscriptions` table.
- Update `stores` table schema:
  - Add `stripe_customer_id` (varchar(255), nullable, unique).
  - Add `stripe_subscription_id` (varchar(255), nullable).
- Create `subscriptions` table:
  ```sql
  CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id) UNIQUE,
    stripe_subscription_id VARCHAR(255) UNIQUE NOT NULL,
    stripe_customer_id VARCHAR(255) NOT NULL,
    plan_tier VARCHAR(50) NOT NULL, -- starter, pro, plus
    status VARCHAR(50) NOT NULL, -- active, past_due, canceled, trialing
    current_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    current_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
  );
  ```

### 2. Checkout & Portal Integration
- Create `/v1/billing/create-checkout-session` endpoint:
  - Input: `plan_tier` (starter/pro/plus), `success_url`, `cancel_url`.
  - Creates Stripe Checkout Session for subscription, returns `session_id` and `checkout_url`.
  - Attaches store metadata to session for webhook processing.
- Create `/v1/billing/create-portal-session` endpoint:
  - Returns Stripe Customer Portal URL for subscription management.
  - Requires active customer_id, redirects to billing page on completion.
- Update `backend/app/schema/billing.py`:
  - `CheckoutSessionRequest` and `CheckoutSessionResponse` schemas.
  - `PortalSessionResponse` with `portal_url` field.
- Frontend integration in `src/pages/Billing.tsx`:
  - "Upgrade to Pro" / "Upgrade to Plus" buttons call checkout endpoint.
  - "Manage Subscription" button opens Customer Portal.
  - Display current plan badge and next billing date from `/v1/billing/entitlements`.

### 3. Webhook Processing
- Create `/v1/billing/webhooks/stripe` endpoint:
  - Verify signature using `stripe.Webhook.construct_event`.
  - Handle key events:
    - `customer.subscription.created`: Create local subscription record.
    - `customer.subscription.updated`: Sync status changes (active → past_due).
    - `customer.subscription.deleted`: Mark subscription as canceled.
    - `invoice.paid`: Update subscription period dates, emit audit log.
    - `invoice.payment_failed`: Log failure, notify store admin (future).
  - Return 200 immediately to acknowledge receipt, process async if needed.
- Create `backend/app/services/webhook_service.py`:
  - `process_subscription_created(event)`: Parse event, create subscription row.
  - `process_subscription_updated(event)`: Update status and dates.
  - `process_invoice_paid(event)`: Sync billing period, emit audit log with event ID.
- Add webhook event tracking in `audit_logs` table:
  - `event_type`: "stripe_webhook".
  - `event_subtype`: Event name (e.g., "invoice.paid").
  - `event_data`: JSON snapshot of webhook payload.

### 4. Entitlement Enforcement
- Create `backend/app/services/entitlement_service.py`:
  - `get_plan_limits(plan_tier)`: Returns dict with limits:
    - `starter`: 1000 transactions/month, basic reports only.
    - `pro`: 10,000 transactions/month, all reports, analytics dashboard.
    - `plus`: Unlimited transactions, priority support, integrations.
  - `check_entitlement(store_id, feature)`: Returns boolean, checks subscription status and plan limits.
  - `enforce_transaction_limit(store_id)`: Raises `403 Forbidden` if monthly limit exceeded.
- Apply entitlement checks:
  - `/v1/fees/apply`: Check transaction limit before processing.
  - `/v1/reports/*`: Require pro/plus tier for advanced reports.
  - Future integration endpoints: Require plus tier.
- Add Prometheus counter `entitlement_denials_total` by feature and plan tier.
- Frontend feature flags in `src/lib/api.ts`:
  - Fetch entitlements from `/v1/billing/entitlements` (updated to return real data).
  - Disable UI elements for features beyond current plan (with upgrade CTA).

### 5. Real Entitlements Endpoint
- Update `/v1/billing/entitlements`:
  - Replace mock data with real subscription from `subscriptions` table.
  - Return: `plan_tier`, `status`, `current_period_end`, `limits` object, `features` array.
  - Include Stripe-provided `cancel_at_period_end` flag.
- Add endpoint `/v1/billing/usage`:
  - Returns current month's transaction count vs plan limit.
  - Calculates from `order_fees` table where `created_at >= current_period_start`.

### 6. Stripe Products & Prices Setup
- Document in `docs/billing/stripe-setup.md`:
  - Create three products in Stripe dashboard: Starter, Pro, Plus.
  - Create monthly recurring prices for each product.
  - Note Price IDs in `.env.example` as `STRIPE_PRICE_ID_STARTER`, etc.
  - Configure Checkout Session with these Price IDs.
- Provide CLI script `backend/scripts/sync_stripe_products.py`:
  - Fetches products/prices from Stripe API.
  - Validates configuration matches expected tiers.
  - Outputs status report for operations team.

### 7. Automated Testing
- Create `backend/tests/fixtures/stripe/` directory with sample webhook payloads:
  - `subscription_created.json`, `subscription_updated.json`, `invoice_paid.json`.
- Create `backend/tests/test_stripe_webhooks.py`:
  - Mock Stripe signature verification.
  - Test webhook event processing creates/updates subscriptions correctly.
  - Verify audit logs created for each event.
  - Test idempotency (duplicate event doesn't create duplicates).
- Create `backend/tests/test_entitlements.py`:
  - Test transaction limits enforced for starter plan.
  - Test pro/plus features gated correctly.
  - Test upgrade unlocks new features.
  - Test expired subscription blocks access.
- Integration test with Stripe test mode:
  - `backend/tests/test_stripe_integration.py` creates real test customer, subscription.
  - Uses Stripe test clock to simulate billing cycle.
  - Validates local state syncs correctly (requires Stripe test API key).

### 8. Frontend Billing Flow
- Update `src/pages/Billing.tsx`:
  - Fetch real entitlements from updated endpoint.
  - Display current plan badge (Starter/Pro/Plus) with status indicator.
  - Show usage bar: "450 / 1,000 transactions this month" (from `/v1/billing/usage`).
  - Pricing table with feature comparison and CTAs:
    - Current plan: "Current Plan" button (disabled).
    - Higher tiers: "Upgrade to [Tier]" button → Checkout Session.
    - Active subscription: "Manage Subscription" button → Customer Portal.
  - Display next billing date and renewal amount.
  - Show cancel_at_period_end warning if subscription ending.
- Add loading/error states for all billing API calls.
- Toast notifications for successful upgrade/downgrade.

### 9. Documentation
- Create `docs/billing/stripe.md`:
  - Environment variable reference (secret key, webhook secret, price IDs).
  - Webhook endpoint URL configuration in Stripe dashboard.
  - Test card numbers for development (4242 4242 4242 4242).
  - Test clock usage for simulating billing cycles.
  - Troubleshooting guide (webhook failures, signature errors).
- Update `docs/api/billing.md`:
  - Document checkout and portal endpoints with example requests/responses.
  - Describe entitlements schema and usage endpoint.
  - Authentication requirements and rate limits.
- Add billing workflow diagram to `docs/diagrams/billing_flow.mermaid`:
  ```mermaid
  sequenceDiagram
    User->>Frontend: Click "Upgrade to Pro"
    Frontend->>API: POST /v1/billing/create-checkout-session
    API->>Stripe: Create Checkout Session
    Stripe-->>API: session_id, checkout_url
    API-->>Frontend: Return checkout_url
    Frontend->>Stripe: Redirect to Checkout
    User->>Stripe: Complete payment
    Stripe->>API: Webhook: invoice.paid
    API->>Database: Update subscription status
    API-->>Stripe: 200 OK
    User->>Frontend: Redirect to success_url
    Frontend->>API: GET /v1/billing/entitlements
    API-->>Frontend: Updated plan = "pro"
    Frontend->>User: Show success, new features unlocked
  ```

### 10. Operations & Rollout
- Extend `docs/security/environment.md`:
  - Document `STRIPE_SECRET_KEY` setup (test vs production keys).
  - Webhook endpoint URL for Stripe dashboard: `https://api.yourdomain.com/v1/billing/webhooks/stripe`.
  - Required webhook events to enable in Stripe: subscription.*, invoice.*.
- Create operations runbook `docs/billing/operations.md`:
  - Monitoring: Alert on webhook processing failures (4xx/5xx from Stripe).
  - Support playbook: How to manually sync subscription if webhook missed.
  - Refund handling: Stripe refunds don't auto-downgrade, requires manual review.
  - Plan migration: Script to bulk-upgrade early adopters.
- Feature flag: `ENABLE_STRIPE_BILLING` (default false until webhooks tested).

## Deliverable Checklist

| Area | Tasks | Owners |
| --- | --- | --- |
| Backend | Stripe service, customer/subscription lifecycle, webhook handlers | Billing team |
| Database | Subscriptions table, store schema updates | Platform team |
| Frontend | Checkout flow, portal integration, usage display, feature gates | Web team |
| Testing | Webhook fixtures, entitlement tests, Stripe test mode integration | QA team |
| Documentation | Stripe setup guide, API docs, billing workflow diagram | Tech writing |
| Operations | Webhook monitoring, support playbook, environment config | DevOps team |
| Stripe Config | Products/prices setup, webhook endpoint registration | Operations team |

## Exit Criteria Checklist
- [ ] Stripe service creates customers and stores `customer_id` in database.
- [ ] Checkout endpoint generates valid Stripe Sessions and redirects users.
- [ ] Customer Portal endpoint provides self-service subscription management.
- [ ] Webhook endpoint processes subscription and invoice events correctly.
- [ ] Subscriptions table synced with Stripe state (status, dates, plan tier).
- [ ] Entitlement service enforces transaction limits and feature gates.
- [ ] `/v1/billing/entitlements` returns real subscription data, not mocks.
- [ ] `/v1/billing/usage` calculates current month transactions vs limit.
- [ ] Frontend billing page displays real plan, usage, and upgrade CTAs.
- [ ] Webhook signature verification blocks unsigned/invalid requests.
- [ ] Audit logs capture all billing events with Stripe event IDs.
- [ ] Automated tests cover webhook processing, entitlements, and idempotency.
- [ ] Integration test with Stripe test mode validates full lifecycle.
- [ ] Documentation includes Stripe dashboard setup, webhook config, and troubleshooting.
- [ ] Postman collection includes billing endpoints with sample responses.
- [ ] Operations runbook covers webhook monitoring and manual sync procedures.
- [ ] Feature flag allows staged rollout in production.
- [ ] Prometheus metrics track checkout sessions, webhook events, entitlement denials.

## Billing Workflow Validation Scenarios
1. **New Subscription**: User upgrades to Pro → Checkout → Payment → Webhook updates DB → Entitlements unlocked.
2. **Failed Payment**: Invoice payment fails → Webhook marks past_due → User sees warning, features remain active during grace period.
3. **Cancellation**: User cancels via Portal → Subscription ends at period_end → Downgrade to Starter at renewal.
4. **Upgrade Mid-Cycle**: User upgrades Pro → Plus → Prorated charge → Immediate access to Plus features.
5. **Transaction Limit**: Starter user hits 1,000 transactions → Next `/v1/fees/apply` returns 403 with upgrade prompt.
6. **Webhook Retry**: Webhook fails (500 error) → Stripe retries → Duplicate event ignored via idempotency.

## Rollout Plan
1. **Week 9 Day 1-2**: Stripe service implementation and customer creation.
2. **Week 9 Day 3-4**: Checkout and portal endpoints, frontend integration.
3. **Week 9 Day 5**: Subscriptions table migration and webhook endpoint skeleton.
4. **Week 10 Day 1-2**: Webhook event processing and entitlement service.
5. **Week 10 Day 3**: Frontend billing page with real data and usage display.
6. **Week 10 Day 4**: Automated testing (unit, integration, webhook fixtures).
7. **Week 10 Day 5**: Staging deployment, test mode validation, documentation completion.

## Dependencies
- Requires Milestone 4 completion (security and rate limiting stable).
- Stripe account with test mode access for development.
- Frontend routing supports redirect flows (success_url, cancel_url).

## Success Metrics
- **Checkout Conversion**: >80% of initiated checkouts complete payment.
- **Webhook Reliability**: 99.9% of webhook events processed successfully.
- **Entitlement Accuracy**: Zero unauthorized access to gated features.
- **Support Tickets**: <5% of billing issues require manual intervention.
- **Revenue Tracking**: 100% of Stripe subscriptions reflected in local database.

Document completion of each checklist item with PR links, Stripe test mode evidence (customer/subscription IDs, webhook logs), and billing dashboard screenshots attached to milestone closure notes.
