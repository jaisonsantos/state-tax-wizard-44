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

## Optional HMAC signatures

`POST /api/v1/fees/apply` supports optional request signing to protect against
payload tampering. When a store setting includes an `hmac_secret`, clients **must**
send:

- `X-RDF-Timestamp`: ISO-8601 timestamp (recommended) or Unix epoch seconds. The
  signature uses the **exact** header value provided, including a trailing `Z`
  when present.
- `X-RDF-Nonce`: unique, one-time value per request.
- `X-RDF-Signature`: lowercase hexadecimal SHA-256 digest of the canonical payload
  (`timestamp + "\n" + nonce + "\n" + body`) using the store secret. The API accepts
  either the bare digest or an explicit algorithm prefix:

```
X-RDF-Signature: <hex digest>
# or
X-RDF-Signature: sha256=<hex digest>
```

If a secret is configured and a required header is **missing**, the API responds
with `401 Unauthorized`. If the signature is present but **invalid**, the API
responds with `403 Forbidden`.

The quote endpoint does not require HMAC, and the reversal endpoint intentionally
leaves HMAC optional for MVP to simplify back-office tooling.

### Rate limiting

Authenticated `/v1/fees/*` routes share a Redis-backed rate limiter (120 requests/minute per store by default). Clients exceeding the quota receive `429 Too Many Requests` with a JSON payload including `retry_after_seconds` and `route`. The Prometheus counter `rate_limit_throttles_total{route}` tracks rejected traffic.

## Reversal endpoint

`POST /api/v1/fees/reverse` accepts `{ "store_id", "order_id", "reason" }` with
reasons `DELIVERY_CANCELLED` or `RETURN_POST_DELIVERY`.

- `DELIVERY_CANCELLED` updates matching order fees to `status="reversed"`, sets
  `reversal_reason`, and records a refund in reports.
- `RETURN_POST_DELIVERY` logs the reversal reason without changing the original
  amount.

Each call writes an audit log (`action="fee_reverse"`) and emits structured log
entries so downstream systems can reconcile refunds.

