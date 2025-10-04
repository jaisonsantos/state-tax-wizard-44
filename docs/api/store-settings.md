# Store Settings API

Os endpoints de store settings controlam regras de taxas de entrega e, a partir da M7, configuram os webhooks outbound Taxo (endpoint, eventos e rotação de segredo). São consumidos pela tela React de Settings, pelo serviço de webhooks e pelas automações de suporte.

## Autenticação
Todas as rotas exigem bearer token válido (`POST /api/auth/login`). O usuário autenticado deve ter acesso à loja alvo – do contrário recebe `403`.

## Endpoints

### `GET /api/v1/stores/{store_id}/settings`
Retorna a configuração persistida da loja. Cria um registro na primeira chamada.

**Response**
```json
{
  "store_id": "1d9a5d24-8a53-4a40-9ae1-6fcb83b4f0be",
  "enable_mn": true,
  "enable_co": true,
  "absorb_fee": false,
  "label_override": "Delivery fee",
  "plan": "starter",
  "hmac_last_rotated_at": "2025-10-06T18:24:12+00:00",
  "webhook_active": true,
  "webhook_endpoint": "https://merchant.invalid/webhooks/taxo",
  "webhook_events": ["fee.applied", "report.ready", "hmac.rotated"]
}
```

### `PUT /api/v1/stores/{store_id}/settings`
Persiste as flags e registra `store_settings.update` no `audit_logs`. Campos opcionais podem ser omitidos (`null` remove endpoint/eventos). O serviço normaliza espaços em `label_override` e valida o catálogo de eventos (`fee.applied`, `fee.skipped`, `report.ready`, `hmac.rotated`).

**Request body**
```json
{
  "enable_mn": false,
  "enable_co": true,
  "absorb_fee": true,
  "label_override": "Handling surcharge",
  "webhook_active": true,
  "webhook_endpoint": "https://merchant.invalid/webhooks/taxo",
  "webhook_events": ["fee.applied", "report.ready", "hmac.rotated"]
}
```

**Response**
```json
{
  "store_id": "1d9a5d24-8a53-4a40-9ae1-6fcb83b4f0be",
  "enable_mn": false,
  "enable_co": true,
  "absorb_fee": true,
  "label_override": "Handling surcharge",
  "plan": "starter",
  "hmac_last_rotated_at": "2025-10-06T18:24:12+00:00",
  "webhook_active": true,
  "webhook_endpoint": "https://merchant.invalid/webhooks/taxo",
  "webhook_events": ["fee.applied", "report.ready", "hmac.rotated"]
}
```

### `POST /api/v1/stores/{store_id}/hmac/rotate`
Gera novo segredo HMAC, persiste timestamp, emite `store_secret.rotated` e enfileira webhook `hmac.rotated`. O valor é exibido **apenas uma vez**.

**Response**
```json
{
  "store_id": "1d9a5d24-8a53-4a40-9ae1-6fcb83b4f0be",
  "hmac_secret": "<new-secret-value>",
  "rotated_at": "2025-10-06T18:24:12+00:00",
  "previous_rotated_at": "2025-08-01T12:04:55+00:00"
}
```

> Copie imediatamente: audit logs armazenam apenas metadados, não o segredo.

## Audit trail
- `store_settings.update` captura ator, loja e payload enviado (sem segredo).
- `store_secret.rotated` registra timestamps para compliance e alimenta o webhook `hmac.rotated`.

## Recursos relacionados
- Frontend: `src/pages/Settings.tsx` renderiza toggles/inputs de webhook e o botão de rotação.
- Postman: pasta **Webhooks** (atualiza settings, rota segredo, lista e replay) em `docs/postman/state-tax-wizard.postman_collection.json`.
- Serviço backend: `backend/app/routers/store_settings.py` + `backend/app/services/taxo_webhook_service.py`.
