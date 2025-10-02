# Epic 09 — Webhooks, Refunds & Order Lifecycle Reversals

## Context

Merchants need accurate ledgering even when orders are cancelled or refunded.
The MVP lacks webhook ingestion and reversal logic, risking over-collection of
fees and compliance issues.

## Current Status

- ❌ No webhook endpoints for Shopify or Woo order events.
- ❌ No refund/cancellation handling; `order_fees` cannot be reverted.
- ⚠️ QA matrix highlights pending scenarios (MN E/F, CO M).

## Acceptance Criteria

1. **Webhook Endpoints**: Implement `/api/v1/webhooks/shopify` and
   `/api/v1/webhooks/woocommerce` with signature verification and payload
   parsing for order paid/fulfilled/cancelled events.
2. **Reversal Logic**: New endpoint or service (e.g., `/api/v1/fees/revert`)
   that marks `order_fees` entries as reversed, emits audit logs, and adjusts
   reports to exclude refunded amounts.
3. **Idempotency**: Webhook processing must be idempotent (dedupe via event ID).
4. **Reporting Alignment**: Reports reflect reversals with dedicated columns for
   refunds/cancellations.
5. **Documentation**: Runbook detailing webhook setup, sample payloads, and how
   to replay events for debugging.

## Deliverables

- FastAPI routers for webhooks and revert operations.
- Database migration adding `status` and `reversed_at` columns to `order_fees`.
- Updated reports logic and tests.
- Documentation under `docs/webhooks/`.

## Validation

- Unit/integration tests for webhook event parsing and idempotency.
- Manual QA executing MN Matrix E/F and CO M scenarios using sample payloads.

## Definition of Done

- Webhook endpoints deployed behind feature flags initially, with staging
  evidence (payload samples + logs) attached to the iteration exit report.
- Reversal operations reflected in database schema diagrams and accompanied by
  data migration backfill steps if required.
- Reports updated to display reversal metrics, with contract tests covering both
  positive and reversed transactions.
- QA checklist updated with replay instructions for Shopify and Woo events,
  including curl examples and expected audit log entries.
- Epic status notes include links to stored webhook payload fixtures and replay
  scripts.

## Dependencies

- Requires Epic 08 security (HMAC) and Epic 03 fee engine enhancements.
