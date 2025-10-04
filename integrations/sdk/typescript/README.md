# State Tax Wizard TypeScript SDK

Lightweight helpers for signing requests to the State Tax Wizard API from Node.js or browser extensions.

## Installation
```bash
npm install @state-tax-wizard/sdk
```

## Usage
```ts
import { signFeeRequest } from '@state-tax-wizard/sdk';

const payload = {
  store_id: 'store-demo',
  order_id: 'web-123',
  destination: { state: 'MN' },
  delivery_method: 'ship',
  items: [],
  shipping_amount_cents: 0,
};

const signed = signFeeRequest(process.env.STW_HMAC_SECRET!, payload);
fetch('https://api.statetaxwizard.com/api/v1/fees/apply', {
  method: 'POST',
  headers: signed.headers,
  body: signed.body,
});
```

## Development
```bash
npm install
npm run lint
npm test
npm run build
```

The library exports:
- `signFeeRequest(secret, payload, options)` – returns `{ body, headers }` with canonical HMAC signature.
- `noncePreview(value, length)` – helper for logging the first `length` characters (default 8) of a nonce to avoid leaking secrets.

## Testing
`vitest` ensures signatures remain deterministic when timestamp/nonce overrides are supplied. The canonical string aligns with the backend contract documented in `docs/security/hmac.md`.

## Publishing
1. Update the version in `package.json`.
2. Run `npm run build`.
3. Publish to a private registry or bundle with the WooCommerce/Shopify connectors.

