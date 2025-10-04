# HMAC Client Examples

Reusable snippets for generating canonical signatures that align with `/v1/fees/quote` and `/v1/fees/apply`.

## TypeScript (shared SDK)
```ts
import { signFeeRequest } from '@state-tax-wizard/sdk';

const payload = {
  store_id: process.env.STW_STORE_ID!,
  order_id: 'web-123',
  destination: { state: 'MN' },
  delivery_method: 'ship',
  items: [],
  shipping_amount_cents: 0,
};

const signed = signFeeRequest(process.env.STW_HMAC_SECRET!, payload);
await fetch(`${process.env.STW_API_BASE_URL}/api/v1/fees/apply`, {
  method: 'POST',
  headers: signed.headers,
  body: signed.body,
});
```

## PHP (WooCommerce plugin)
```php
$timestamp = gmdate('c');
$nonce = bin2hex(random_bytes(8));
$body = wp_json_encode($payload, JSON_UNESCAPED_SLASHES);
$canonical = sprintf("%s\n%s\n%s", $timestamp, $nonce, $body);
$signature = hash_hmac('sha256', $canonical, $secret);

$headers = [
  'Content-Type' => 'application/json',
  'X-Taxo-Timestamp' => $timestamp,
  'X-Taxo-Nonce' => $nonce,
  'X-Taxo-Signature' => $signature,
];
```

## Python (custom integrations)
```python
import hashlib
import hmac
import json
from datetime import datetime, timezone

def build_headers(secret: str, payload: dict) -> tuple[dict[str, str], str]:
    timestamp = datetime.now(timezone.utc).isoformat()
    nonce = secrets.token_hex(16)
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    canonical = f"{timestamp}\n{nonce}\n{body}"
    signature = hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    return {
        'Content-Type': 'application/json',
        'X-Taxo-Timestamp': timestamp,
        'X-Taxo-Nonce': nonce,
        'X-Taxo-Signature': signature,
    }, body
```

Refer to `docs/security/hmac.md` for nonce TTL, timestamp skew, and replay protections. Use `noncePreview(nonce)` when logging to avoid leaking full identifiers.
