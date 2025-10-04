# Integrations QA Checklist

Use this checklist to validate WooCommerce and Shopify integrations end-to-end.

## Pre-flight
- [ ] API deployed with `INTEGRATIONS_WOO_ENABLED` / `INTEGRATIONS_SHOPIFY_ENABLED` as required.
- [ ] `make migrate && make seed` executed so demo stores (`store_demo_1`, `store_demo_2`) exist.
- [ ] `SMOKE_HMAC_SECRET` exported or rotated prior to tests.

## Automated Coverage
| Command | Purpose |
| --- | --- |
| `make woocommerce-test` | Runs PHPUnit coverage for the PHP plugin (HMAC signatures). |
| `make shopify-test` | Executes Jest coverage for proxy + webhook helpers. |
| `make sdk-test` | Validates the TypeScript SDK canonical signing logic. |
| `make integrations-smoke` | Calls `/v1/integrations/status` and asserts Prometheus counters update. |
| `make m6-validation` | Shortcut for the integrations smoke target (documented evidence). |

## Manual Scenarios
1. **WooCommerce cart fee**
   - Add products to cart, proceed to checkout.
   - Confirm fee line appears with configured label and amount from API.
2. **WooCommerce order persistence**
   - Place an order; confirm `/api/v1/fees/apply` audit log exists (`integration_install`).
3. **Shopify proxy**
   - Trigger proxy route (e.g., app block) and verify the JSON response includes `lines`.
4. **Shopify webhook**
   - Send `orders/create` via Shopify CLI; confirm API responds `200` and `/metrics` increments `integrations_requests_total{provider="shopify",route="status"}`.
5. **Feature flag disabled**
   - With `INTEGRATIONS_WOO_ENABLED=false`, call `POST /v1/integrations/providers/woocommerce/install` to confirm `503 integration_disabled`.
6. **Metrics**
   - Inspect `/metrics` for `integrations_requests_total` and `integrations_errors_total` with provider labels.
7. **Postman**
   - Run folder **Integrations** (status + negative install). Capture CLI evidence in `docs/certification/EVIDENCE/newman_integrations.txt`.

## Evidence
- Rotate and capture `docs/certification/EVIDENCE/integrations_smoke.txt` (`make integrations-smoke`).
- Append `/metrics` grep output to `metrics_dump.txt` ensuring `integration_` counters appear (use `grep 'integration_' | head`).
- Record API logs with `nonce_preview` only (`tail -n 200` from API service logs) and store in `docs/certification/EVIDENCE/api_logs.txt`.

## Rollback
- Disable feature flags (`INTEGRATIONS_WOO_ENABLED=false`, `INTEGRATIONS_SHOPIFY_ENABLED=false`).
- Remove WooCommerce plugin (deactivate) or unset Shopify webhook URLs.
- Retain audit logs for traceability; no database cleanup required beyond optional log pruning.
