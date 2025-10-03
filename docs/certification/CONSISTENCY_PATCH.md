# Consistency Patch Log (Status)

## Concluído nesta rodada
- ✅ Portal API e docs refletem `portal_session_id` + erro `stripe_customer_missing`. 【F:backend/app/schema/billing.py†L45-L52】【F:docs/api/billing.md†L113-L140】
- ✅ README/STATUS/backlog M5 sincronizados após o fix. 【F:README.md†L80-L150】【F:STATUS.md†L6-L66】【F:docs/backlog/15_milestone_05_billing.md†L1-L28】
- ✅ Evidências e métricas (`metrics_dump.txt` com `checkout_sessions_created_total` / `entitlement_denials_total`, `pytest.txt`, smokes) foram renovadas. 【F:docs/certification/EVIDENCE/metrics_dump.txt†L1-L30】【F:docs/certification/EVIDENCE/security_smoke.txt†L1-L7】

## Pendências para M6
1. Adicionar métricas `integration_requests_total` / `integration_failures_total` e documentá-las. 【F:docs/backlog/16_milestone_06_integrations.md†L60-L120】
2. Sincronizar futuros plugins/apps com Postman (folder “Integrations”) e Makefile (`integrations-smoke`).
3. Atualizar `docs/certification/EVIDENCE/` com novos artefatos (integrations smokes/Newman) durante a execução do incremento.
