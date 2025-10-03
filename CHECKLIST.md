# Milestone 6 Readiness Checklist

Este checklist complementar aponta para a versão completa em `docs/certification/CHECKLIST.md` e destaca os itens obrigatórios antes de avançar com a execução da M6.

## Gates herdados da M5 (devem permanecer verdes)

- [ ] `alembic upgrade head` com `GUID` portátil (SQLite/Postgres). 【F:docs/certification/EVIDENCE/migrate.txt†L1-L10】
- [ ] `pytest -q` + smokes (`analytics`, `reports`, `security`, `billing` modo skip). 【F:docs/certification/EVIDENCE/pytest.txt†L1-L50】【F:docs/certification/EVIDENCE/analytics_smoke.txt†L1-L3】【F:docs/certification/EVIDENCE/security_smoke.txt†L1-L7】【F:docs/certification/EVIDENCE/billing_smoke.txt†L1-L1】
- [ ] Métricas `/metrics` atualizadas (`billing_events_total`, `checkout_sessions_created_total`, `entitlement_denials_total`). 【F:docs/certification/EVIDENCE/metrics_dump.txt†L1-L18】
- [ ] Postman Billing com `BILLING_SKIPPED` e README alinhados. 【F:docs/postman/state-tax-wizard.postman_collection.json†L940-L1259】【F:docs/postman/README.md†L1-L120】

## Novos gates da M6 (planejados)

- [ ] Endpoints `/v1/integrations/*` + métricas `integration_*` implementados e observáveis.
- [ ] Plugins WooCommerce/Shopify compilam e passam `composer test` / `npm run test`.
- [ ] UI/Admin exibe seção "Integrations" com instruções e links.
- [ ] Evidências ≤512 KB anexadas (pytest, smokes, Newman/CI, artefatos de build).

> Consulte `docs/certification/CHECKLIST.md` para a versão completa e marque cada item durante a execução. 【F:docs/certification/CHECKLIST.md†L1-L34】
