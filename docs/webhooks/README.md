# Taxo Webhooks Overview

State Tax Wizard emite webhooks outbound quando eventos relevantes ocorrem após o cálculo/relatórios das taxas. Esta pasta consolida contrato, catálogo, guias de verificação e runbooks operacionais.

## Contrato de assinatura
- Cabeçalhos obrigatórios:
  - `X-Taxo-Timestamp` – ISO 8601 UTC (`datetime.now(timezone.utc).isoformat()`), janela ±5 minutos.
  - `X-Taxo-Nonce` – UUID4 em hexadecimal, utilizado uma única vez.
  - `X-Taxo-Signature` – HMAC SHA-256 hex codificado sobre `timestamp\nnonce\n<body JSON canonicalizado>`.
  - `X-Taxo-Event` / `X-Taxo-Event-Id` – metadata auxiliar para roteamento no cliente.
- Rejeitar entregas se qualquer cabeçalho estiver ausente ou se o timestamp estiver fora da janela.
- Responder `2xx` para confirmar recebimento; outros códigos acionam retries com backoff 1m→5m→1h→6h→24h.

## Catálogo suportado
- `fee.applied` – taxas cobradas e persistidas.
- `fee.skipped` – pedido avaliado mas sem cobrança.
- `report.ready` – relatório disponível para download autenticado.
- `hmac.rotated` – confirmação de rotação do segredo via UI/API.

Cada payload inclui `id`, `type`, `version`, `occurred_at`, `store_id`, `data` específico e `meta.request_id` para correlação. Detalhes completos estão em [`events.md`](events.md).

## Entrega & observabilidade
- Eventos são persistidos em `webhook_events` com status `pending`, `delivered`, `dead_letter`.
- Tentativas registradas em `webhook_delivery_attempts` com duração e status HTTP.
- Métricas Prometheus: `webhooks_delivery_total{event,status}`, `webhooks_delivery_seconds{event}`, `webhooks_failed_total{reason}`, `webhooks_dead_letter_total{event}`.
- Logs estruturados registram `event`, `status`, `attempt`, `dead_letter`, `error` (truncado a 512 bytes).

## Ferramentas
- **API:** `/v1/webhooks/events` (listar) e `/v1/webhooks/events/{event_id}/replay`.
- **CLI/Smoke:** `python backend/smoke_test.py --webhooks-only` configura store demo, captura entregas locais e valida métricas.
- **Postman:** pasta "Webhooks" assina requisições automaticamente (`pre-request script`).

## Próximos passos (M8)
- Automatizar Newman + smoke na pipeline principal.
- Publicar dashboards (Grafana) com widgets para latência P95, falhas por motivo, DLQ aberta.
- Documentar troubleshooting avançado (correlação com logs de clientes, limites de throughput).
