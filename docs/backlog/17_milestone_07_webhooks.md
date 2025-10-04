# Milestone 7 — Webhooks & Order Lifecycle

_[← Milestone 6 — Integrations](16_milestone_06_integrations.md) • [Milestone 8 — Launch →](18_milestone_08_launch.md)_

## Stage Validation Summary
- **Outgoing webhooks implementados:** `TaxoWebhookService` cria eventos `fee.applied`, `fee.skipped`, `report.ready`, `hmac.rotated` com assinatura `X-Taxo-*` e backoff 1m→24h. Eventos persistem em `webhook_events` + `webhook_delivery_attempts`. 【F:backend/app/services/taxo_webhook_service.py†L33-L452】【F:backend/app/models/models.py†L228-L310】
- **APIs & Admin:** `/v1/webhooks/events` lista/replay; `/v1/stores/{id}/settings` controla `webhook_active/endpoint/events`; UI Settings atualiza toggles e rotação de segredo. 【F:backend/app/routers/webhooks.py†L14-L84】【F:backend/app/routers/store_settings.py†L41-L199】【F:src/pages/Settings.tsx†L560-L626】
- **Emissores:** Fees e Reports enfileiram eventos após operações de sucesso; rotação HMAC dispara `hmac.rotated`. 【F:backend/app/routers/fees.py†L198-L239】【F:backend/app/routers/reports.py†L148-L203】
- **Observabilidade & Tooling:** métricas `webhooks_delivery_total/seconds/failed_total/dead_letter_total`, smoke `--webhooks-only`, Postman pasta "Webhooks", docs `docs/webhooks/*`, runbooks e SLOs publicados. 【F:backend/app/observability.py†L89-L256】【F:backend/smoke_test.py†L838-L969】【F:docs/webhooks/README.md†L1-L120】【F:docs/observability.md†L1-L80】
- **Certificação:** `docs/AGENTE.md` marca M7=PASS; `docs/certification/*` alinhados; próxima etapa é M8 Launch Readiness.

## Remaining Enhancements
- **CI Automation:** adicionar jobs para `python backend/smoke_test.py --webhooks-only` e Newman (pasta "Webhooks").
- **Metrics capture:** provisionar Prometheus/Grafana e armazenar dashboards conforme `docs/observability.md`.
- **Partner SDKs:** atualizar integrações Shopify/WooCommerce para consumir novos eventos (planejado M8+).

## Next Development Objective
- **Milestone 8 – Launch Readiness** focará em automatizar observabilidade, suporte e ensaios de runbooks antes do go-live.

## Implementation Notes
- Migration `202510060001` é obrigatória antes de habilitar webhooks em produção.
- Replays via `/v1/webhooks/events/{event_id}/replay` respeitam configuração atual; garanta `webhook_active=true` e segredo válido.
- `webhook_events` mantém histórico completo – considerar pipeline ETL para análises futuras.
