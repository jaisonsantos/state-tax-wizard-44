# Consistency Patch Log – M7 Webhooks

## Alinhado nesta rodada
- Router `/v1/billing/webhooks/stripe`, serviço de idempotência (`processed_webhooks`) e replay documentados em API/Stripe guide/STATUS. 【backend/app/routers/billing.py†L200-L270】【backend/app/services/webhook_service.py†L40-L260】【docs/api/billing.md†L1-L220】【docs/billing/stripe.md†L1-L220】
- Métricas `webhooks_received_total`, `webhooks_processed_total`, `webhook_processing_latency_ms` implementadas, descritas em `docs/security/observability.md`, e capturadas em `docs/certification/EVIDENCE/metrics_dump.txt`/smokes. 【backend/app/observability.py†L77-L160】【docs/security/observability.md†L1-L60】【backend/smoke_test.py†L800-L960】
- Tooling sincronizado: `make webhooks-smoke`/`m7-validation`, Postman **Webhooks** com pré-script de assinatura, README/STATUS/backlog atualizados. 【Makefile†L1-L150】【docs/postman/state-tax-wizard.postman_collection.json†L1700-L1900】【README.md†L1-L200】【STATUS.md†L6-L70】【docs/backlog/17_milestone_07_webhooks.md†L1-L200】
- Observability playbook (`docs/observability.md`) consolida dashboards, alertas e política de retenção para `processed_webhooks`, referenciado em `docs/billing/stripe.md` e `docs/security/incident-response.md`. 【docs/observability.md†L1-L120】【docs/billing/stripe.md†L120-L200】【docs/security/incident-response.md†L40-L100】

## Próximos cuidados (M8)
- Garantir que dashboards/alertas reflitam os novos counters (`webhooks_*`, `integrations_*`) e anexar prints/comandos ≤512 KB.
- Priorizar execução do job de limpeza em produção e monitorar métricas pós-remoção.
- Consolidar evidências finais (`full_validation`, `webhooks_smoke`, `metrics_dump`, `api_logs`) antes do handoff.
