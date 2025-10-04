# Certification Decision – Milestone 7

- `LAST_COMPLETED_MILESTONE`: **M7 – Webhooks & Lifecycle**
- `CURRENT_ACTIVE_MILESTONE`: **M8 – Launch Readiness**

## Decision
- **M7: PASS**
  - `/v1/billing/webhooks/stripe` now verifies `Stripe-Signature`, persists events in `processed_webhooks`, enforces idempotência/retentativas e devolve respostas determinísticas (`processed`, `duplicate`, `retry`, `dead_letter`). 【F:backend/app/routers/billing.py†L200-L270】【F:backend/app/services/webhook_service.py†L40-L220】【F:backend/app/models/models.py†L220-L260】
  - `POST /v1/billing/webhooks/stripe/replay/{event_id}` permite reprocessar eventos de DLQ com autenticação, mantendo auditoria e métricas alinhadas. 【F:backend/app/routers/billing.py†L240-L270】
  - Novos contadores/histograma (`webhooks_received_total`, `webhooks_processed_total`, `webhook_processing_latency_ms`) expostos em `/metrics`, documentados e exercitados via smoke/Postman. 【F:backend/app/observability.py†L77-L160】【F:docs/security/observability.md†L1-L60】【F:backend/smoke_test.py†L800-L960】【F:docs/postman/state-tax-wizard.postman_collection.json†L1700-L1900】
  - Tooling atualizado: `make webhooks-smoke`, pasta **Webhooks** no Postman (com assinatura automática), evidências (`webhooks_smoke.txt`, `metrics_dump.txt`, `newman_webhooks.txt`) e STATUS/backlog refletem o estado atual. 【F:Makefile†L1-L150】【F:STATUS.md†L6-L70】【F:docs/backlog/17_milestone_07_webhooks.md†L1-L200】

## NEXT_SLICE – Milestone 8 (Launch Readiness)
1. **Operational Hardening** — dashboards/alertas para métricas críticas (`webhooks_*`, `billing_*`, `integrations_*`), runbooks atualizados e playbooks de incidente. 【F:docs/backlog/18_milestone_08_launch.md†L1-L180】
2. **Paridade de Relatórios & Reversals** — cobrir reversals Shopify/WooCommerce, validar relatórios/analytics com reversals, garantir reconciliação end-to-end. 【F:docs/backlog/18_milestone_08_launch.md†L80-L160】
3. **Go-live Checklist & Evidências** — consolidar QA final (pytest completo + smokes/Postman), coletar métricas finais e preparar documentação de lançamento/rollback. 【F:docs/backlog/18_milestone_08_launch.md†L180-L260】
