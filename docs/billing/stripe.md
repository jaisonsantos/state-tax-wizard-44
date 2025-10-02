# Stripe Billing Integration

This document describes the intended Stripe billing integration for the State Tax Wizard platform.

> ⚠️ **Current state:** the Stripe workflow is not yet implemented. The API still
> returns `billing_unconfigured`, migrations fail, and the services described
> below represent the target architecture rather than working behaviour.

## Overview

The platform plans to use Stripe for subscription management with three tiers:

- **Starter** – 1,000 transactions/month, basic reports
- **Pro** – 10,000 transactions/month, advanced reports & analytics
- **Plus** – Unlimited transactions, integrations & priority support

## Environment Configuration

### Required Environment Variables

```bash
# Stripe API keys
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Stripe product price IDs
STRIPE_PRICE_ID_STARTER=price_...
STRIPE_PRICE_ID_PRO=price_...
STRIPE_PRICE_ID_PLUS=price_...
```

### Stripe Dashboard Setup

1. **Create products** (Stripe Dashboard → Products) for Starter, Pro, and Plus subscriptions.
2. **Copy price IDs** from each product and map them to the environment variables above.
3. **Configure a webhook** (Developers → Webhooks):
   - Endpoint URL: `https://your-domain.com/v1/billing/webhooks/stripe`
   - Events to listen for:
     - `customer.subscription.created`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.paid`
     - `invoice.payment_failed`
   - Copy the signing secret into `STRIPE_WEBHOOK_SECRET`.

## Testing

### Test Cards

Use Stripe test mode cards:

- Success: `4242 4242 4242 4242`
- Decline: `4000 0000 0000 0002`
- 3D Secure: `4000 0025 0000 3155`

Any future expiration date and CVC value works.

### Test Clock

1. Stripe Dashboard → Developers → Test Clocks
2. Create a test clock and attach it to a test customer
3. Advance the clock to simulate renewals or payment failures

## API Endpoints

### Get Entitlements *(not yet available)*

> Currently returns `503 billing_unconfigured`.

```http
GET /v1/billing/entitlements?store_id={store_id}
Authorization: Bearer {token}
```

Returns current plan, features, and limits.

### Get Usage *(not yet available)*

> Currently returns `503 billing_unconfigured`.

```http
GET /v1/billing/usage?store_id={store_id}
Authorization: Bearer {token}
```

Returns transaction usage for the current billing period.

### Create Checkout Session *(not yet available)*

> Currently returns `503 billing_unconfigured`.

```http
POST /v1/billing/create-checkout-session?store_id={store_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "plan_tier": "pro",
  "success_url": "https://app.example.com/billing/success",
  "cancel_url": "https://app.example.com/billing"
}
```

Returns a `checkout_url` for redirecting the customer to Stripe Checkout.

### Create Customer Portal Session *(not yet available)*

> Currently returns `503 billing_unconfigured`.

```http
POST /v1/billing/create-portal-session?store_id={store_id}&return_url={url}
Authorization: Bearer {token}
```

Returns a `portal_url` for self-service subscription management.

## Webhook Processing

Stripe webhooks will be posted to `/v1/billing/webhooks/stripe` and verified using `STRIPE_WEBHOOK_SECRET`.

- Acknowledge with `200 OK`
- Log failures while still returning `200 OK` so Stripe handles retries
- Process idempotently to avoid duplicate subscription updates

### Events to handle

- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.paid`
- `invoice.payment_failed`

## Entitlement Enforcement

Transaction limits will be enforced in the fees service:

```python
from app.services.entitlement_service import EntitlementService

EntitlementService.enforce_transaction_limit(db, store_id)
```

An exceeded limit should return:

```json
{
  "detail": {
    "code": "transaction_limit_exceeded",
    "message": "Monthly transaction limit of 1000 exceeded. Please upgrade your plan.",
    "current_usage": 1001,
    "limit": 1000
  }
}
```

Frontend handling should prompt for upgrades and link to a checkout session.

## Observability

- Audit logs will capture `stripe_webhook` events with plan and customer identifiers.
- Prometheus metrics to expose: `billing_events_total`, `checkout_sessions_created_total`, `entitlement_denials_total`.

---

This integration guide will be updated once the Stripe implementation is complete.
