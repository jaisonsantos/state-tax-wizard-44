# Webhook Configuration Guide (Operator UI)

## Pré-requisitos
- Usuário autenticado com acesso à loja.
- Endpoint HTTPS disponível para receber POST JSON.
- Segredo HMAC compartilhado (gerado via rotação ou fornecido inicialmente).

## Passos na UI (Settings → Webhooks)
1. **Enable webhooks** – marque o toggle "Enable webhooks" para ativar o bloco de configuração.
2. **Delivery endpoint URL** – informe URL completa (https://) do consumidor.
3. **Select events** – escolha pelo menos um entre `fee.applied`, `fee.skipped`, `report.ready`, `hmac.rotated`.
4. **Salvar** – clique em "Save settings"; a API `/v1/stores/{id}/settings` persistirá `webhook_active`, `webhook_endpoint`, `webhook_events`.
5. **Teste** – utilize Postman ou smoke (`python backend/smoke_test.py --webhooks-only`) para validar entrega.

> Se o endpoint estiver vazio ou inválido, o serviço marcará eventos como `failed` com `last_error = "missing_endpoint"` até correção.

## Rotação de segredo
1. Clique em "Rotate HMAC secret".
2. Copie imediatamente o segredo exibido (não será mostrado novamente).
3. Atualize o consumidor antes da próxima entrega.
4. Confirme recebimento do webhook `hmac.rotated` no cliente.

## Troubleshooting rápido
- **Erro `missing_endpoint`**: endpoint não configurado; revise UI.
- **Erro `missing_hmac_secret`**: segredo vazio; execute rotação.
- **DLQ**: veja [`runbook.md`](runbook.md) para replay manual.
- **Assinatura inválida**: garanta que o cliente siga [`verification.md`](verification.md).

## API equivalente
- `GET /v1/stores/{store_id}/settings`
- `PUT /v1/stores/{store_id}/settings` (payload inclui `webhook_active`, `webhook_endpoint`, `webhook_events`)
- `POST /v1/stores/{store_id}/hmac/rotate`
- `GET /v1/webhooks/events?store_id=...`
- `POST /v1/webhooks/events/{event_id}/replay`
