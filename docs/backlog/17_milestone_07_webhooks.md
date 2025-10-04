# Milestone 7 — Webhooks & Order Lifecycle

_[← Milestone 6 — Integrations](16_milestone_06_integrations.md) • [Milestone 8 — Launch →](18_milestone_08_launch.md)_

## Stage Validation Summary

- **Stripe webhooks ingested**: `/v1/billing/webhooks/stripe` verifies `Stripe-Signature`, records events in `processed_webhooks`, enforces idempotency, and exposes replay/metrics for DLQ management. 【F:backend/app/routers/billing.py†L200-L260】【F:backend/app/models/models.py†L220-L260】
- **Retry & DLQ implemented**: Failed events persist attempts/backoff, surface `dead_letter` status, and can be replayed via the authenticated endpoint. 【F:backend/app/services/webhook_service.py†L40-L200】
- **Observability & tooling**: Prometheus counters (`webhooks_received_total`, `webhooks_processed_total`, `webhook_processing_latency_ms`), smoke tests (`make webhooks-smoke`), and Postman folder cover positive/negative flows. 【F:backend/app/observability.py†L77-L140】【F:backend/smoke_test.py†L820-L940】【F:docs/postman/state-tax-wizard.postman_collection.json†L1700-L1900】
- **Docs & certification updated**: API references, Stripe guide, STATUS/backlog, and certification pack reflect webhook lifecycle, replay steps, and evidence capture. 【F:docs/api/billing.md†L1-L200】【F:docs/billing/stripe.md†L1-L200】【F:STATUS.md†L6-L100】
- **Remaining gap**: Shopify/WooCommerce order lifecycle webhooks and fee reversal automation remain future scope (Milestone 8+).

## Next Development Objective

Deliver **Order Lifecycle Management** by implementing webhook handlers for Shopify/WooCommerce order events, reversal logic for refunds/cancellations, and reporting alignment to ensure accurate tax liability ledgering.

## Implementation Plan

### 1. Webhook Infrastructure

- Create unified webhook router `backend/app/routers/webhooks.py`:
  - `/v1/webhooks/shopify` (POST): Handles Shopify webhook events.
  - `/v1/webhooks/woocommerce` (POST): Handles WooCommerce webhook events.
- **Signature Verification**:
  - Shopify: Verify `X-Shopify-Hmac-Sha256` header using shop's webhook secret.
  - WooCommerce: Verify custom `X-WC-Webhook-Signature` using delivery secret.
  - Reject requests with invalid/missing signatures → 401 Unauthorized.
- **Event Parsing**:
  - Extract event type from headers (`X-Shopify-Topic`, `X-WC-Webhook-Topic`).
  - Parse JSON body into platform-specific schemas.
  - Log parsed event to `audit_logs` with `event_type: webhook_received`.

### 2. Shopify Webhook Events

- **Supported Events**:
  - `orders/create`: Order placed (already handled by Milestone 6 for fee application).
  - `orders/paid`: Payment confirmed, update order status if needed.
  - `orders/fulfilled`: Order shipped, no action required (informational).
  - `orders/cancelled`: Order cancelled, trigger reversal.
  - `refunds/create`: Refund issued, trigger partial or full reversal.
- **Implementation** (`backend/app/services/shopify_webhook_service.py`):
  - `process_order_cancelled(event)`: Extract order ID, call reversal service.
  - `process_refund_created(event)`: Calculate refund amount, call partial reversal if fee included.
- **Idempotency**:
  - Store processed webhook IDs in `webhook_events` table:

    ```sql
    CREATE TABLE webhook_events (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      platform VARCHAR(50) NOT NULL, -- shopify, woocommerce
      event_id VARCHAR(255) UNIQUE NOT NULL, -- Platform's unique event ID
      event_type VARCHAR(100) NOT NULL,
      processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
      store_id UUID REFERENCES stores(id),
      payload JSONB NOT NULL
    );
    ```
  - Before processing, check if `event_id` exists; skip if duplicate.

### 3. WooCommerce Webhook Events

- **Supported Events**:
  - `order.created`: Order placed (already handled for fee application).
  - `order.updated`: Status change, check if cancelled/refunded.
  - `order.deleted`: Order deleted (rare), trigger reversal if fee applied.
  - `order.refunded`: Refund issued, trigger reversal.
- **Implementation** (`backend/app/services/woocommerce_webhook_service.py`):
  - `process_order_updated(event)`: Check `status` field (cancelled, refunded), call reversal.
  - `process_order_refunded(event)`: Extract refund amount, call partial reversal if needed.
- **Mapping Order IDs**:
  - WooCommerce order ID stored in `order_fees.external_order_id` during `/v1/fees/apply`.
  - Webhook references WC order ID, query `order_fees` to find matching record.

### 4. Reversal Logic

- Create `/v1/fees/revert` endpoint (internal use + webhook processing):
  - **Input**: `order_fee_id` or `external_order_id`, `reason` (cancelled/refunded/deleted).
  - **Output**: Confirmation of reversal with updated `order_fee` record.
- Update `order_fees` table schema:

  ```sql
  ALTER TABLE order_fees
    ADD COLUMN status VARCHAR(50) DEFAULT 'applied',
    ADD COLUMN reversed_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN reversal_reason VARCHAR(100),
    ADD COLUMN reversal_audit_id UUID REFERENCES audit_logs(id);
  ```
  - Valid `status` values: `applied`, `reversed_full`, `reversed_partial`.
- **Reversal Service** (`backend/app/services/reversal_service.py`):
  - `revert_full(order_fee_id, reason)`:
    - Set `status = 'reversed_full'`, `reversed_at = NOW()`, `reversal_reason = reason`.
    - Create audit log entry with `event_type: fee_reversed`.
    - Emit Prometheus counter `fees_reversed_total` with labels: `jurisdiction`, `reason`.
  - `revert_partial(order_fee_id, refunded_amount, reason)`:
    - Calculate prorated fee reversal based on refunded items.
    - Set `status = 'reversed_partial'`, store partial amount in new `reversed_amount` column.
    - Create audit log entry with original and reversed amounts.
- **Authorization**: Reversal endpoint requires admin role or valid webhook signature.

### 5. Reporting Alignment

- Update report generation to exclude reversed fees:
  - **Minnesota Summary JSON** (`backend/app/routers/reports.py`):
    - Filter `order_fees` WHERE `status = 'applied'` or include separate reversal section.
    - Add `reversals` array to JSON output:

      ```json
      {
        "reporting_period": {...},
        "fees_collected": [...],
        "reversals": [
          {
            "original_transaction_id": "uuid",
            "reversed_at": "2025-04-15T10:30:00Z",
            "reason": "order_cancelled",
            "amount": 0.50
          }
        ],
        "net_collected": 450.00  // fees_collected - reversals
      }
      ```
  - **Colorado DR-1786 CSV** (`backend/app/services/report_service.py`):
    - Add `Status` column: "Applied", "Reversed - Cancelled", "Reversed - Refunded".
    - Include reversed transactions with negative amounts or separate reversal rows.
    - Update summary rows to reflect net collected amount.
- **Analytics Dashboard**:
  - Update `/v1/analytics/overview` to calculate net fees (applied - reversed).
  - Add KPI card for "Reversed Fees (This Month)".
  - Display reversal rate in dashboard insights.

### 6. Webhook Configuration Documentation

- Create `docs/webhooks/shopify.md`:
  - **Setup Instructions**:
    - Navigate to Shopify Admin → Settings → Notifications → Webhooks.
    - Add webhook endpoints:
      - URL: `https://api.statetaxwizard.com/v1/webhooks/shopify`.
      - Format: JSON.
      - Events: `orders/cancelled`, `refunds/create`.
      - Verify webhook secret matches State Tax Wizard settings.
  - **Testing**: Use Shopify's webhook replay feature for development.
  - **Troubleshooting**: Check webhook delivery logs in Shopify admin.
- Create `docs/webhooks/woocommerce.md`:
  - **Setup Instructions**:
    - Install WooCommerce → Settings → Advanced → Webhooks → Add webhook.
    - Delivery URL: `https://api.statetaxwizard.com/v1/webhooks/woocommerce`.
    - Secret: Generate in State Tax Wizard settings, copy to WooCommerce.
    - Topic: `Order updated`, `Order refunded`.
    - Status: Active.
  - **Testing**: Use WooCommerce's webhook testing tool or manually cancel order.
- **Replay Scripts** (`backend/scripts/replay_webhook.py`):
  - CLI tool to replay webhook events from stored `webhook_events` payloads.
  - Usage: `python backend/scripts/replay_webhook.py --event-id <uuid>`.
  - Useful for debugging and testing reversal logic.

### 7. Idempotency & Error Handling

- **Duplicate Event Protection**:
  - Check `webhook_events` table before processing.
  - If `event_id` exists, return `200 OK` with `{"status": "already_processed"}`.
- **Retry Logic**:
  - If reversal service fails (DB error, transient issue), return `500 Internal Server Error`.
  - Platform retries webhook (Shopify retries 19 times over 48 hours).
  - Log retry attempts to `audit_logs` with `event_subtype: webhook_retry`.
- **Dead Letter Queue**:
  - If event processing fails after all retries, store in `failed_webhook_events` table.
  - Alert operations team for manual review.
  - Provide admin endpoint to manually reprocess failed events.

### 8. QA Scenarios (Epic 09 Matrix)

- **MN Matrix E**: Order placed → Fee applied → Order cancelled → Webhook triggers reversal → Report excludes reversed fee.
- **MN Matrix F**: Order placed → Fee applied → Partial refund (1 of 2 items) → Webhook triggers partial reversal → Report shows reduced fee.
- **CO Matrix M**: Colorado order → Fee applied → Refund issued → DR-1786 CSV shows reversal row.
- **Shopify Scenarios**:
  - Create order → Cancel before fulfillment → Webhook received → Fee reversed.
  - Create order → Issue refund after fulfillment → Webhook received → Partial reversal.
- **WooCommerce Scenarios**:
  - Place order → Admin cancels → Webhook received → Fee reversed.
  - Place order → Admin refunds → Webhook received → Fee reversed.
- **Edge Cases**:
  - Duplicate webhook (same event_id) → Idempotency check skips reprocessing.
  - Webhook for order without fee → No reversal, log event, return 200.
  - Invalid signature → 401 Unauthorized, event not processed.

### 9. Automated Testing

- Create `backend/tests/fixtures/webhooks/`:
  - `shopify_order_cancelled.json`, `shopify_refund_created.json`.
  - `woocommerce_order_updated_cancelled.json`, `woocommerce_order_refunded.json`.
- Create `backend/tests/test_webhook_handlers.py`:
  - Test signature verification (valid, invalid, missing).
  - Test event parsing and routing.
  - Test idempotency (duplicate event skipped).
  - Test reversal triggered by webhook.
  - Test audit log creation.
- Create `backend/tests/test_reversal_service.py`:
  - Test full reversal updates `order_fees` correctly.
  - Test partial reversal calculates prorated amount.
  - Test authorization (admin only or webhook signature required).
  - Test Prometheus counter incremented.
- Integration test: Send real webhook to local API, verify DB state.

### 10. Monitoring & Alerts

- **Prometheus Metrics**:
  - `webhook_events_received_total`: Counter by platform, event_type.
  - `webhook_processing_duration_seconds`: Histogram by platform, event_type.
  - `webhook_signature_failures_total`: Counter by platform.
  - `fees_reversed_total`: Counter by jurisdiction, reason (cancelled/refunded).
  - `webhook_idempotency_hits_total`: Counter for duplicate events.
- **Grafana Dashboard**:
  - Panel: Webhook event rate by platform (last 24 hours).
  - Panel: Reversal rate (reversed / applied fees, percentage).
  - Panel: Signature failure rate (should be near zero).
  - Panel: Failed webhook events (alert if > 0).
- **Alerts**:
  - `HighWebhookFailureRate`: >5% of webhook processing returns 500 in 15-minute window.
  - `SignatureFailureSpike`: >10 signature failures in 5 minutes (potential attack).
  - `ReversalAnomalyDetection`: Reversal rate >20% (unusual merchant behavior).

### 11. Documentation Updates

- Update `docs/api/fees.md`:
  - Add `/v1/fees/revert` endpoint documentation.
  - Describe reversal request/response schema.
  - Note authorization requirements.
- Update `docs/reports/mn_summary.md`:
  - Add "Reversals" section documenting JSON schema changes.
  - Provide example output with reversals array.
- Update `docs/reports/co_dr1786.md`:
  - Document `Status` column values.
  - Explain how reversed transactions appear in CSV.
- Create `docs/webhooks/README.md`:
  - Overview of webhook architecture.
  - Links to platform-specific setup guides (Shopify, WooCommerce).
  - Replay script usage.
  - Troubleshooting common issues.

### 12. Operations Runbook

- Create `docs/webhooks/operations.md`:
  - **Monitoring**: Dashboards to watch, alert thresholds.
  - **Failed Events**: How to query `failed_webhook_events`, manual reprocessing steps.
  - **Replay**: When and how to use replay script (e.g., missed webhook during downtime).
  - **Signature Rotation**: If webhook secret compromised, regenerate and update all platforms.
  - **Support Playbook**:
    - Merchant reports missing reversal → Check `webhook_events` table for event receipt → Replay if needed.
    - High failure rate → Check API logs for errors → Escalate to engineering if DB/service issue.

## Deliverable Checklist

| Area | Tasks | Owners |
| --- | --- | --- |
| Backend | Webhook routers, signature verification, event parsing | API team |
| Reversal Service | Full/partial reversal logic, audit logs, metrics | API team |
| Database | `webhook_events` table, `order_fees` schema updates | Platform team |
| Reporting | Exclude reversed fees, add reversals section to outputs | Reporting team |
| Analytics | Update dashboard to show net fees and reversal rate | Web team |
| Testing | Webhook fixtures, pytest coverage, QA scenarios | QA team |
| Documentation | Webhook setup guides, API docs, runbook | Tech writing |
| Monitoring | Prometheus metrics, Grafana dashboards, alerts | DevOps team |

## Exit Criteria Checklist

- [ ] Webhook endpoints accept and verify Shopify/WooCommerce signatures.
- [ ] Event parsing routes to correct service (order cancelled, refund created).
- [ ] Idempotency prevents duplicate processing via `webhook_events` table.
- [ ] Reversal service updates `order_fees` status and creates audit logs.
- [ ] Partial reversal logic calculates prorated amounts correctly.
- [ ] Reports (MN JSON, CO CSV) reflect reversed transactions.
- [ ] Analytics dashboard displays net fees and reversal rate.
- [ ] Automated tests cover webhook handling and reversal scenarios.
- [ ] QA scenarios (MN Matrix E/F, CO Matrix M) pass manual validation.
- [ ] Prometheus metrics track webhook events and reversals.
- [ ] Grafana dashboards visualize webhook activity and failure rates.
- [ ] Alerts configured for high failure rate and signature anomalies.
- [ ] Documentation covers webhook setup for both platforms.
- [ ] Replay script functional and documented.
- [ ] Operations runbook covers monitoring and incident response.
- [ ] Failed webhook events table and manual reprocessing tested.

## Webhook Lifecycle Validation Scenarios

1. **Shopify Cancellation**: Order created → Fee applied → Order cancelled → Webhook received → Fee reversed → Report excludes fee.
2. **Shopify Refund**: Order fulfilled → Refund issued → Webhook received → Partial reversal calculated → Analytics updated.
3. **WooCommerce Cancellation**: Order placed → Admin cancels → Webhook received → Fee reversed → Audit log created.
4. **WooCommerce Refund**: Order completed → Admin refunds → Webhook received → Full reversal → Report shows reversal.
5. **Duplicate Webhook**: Webhook received twice → Second attempt returns "already_processed" → No duplicate reversal.
6. **Invalid Signature**: Tampered webhook → Signature validation fails → 401 Unauthorized → Event not processed.
7. **Missing Fee**: Webhook for order without fee → Log event, no reversal attempted → 200 OK.
8. **Webhook Replay**: Missed event during downtime → Operator runs replay script → Event processed successfully.

## Rollout Plan

1. **Week 13 Day 1-2**: Webhook router and signature verification.
2. **Week 13 Day 3**: Event parsing and idempotency infrastructure.
3. **Week 13 Day 4**: Reversal service implementation.
4. **Week 13 Day 5**: `order_fees` schema migration and reporting updates.
5. **Week 14 Day 1**: Analytics dashboard changes for net fees.
6. **Week 14 Day 2**: Automated testing (webhooks, reversals).
7. **Week 14 Day 3**: QA scenario validation (MN E/F, CO M).
8. **Week 14 Day 4**: Documentation and monitoring setup.
9. **Week 14 Day 5**: Staging deployment and webhook configuration with test stores.

## Dependencies

- Requires Milestone 6 completion (integrations sending order data).
- Requires Milestone 4 completion (HMAC verification foundation).
- Access to test stores for webhook setup (Shopify, WooCommerce).

## Success Metrics

- **Webhook Reliability**: >99.5% of webhook events processed successfully.
- **Reversal Accuracy**: 100% of cancelled/refunded orders reflected in reports.
- **Idempotency**: Zero duplicate reversals due to webhook retries.
- **Latency**: Webhook processing completes in <500ms (p95).
- **Support Tickets**: <2% of reversals require manual intervention.

Document completion of each checklist item with PR links, webhook test logs, QA scenario results, and operations runbook sign-off attached to milestone closure notes.
