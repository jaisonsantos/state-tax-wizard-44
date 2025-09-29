# Fees API Enhancements

The fees service now supports store-level remittance settings, absorbed fee
tracking, and order reversals.

## New request fields

`POST /api/v1/fees/quote` and `POST /api/v1/fees/apply` accept an optional
`source_of_remittance` property (`"merchant"` or `"marketplace"`). When set to
`"marketplace"` the Colorado decision tree includes the `CO_MARKETPLACE_SOR`
reason code and the value is persisted on each `order_fee` row.

## Absorbed flag

Responses include `FeeLine.absorbed`, mirroring the `absorb_fee` toggle in store
settings. The API also returns `absorbed` at the top level and persists
`OrderFee.absorbed` for reporting.

## Reversal endpoint

`POST /api/v1/fees/reverse` accepts `{ "store_id", "order_id", "reason" }` with
reasons `DELIVERY_CANCELLED` or `RETURN_POST_DELIVERY`.

- `DELIVERY_CANCELLED` updates matching order fees to `status="reversed"`, sets
  `reversal_reason`, and records a refund in reports.
- `RETURN_POST_DELIVERY` logs the reversal reason without changing the original
  amount.

Each call writes an audit log (`action="fee_reverse"`) and emits structured log
entries so downstream systems can reconcile refunds.
