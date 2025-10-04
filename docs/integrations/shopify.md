# Shopify Integration Guide

Use this document to deploy the State Tax Wizard Shopify app, configure webhooks, and validate the integration slice.

## Prerequisites
- Shopify Partner account with a custom app (orders read access).
- Node.js 18+
- State Tax Wizard API credentials (store ID, HMAC secret).
- Feature flag `INTEGRATIONS_SHOPIFY_ENABLED=true` in the API environment.

## Local Development
```bash
cd integrations/shopify
npm install
npm run dev
```

Environment variables:
| Variable | Purpose |
| --- | --- |
| `STW_API_BASE_URL` | Base URL for the backend (e.g., `http://localhost:8000`). |
| `STW_STORE_ID` | Store ID seeded by the backend (`store_demo_1` by default). |
| `STW_HMAC_SECRET` | Integration secret (rotate via Settings → Rotate HMAC secret). |
| `SHOPIFY_WEBHOOK_SECRET` | Secret generated when registering the Shopify webhook. |

## App Proxy (Quote API)
1. Configure an **App proxy** in the Shopify admin pointing to `https://<your-host>/apps/state-tax-wizard/quote`.
2. The proxy handler signs the payload with `signPayload` (see `src/routes/proxy.ts`) and forwards it to `/api/v1/fees/quote`.
3. Use the Postman request **Integrations / Status** to confirm `integrations_requests_total{provider="shopify",route="status"}` increments after running cart scenarios.

## Webhook Configuration
1. Register the `orders/create` webhook targeting `https://<your-host>/webhooks/orders/create`.
2. Populate `SHOPIFY_WEBHOOK_SECRET` with the secret returned by Shopify.
3. Trigger a test event using the Shopify CLI:
   ```bash
   shopify app webhook trigger orders/create
   ```
4. The app verifies the HMAC header and posts to `/api/v1/fees/apply`. Monitor `/metrics` for `integrations_requests_total{provider="shopify",route="status"}` and `route="install"` as the integration is connected.

## Build & Deploy
```bash
npm run build
npm start
```
Deploy the `dist/` output to your Node runtime (Railway, Fly.io, AWS). Ensure HTTPS is enabled for webhook delivery.

## Validation Checklist
- `make shopify-test` — runs the Jest suite (HMAC and webhook verification).
- `make integrations-smoke` — exercises `/v1/integrations/status` and enforces metrics coverage.
- `/metrics` includes `integrations_requests_total` and `integrations_errors_total` per provider.
- Postman folder **Integrations** passes (status request) and the negative install test returns `503 integration_disabled` when flags are off.

## Troubleshooting
| Symptom | Cause | Resolution |
| --- | --- | --- |
| `401 Invalid Shopify webhook signature` | Secret mismatch | Update `SHOPIFY_WEBHOOK_SECRET`, redeploy, re-send webhook. |
| Proxy call returns 502 | Backend unreachable | Confirm `STW_API_BASE_URL` and inspect backend logs. |
| `integration_disabled` response | Feature flag not enabled | Export `INTEGRATIONS_SHOPIFY_ENABLED=true` (env var) and restart the API service. |
| Duplicate orders | Webhook retried | `/v1/fees/apply` is idempotent; review audit logs for duplicate payloads. |

For canonical HMAC signing guidance, see `docs/security/hmac.md` and the shared SDK in `integrations/sdk/typescript`.
