# Webhook Signature Verification Guide

A verificação deve reproduzir exatamente o algoritmo usado pelo backend (`TaxoWebhookService`).

## Passo a passo
1. Ler cabeçalhos `X-Taxo-Timestamp`, `X-Taxo-Nonce`, `X-Taxo-Signature`.
2. Validar timestamp: converter para UTC e garantir |`now` - `timestamp`| ≤ 5 minutos.
3. Verificar nonce: guardar identificadores recentes (≥10 min) e rejeitar repetições.
4. Canonicalizar o corpo JSON (ordenar chaves, remover espaços). Em JavaScript, `JSON.stringify(payload)` com `sort` prévio.
5. Construir string canônica: `"{timestamp}\n{nonce}\n{canonical_body}"`.
6. Calcular HMAC SHA-256 com o segredo compartilhado e codificar em hexadecimal minúsculo.
7. Comparar com `X-Taxo-Signature` usando comparação em tempo constante.

## Exemplo – Node.js
```ts
import crypto from "node:crypto";

export function verifyTaxoWebhook(
  secret: string,
  timestamp: string,
  nonce: string,
  body: unknown,
  signature: string,
): boolean {
  const canonical = JSON.stringify(body, Object.keys(body as object).sort());
  const message = `${timestamp}\n${nonce}\n${canonical}`;
  const expected = crypto
    .createHmac("sha256", secret)
    .update(message)
    .digest("hex");
  return crypto.timingSafeEqual(
    Buffer.from(signature, "hex"),
    Buffer.from(expected, "hex"),
  );
}
```

## Exemplo – Python (FastAPI)
```py
import hashlib
import hmac
import json
from fastapi import HTTPException

def verify_taxo_request(secret: str, headers, body: bytes) -> dict:
    timestamp = headers["X-Taxo-Timestamp"]
    nonce = headers["X-Taxo-Nonce"]
    signature = headers["X-Taxo-Signature"]

    parsed = json.loads(body.decode("utf-8"))
    canonical = json.dumps(parsed, separators=(",", ":"), sort_keys=True)
    message = f"{timestamp}\n{nonce}\n{canonical}"
    digest = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(digest, signature):
        raise HTTPException(status_code=401, detail="invalid_signature")
    return parsed
```

## Respostas recomendadas do cliente
- `2xx` – entrega aceita (inclusive `204`).
- `4xx` – erro permanente (por ex. `401 invalid_signature`, `409 replay`). Taxo registrará como `dead_letter` após retentativas.
- `5xx` – erro temporário; Taxo reagendará conforme backoff.

## Testes locais
- Utilize `docs/postman/state-tax-wizard.postman_collection.json` → pasta "Webhooks".
- `python backend/smoke_test.py --webhooks-only` cria segredos aleatórios, configura endpoint local e envia eventos reais.
- Ferramenta de captura: `python -m http.server` customizado ou serviço como [webhook.site](https://webhook.site/) durante homologação.
