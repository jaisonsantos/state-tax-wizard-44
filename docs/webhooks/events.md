# Webhook Event Catalog

Todos os payloads utilizam JSON canonicalizado (chaves ordenadas, sem espaços) antes da assinatura HMAC. Campos `occurred_at` e datas em `data` são sempre ISO 8601 UTC.

## fee.applied
```json
{
  "id": "fee.applied:2bb3b608-986e-4bf8-8d9c-5f4a3a72f234",
  "type": "fee.applied",
  "version": 1,
  "occurred_at": "2025-10-06T18:22:01Z",
  "store_id": "store_123",
  "data": {
    "order_id": "order_456",
    "jurisdiction": "MN",
    "amount_cents": 50,
    "delivery_method": "delivery",
    "reason_codes": ["STATE_DELIVERY_FEE"],
    "absorbed": false,
    "source_of_remittance": "merchant",
    "fee_id": "2bb3b608-986e-4bf8-8d9c-5f4a3a72f234"
  },
  "meta": {
    "request_id": "req_abc"
  }
}
```
- `id` deriva do `order_fee.id`; reentregas reutilizam o mesmo identificador.
- `absorbed=true` indica que a taxa foi paga pela loja (invisível ao shopper).

## fee.skipped
```json
{
  "id": "fee.skipped:a6f587cc0e5d4f4da31d0fd4d37d1bb3",
  "type": "fee.skipped",
  "version": 1,
  "occurred_at": "2025-10-06T18:22:01Z",
  "store_id": "store_123",
  "data": {
    "order_id": "order_456",
    "jurisdiction": "CO",
    "reason_codes": ["OUT_OF_SCOPE"]
  },
  "meta": {
    "request_id": "req_abc"
  }
}
```
- `id` usa hash SHA-256 de `(store_id, order_id, jurisdiction)` → garante idempotência.

## report.ready
```json
{
  "id": "report.ready:4be69ab424a44b6f92cbcf74f4a69e0845ad96f1",
  "type": "report.ready",
  "version": 1,
  "occurred_at": "2025-10-06T18:22:05Z",
  "store_id": "store_123",
  "data": {
    "report": "co_dr1786",
    "format": "csv",
    "from_date": "2025-09-01T00:00:00Z",
    "to_date": "2025-09-30T23:59:59Z",
    "row_count": 42,
    "download_path": "/api/v1/reports/co/dr1786?store_id=store_123&from_date=2025-09-01T00:00:00Z&to_date=2025-09-30T23:59:59Z"
  },
  "meta": {
    "request_id": "req_def"
  }
}
```
- `download_path` requer autenticação do operador (bearer token) e expira conforme política padrão do relatório.

## hmac.rotated
```json
{
  "id": "hmac.rotated:store_123:2025-10-06T18:24:12+00:00",
  "type": "hmac.rotated",
  "version": 1,
  "occurred_at": "2025-10-06T18:24:12Z",
  "store_id": "store_123",
  "data": {
    "rotated_by": "operator@example.com",
    "rotated_at": "2025-10-06T18:24:12Z",
    "previous_rotated_at": "2025-09-01T12:04:55Z"
  }
}
```
- Enviado imediatamente após rotação via UI/API. Usado para confirmar recebimento do novo segredo.

> Consulte [`verification.md`](verification.md) para exemplos de código de validação e [`runbook.md`](runbook.md) para troubleshooting.
