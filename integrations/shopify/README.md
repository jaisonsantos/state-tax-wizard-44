# State Tax Wizard – Shopify App

This reference app proxies cart fee quotes and processes order webhooks from Shopify to the State Tax Wizard API.

## Features
- **App proxy** at `/apps/state-tax-wizard/quote` for storefront cart integrations.
- **Webhook handler** for `orders/create` events with signature verification.
- Shared HMAC signing that reuses the canonical format (`timestamp\nnonce\nbody`).

## Requirements
- Node.js 18+
- Shopify Partner account with custom app permissions (Orders read access).
- State Tax Wizard API credentials (store ID + HMAC secret).

## Getting Started
```bash
npm install
npm run dev
```

Environment variables:

| Variable | Description |
| --- | --- |
| `PORT` | Server port (default `4000`). |
| `STW_API_BASE_URL` | Base URL for the State Tax Wizard backend. |
| `STW_STORE_ID` | Store identifier from State Tax Wizard. |
| `STW_HMAC_SECRET` | HMAC secret for API signing. |
| `SHOPIFY_WEBHOOK_SECRET` | Secret provided by Shopify when registering webhooks. |

## Testing
```bash
npm test
```

The Jest suite validates HMAC signing and webhook verification utilities.

## Build & Deploy
```bash
npm run build
npm start
```

Deploy the compiled `dist/` directory to your preferred Node runtime (e.g., Railway, Fly.io). Ensure the environment variables above are configured and that the Shopify app proxy + webhook URLs point to the deployed host.

## Observability
- Monitor `/api/v1/integrations/status?store_id=<id>` to confirm the Shopify provider is enabled.
- The backend increments `integrations_requests_total{provider="shopify"}` for proxy/webhook calls and `integrations_errors_total` for failures, enabling Prometheus/Grafana dashboards.

## Troubleshooting
- Webhook `401` errors typically indicate a rotated secret; update `SHOPIFY_WEBHOOK_SECRET` and retry using Shopify CLI (`shopify app webhook trigger orders/create`).
- Cart quote failures may stem from mismatched payloads; inspect the `state-tax-wizard` metafield logs and backend audit trail (`integration_install`).
