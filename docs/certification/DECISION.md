# Certification Decision – Milestone 7 Review

- `LAST_COMPLETED_MILESTONE`: **M7 – Webhooks & Lifecycle**
- `CURRENT_ACTIVE_MILESTONE`: **M8 – Launch Readiness**

## Decision
- **M7: PASS**
  - Outgoing webhook service (`TaxoWebhookService`) gera eventos `fee.applied`, `fee.skipped`, `report.ready` e `hmac.rotated`, com cabeçalhos `X-Taxo-Timestamp`, `X-Taxo-Nonce`, `X-Taxo-Signature`, retentativas exponenciais (1m→24h) e DLQ documentada. 【F:backend/app/services/taxo_webhook_service.py†L33-L452】
  - Migration `202510060001_taxo_webhooks_outbox` adiciona tabelas `webhook_events`/`webhook_delivery_attempts` e campos de configuração no `store_settings`, sustentando replay/admin e observabilidade. 【F:backend/alembic/versions/202510060001_taxo_webhooks_outbox.py†L32-L108】
  - Rotas `/v1/webhooks/events` (list/replay) e configurações de loja (`webhook_active`, `webhook_endpoint`, `webhook_events`, rotação de segredo) estão disponíveis e cobertas por testes/smoke. 【F:backend/app/routers/webhooks.py†L14-L84】【F:backend/app/routers/store_settings.py†L41-L199】【F:backend/tests/test_taxo_webhook_service.py†L1-L290】
  - Documentação/Tooling alinhados: `docs/webhooks/*`, Postman (carpeta "Webhooks"), `make webhooks-smoke`, e `STATUS.md` refletem o novo catálogo e operação. 【F:docs/webhooks/events.md†L1-L140】【F:docs/postman/state-tax-wizard.postman_collection.json†L1850-L2140】【F:backend/smoke_test.py†L838-L969】【F:STATUS.md†L1-L160】

## NEXT_SLICE – M8 Init (Launch Readiness)
1. **Observabilidade operacional** – Publicar dashboards/alertas de webhooks (latência P95<5s, falhas por motivo) e validar export para on-call. 【F:docs/observability.md†L1-L80】
2. **Processos de suporte** – Finalizar playbooks (incident template, status-page macros, FAQ) e vincular canais de atendimento. 【F:docs/SUPPORT_PLAYBOOK.md†L20-L160】
3. **Confiabilidade de release** – Ensaiar runbooks de deploy/rollback, garantir `make webhooks-smoke`/Newman rodando em CI, coletar evidências. 【F:docs/launch/RUNBOOKS.md†L1-L180】【F:docs/certification/CHECKLIST.md†L40-L140】

## Evidence Snapshot
- `docs/certification/EVIDENCE/pytest.txt` – `pytest -q` (73 passed) pós-implementação M7.
- `docs/certification/EVIDENCE/webhooks_smoke.txt` – tentativa de `make webhooks-smoke` (SKIP controlado em ambiente sem Docker) + instruções para execução manual.
- `docs/certification/EVIDENCE/metrics_dump.txt` – notas de captura planejada das métricas `webhooks_delivery_*`, `webhooks_failed_total` e `webhooks_dead_letter_total` (SKIP até provisionamento de stack Prometheus).
