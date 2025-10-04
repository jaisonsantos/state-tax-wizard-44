# Milestone 8 Readiness Checklist (Resumo)

Este checklist resume os itens críticos antes de executar a rodada "Launch Readiness". Use `docs/certification/CHECKLIST.md` como fonte primária para marcação detalhada.

## Gates herdados (devem permanecer verdes)
- [x] `alembic upgrade head` inclui migration 202510060001 (webhook outbox). 【F:backend/alembic/versions/202510060001_taxo_webhooks_outbox.py†L32-L108】
- [x] `pytest -q` (73 testes) executado após merge de M7. 【F:docs/certification/EVIDENCE/pytest.txt†L1-L10】
- [ ] Smoke webhooks disponível (`python backend/smoke_test.py --webhooks-only` ou `make webhooks-smoke` em ambiente com Docker). 【F:docs/certification/EVIDENCE/webhooks_smoke.txt†L1-L10】
- [ ] Newman "Webhooks" rodando em CI (planejado para M8). 【F:docs/postman/state-tax-wizard.postman_collection.json†L1820-L2140】

## Novos gates da M8 (planejamento)
- [ ] Dashboards Grafana publicados (latência, sucesso, DLQ). 【F:docs/observability.md†L1-L80】
- [ ] Alertas Prometheus configurados (`webhooks_delivery_seconds`, `webhooks_failed_total`, `webhooks_dead_letter_total`). 【F:docs/observability.md†L1-L80】
- [ ] Runbooks de deploy/rollback e suporte aprovados. 【F:docs/launch/RUNBOOKS.md†L1-L140】【F:docs/SUPPORT_PLAYBOOK.md†L1-L160】
- [ ] GO LIVE checklist revisado com owners e datas. 【F:docs/launch/GO_LIVE_CHECKLIST_M8.md†L1-L200】
- [ ] SLOs de webhooks aceitos (P95 ≤5s, sucesso ≥99.5%, DLQ=0). 【F:docs/SLO.md†L1-L120】

## Próximos passos
1. Provisionar stack Prometheus/Grafana para capturar métricas reais e anexar evidências (`metrics_dump.txt`).
2. Automatizar smoke/Postman no CI e anexar relatórios ≤512 KB.
3. Executar ensaio do runbook de rollback com base seedada.
4. Atualizar `docs/certification/CHECKLIST.md` conforme cada gate for concluído.
