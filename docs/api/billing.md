# Billing API Reference

## Overview

> ⚠️ **Implementation pending:** the billing endpoints described below are not
> yet functional. The current backend returns `503 billing_unconfigured`, and
> migrations/models must be repaired before these contracts can be exercised.

The Billing API manages subscription lifecycle, entitlements, and usage tracking for the State Tax Wizard platform.

## Authentication

All endpoints require Bearer token authentication:

```text
Authorization: Bearer {access_token}
```

## Endpoints

### Get Entitlements

Get current plan and feature entitlements for a store.

**Endpoint**: `GET /v1/billing/entitlements`

**Parameters**:

- `store_id` (query, required): Store UUID

**Response**: `200 OK` (planned)

```json
{
  "plan": "pro",
  "provider": "stripe",
  "status": "active",
  "trial_ends_at": null,
  "current_period_end": "2025-11-01T00:00:00Z",
  "cancel_at_period_end": false,
  "features": [
    "basic_reports",
    "advanced_reports",
    "fee_calculation",
    "analytics_dashboard"
  ],
  "limits": {
    "transactions_per_month": 10000,
    "advanced_reports": true,
    "analytics_dashboard": true,
    "integrations": false
  }
}
```

**Errors**:

- `401 Unauthorized`: Invalid or missing token
- `403 Forbidden`: Not authorized for this store

---

### Get Usage

Get current billing period usage statistics.

**Endpoint**: `GET /v1/billing/usage`

**Parameters**:

- `store_id` (query, required): Store UUID

**Response**: `200 OK` (planned)

```json
{
  "transactions_used": 4523,
  "transactions_limit": 10000,
  "unlimited": false,
  "percentage_used": 45.23,
  "period_start": "2025-10-01T00:00:00Z",
  "period_end": "2025-11-01T00:00:00Z"
}
```

---

### Create Checkout Session

Create a Stripe Checkout Session for subscription upgrade.

**Endpoint**: `POST /v1/billing/create-checkout-session`

**Parameters**:

- `store_id` (query, required): Store UUID

**Request Body**:

```json
{
  "plan_tier": "pro",
  "success_url": "https://app.example.com/billing/success",
  "cancel_url": "https://app.example.com/billing"
}
```

**Fields**:

- `plan_tier`: One of `starter`, `pro`, `plus`
- `success_url`: URL to redirect after successful payment
- `cancel_url`: URL to redirect if user cancels

**Response**: `200 OK` (planned)

```json
{
  "session_id": "cs_test_...",
  "checkout_url": "https://checkout.stripe.com/pay/cs_test_..."
}
```

**Usage**:

```javascript
// Redirect user to checkout
const response = await fetch(
  "/v1/billing/create-checkout-session?store_id=...",
  {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      plan_tier: "pro",
      success_url: `${window.location.origin}/billing/success`,
      cancel_url: `${window.location.origin}/billing`,
    }),
  },
);

const { checkout_url } = await response.json();
window.location.href = checkout_url;
```

**Errors**:

- `400 Bad Request`: Invalid plan tier
- `401 Unauthorized`: Invalid or missing token
- `403 Forbidden`: Not authorized for this store

---

### Create Portal Session

Create a Stripe Customer Portal session for self-service subscription management.

**Endpoint**: `POST /v1/billing/create-portal-session`

**Parameters**:

- `store_id` (query, required): Store UUID
- `return_url` (query, required): URL to return to after portal

**Response**: `200 OK` (planned)

```json
{
  "portal_url": "https://billing.stripe.com/session/..."
}
```

**Usage**:

```javascript
const response = await fetch(
  `/v1/billing/create-portal-session?store_id=...&return_url=${encodeURIComponent(window.location.href)}`,
  {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  },
);

const { portal_url } = await response.json();
window.location.href = portal_url;
```

**Errors**:

- `400 Bad Request`: Store has no Stripe customer
- `401 Unauthorized`: Invalid or missing token
- `403 Forbidden`: Not authorized for this store

---

### Stripe Webhooks

Process Stripe webhook events (internal endpoint).

**Endpoint**: `POST /v1/billing/webhooks/stripe`

> Pending implementation — backend startup currently fails before
> webhook handlers can run.

**Headers**:

- `stripe-signature`: Webhook signature for verification

**Events Processed**:

- `customer.subscription.created` - New subscription created
- `customer.subscription.updated` - Subscription status/plan changed
- `customer.subscription.deleted` - Subscription canceled
- `invoice.paid` - Payment successful, billing period updated
- `invoice.payment_failed` - Payment failed, grace period started

**Response**: `200 OK`

```json
{
  "status": "success"
}
```

**Note**: This endpoint is called by Stripe, not by frontend code.

---

## Plan Tiers

### Starter

- **Price**: Free trial / $29/month
- **Transactions**: 1,000/month
- **Features**:
  - Basic reports
  - Fee calculation

### Pro

- **Price**: $99/month
- **Transactions**: 10,000/month
- **Features**:
  - All Starter features
  - Advanced reports (CO DR 1786, MN Summary)
  - Analytics dashboard

### Plus

- **Price**: $299/month
- **Transactions**: Unlimited
- **Features**:
  - All Pro features
  - Platform integrations (WooCommerce, Shopify)
  - Priority support

---

## Rate Limits

All billing endpoints are rate-limited:

- **Authenticated requests**: 120 requests/minute per store
- **Webhook endpoint**: 1000 requests/minute (Stripe retry logic)

Rate limit headers included in responses:

```text
X-RateLimit-Limit: 120
X-RateLimit-Remaining: 115
X-RateLimit-Reset: 1696118400
```

---

## Error Responses

### Transaction Limit Exceeded

When a store exceeds their monthly transaction limit:

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

**HTTP Status**: `403 Forbidden`

**Frontend Handling**:

- Display upgrade prompt
- Link to checkout session for higher tier
- Show current usage stats

---

## Observability

### Audit Logs

All billing events are logged to `audit_logs` table with action `stripe_webhook`:

```sql

```

```sql
SELECT
  timestamp,
  payload->>'event_type' AS event,
  payload->>'subscription_id' AS subscription,
  payload->>'plan_tier' AS plan
FROM audit_logs
WHERE action = 'stripe_webhook'
ORDER BY timestamp DESC;
```

### Prometheus Metrics

- `billing_events_total{event}` - Count of webhook events
- `checkout_sessions_created_total{plan_tier}` - Checkout sessions by tier
- `entitlement_denials_total{feature, plan}` - Feature access denials

---

## Testing

### Test Mode

All Stripe operations use test mode keys by default in development.

**Test Cards**:

- Success: `4242 4242 4242 4242`
- Decline: `4000 0000 0000 0002`

**Webhook Testing**:

Use Stripe CLI to forward webhooks locally:

```bash
stripe listen --forward-to localhost:8000/v1/billing/webhooks/stripe
```

### Integration Tests

```python
# Test checkout session creation
response = client.post(
    "/v1/billing/create-checkout-session",
    params={"store_id": store_id},
    json={
        "plan_tier": "pro",
        "success_url": "https://example.com/success",
        "cancel_url": "https://example.com/cancel",
    },
    headers={"Authorization": f"Bearer {token}"},
)
assert response.status_code == 200
assert "checkout_url" in response.json()
```

---

## Migration Guide

For stores migrating from trial to paid plans:

1. User initiates upgrade from UI
2. Frontend calls `/v1/billing/create-checkout-session`
3. User completes payment on Stripe Checkout
4. Webhook `customer.subscription.created` updates database
5. User redirected to `success_url`
6. Frontend refetches `/v1/billing/entitlements` to show new plan
7. Transaction limits automatically updated
