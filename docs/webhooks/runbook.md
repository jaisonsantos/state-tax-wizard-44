# Webhook Operations Runbook

## Objetivo
Garantir entregas confiáveis dos webhooks outbound Taxo e fornecer procedimentos de resposta a incidentes.

## Contatos
- **Owner primário:** EngOps Taxo Platform
- **Backup:** On-call Billing & Tax (rota PagerDuty `taxo-webhooks`)
- **Slack:** `#taxo-alerts`

## Fluxo de entrega
1. Serviços de fees/reports/secret rotation enfileiram eventos via `TaxoWebhookService.queue_*`.
2. `dispatch_events` lê configurações (`webhook_active`, `webhook_endpoint`, `webhook_events`) e envia HTTP POST.
3. Tentativas são gravadas em `webhook_delivery_attempts`; métricas (`webhooks_delivery_total`, `webhooks_delivery_seconds`, `webhooks_failed_total`, `webhooks_dead_letter_total`) são emitidas.
4. Após exceder o número de tentativas (5), o evento vai para DLQ (`dead_letter=true`).

## Painéis e alertas
- **Dashboard Grafana `Taxo – Webhooks`:**
  - Cartão `Delivery Success Rate` (100% target).
  - Gráfico `Delivery Latency P95` (meta < 5 segundos).
  - Tabela `Dead Letters` (event_id, última falha, store_id).
- **Alertas sugeridos:**
- `webhooks_delivery_seconds_p95 > 5` por 5 minutos → alerta Warning.
  - `increase(webhooks_failed_total[15m]) > 0` → alerta Critical (investigar motivo em `reason`).
  - `increase(webhooks_dead_letter_total[30m]) > 0` → alerta Critical.

## Procedimentos comuns
### 1. Falhas de entrega (HTTP 4xx/5xx)
1. Consultar `/v1/webhooks/events?store_id=...&status=pending`.
2. Validar endpoint e segredo em `/v1/stores/{id}/settings`.
3. Se segredo inválido, acionar operador para atualizar; rotacionar via `/v1/stores/{id}/hmac/rotate`.
4. Após correção, chamar `/v1/webhooks/events/{event_id}/replay`.
5. Monitorar dashboard para confirmar `status=delivered`.

### 2. DLQ crescente
1. Exportar lista `status=dead_letter`.
2. Revisar `last_error` e tentativas.
3. Corrigir causa raiz (endpoint offline, HTTP 400, etc.).
4. Usar replay manual (mesmo procedimento acima).
5. Se volume alto, coordenar com equipe da loja para validação em massa.

### 3. Rotação emergencial do HMAC
1. Executar `/v1/stores/{id}/hmac/rotate` (requer autenticação admin).
2. Atualizar o consumidor com o novo segredo.
3. Confirmar recebimento do evento `hmac.rotated` no cliente.
4. Auditar logs (`audit_logs` -> `store_secret.rotated`).

### 4. Endpoint indisponível
1. Temporariamente desativar webhooks via `/v1/stores/{id}/settings` (`webhook_active=false`).
2. Comunicar loja sobre suspensão e SLA de restabelecimento.
3. Após recuperação, reativar e reenfileirar eventos via `replay`.

## Verificações periódicas
- Executar `python backend/smoke_test.py --webhooks-only` semanalmente em staging.
- Validar checklist `docs/launch/GO_LIVE_CHECKLIST_M8.md` item "Webhooks".
- Atualizar `docs/SLO.md` com dados reais (latência, sucesso) mensalmente.

## Referências
- `backend/app/services/taxo_webhook_service.py`
- `docs/webhooks/verification.md`
- `docs/postman/state-tax-wizard.postman_collection.json` (pasta "Webhooks")
