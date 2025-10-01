# HMAC Request Signing Guide

The State Tax Wizard API enforces replay-resistant HMAC signatures on delivery fee application requests. This guide documents the header contract, signing algorithm, troubleshooting tips, and rotation guidance so plugin and webhook integrations can safely interoperate with `/v1/fees/apply`.

## Required headers

Every signed request must include the following headers:

| Header | Purpose |
| ------ | ------- |
| `X-RDF-Timestamp` | UTC timestamp in ISO 8601 format (e.g. `2025-03-15T18:02:14Z`). Requests more than ±5 minutes from the API clock are rejected with `detail.code = stale_timestamp`. |
| `X-RDF-Nonce` | Unique identifier for the request. Nonces are persisted for 10 minutes; reuse within that window returns `detail.code = replay_detected`. |
| `X-RDF-Signature` | Hex-encoded SHA-256 HMAC digest of the canonical payload. A `sha256=` prefix is optional. |

The canonical payload concatenates the timestamp, nonce, and raw HTTP body separated by newlines:

```
canonical = `${timestamp}\n${nonce}\n${body}`
signature = HMAC_SHA256(secret, canonical)
```

> **Importante:** a assinatura é calculada usando **exatamente** o valor enviado em
`X-RDF-Timestamp` (incluindo `Z` quando presente). O servidor normaliza o
timestamp apenas para checar skew, não para recomputar a assinatura.
Timestamps em epoch (segundos) são aceitos por compatibilidade, porém recomenda-se ISO-8601.

The request body must be identical to the bytes used to compute the signature. When sending JSON, serialize with consistent ordering (e.g. `JSON.stringify` without additional whitespace) and send via the `data`/`body` transport rather than a language helper that might reformat the payload.

## JavaScript example

```ts
import crypto from "crypto";

function signApplyRequest(secret: string, payload: unknown) {
  const body = JSON.stringify(payload);
  const timestamp = new Date().toISOString();
  const nonce = crypto.randomBytes(16).toString("hex");
  const canonical = `${timestamp}\n${nonce}\n${body}`;
  const signature = crypto.createHmac("sha256", secret).update(canonical).digest("hex");

  return {
    headers: {
      "Content-Type": "application/json",
      "X-RDF-Timestamp": timestamp,
      "X-RDF-Nonce": nonce,
      "X-RDF-Signature": signature,
    },
    body,
  };
}
```

## Python example

```python
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone


def sign_apply_request(secret: str, payload: dict[str, object]) -> tuple[dict[str, str], str]:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    nonce = secrets.token_hex(16)
    canonical = f"{timestamp}\n{nonce}\n{body}"
    signature = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return (
        {
            "Content-Type": "application/json",
            "X-RDF-Timestamp": timestamp,
            "X-RDF-Nonce": nonce,
            "X-RDF-Signature": signature,
        },
        body,
    )
```

## Replay protection

- Nonces are stored for 10 minutes. Reusing a nonce within that window returns `409 Conflict` with `detail.code = replay_detected`.
- Expired nonces are purged automatically; you do **not** need to manually clear them.
- Integrations should generate a fresh nonce for every request and never reuse signatures.
- Clock skew beyond ±300 seconds results in `401` with `detail.code = stale_timestamp`. Sync production systems via NTP.

## Troubleshooting

| Symptom | Root cause | Resolution |
| ------- | ---------- | ---------- |
| `detail.code = missing_signature` | `X-RDF-Signature` header absent | Ensure your HTTP client is not stripping custom headers and that authentication middleware runs before signing. |
| `detail.code = invalid_signature` | Timestamp/nonce/body mismatch or wrong secret | Confirm the exact request body bytes used by the HTTP client and regenerate the signature with the same string. |
| `detail.code = replay_detected` | Nonce reused within 10 minutes | Generate a new nonce per request or wait for the TTL to expire. |
| `detail.code = stale_timestamp` | Timestamp outside ±5 minute skew | Synchronise server clocks (e.g. `systemd-timesyncd`, `ntpd`). |

Inspect the `security` logger or the `hmac_validation_failures_total`/`hmac_replay_attempts_total` metrics for additional diagnostics when debugging integration issues.

## Secret rotation

1. Generate a new random 32+ byte secret per store (e.g. `openssl rand -hex 32`).
2. Update the store via the admin tooling or seed script; the `hmac_secret_rotated_at` timestamp records when the secret changed.
3. Distribute the secret over a secure channel to each integration. Avoid emailing raw secrets.
4. Monitor `hmac_validation_failures_total{store_id}` for spikes during the transition. Roll back by reapplying the previous secret if necessary.

For audits, capture the output of `python backend/seed_data.py` (which prints the seeded secret) or query the admin view to show rotation history.
