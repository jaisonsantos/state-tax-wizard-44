# CHECKLIST – M5 concluída / Preparação M6

## Correções rápidas (§5)
- [x] `STATUS.md` reflete comportamento real (portal `portal_session_id`, `stripe_customer_missing`). 【F:STATUS.md†L6-L66】
- [x] `hmac_secret` documentado apenas em `store_settings`. 【F:backend/app/models/models.py†L63-L90】【F:docs/security/hmac.md†L1-L160】
- [x] Replay-store com índice `(store_id, nonce)` e downgrade válido. 【F:backend/app/models/models.py†L205-L220】【F:backend/alembic/versions/202510010002_add_subscription_period_start.py†L1-L69】
- [x] Contrato HMAC (`timestamp\nnonce\nbody`) documentado. 【F:docs/security/hmac.md†L9-L80】
- [x] Métricas de baixa cardinalidade (billing/hmac/rate-limit). 【F:backend/app/observability.py†L37-L96】
- [x] Logs com `nonce_preview` e campos estáveis. 【F:backend/app/security/hmac.py†L60-L180】
- [x] Smoke harness aceita `--security-only` e `SMOKE_*`. 【F:backend/smoke_test.py†L780-L806】
- [x] Backlogs M2–M5 marcam features shipped com rotas reais. 【F:docs/backlog/15_milestone_05_billing.md†L1-L32】

## Gate M5 (Billing/Stripe)
- [x] Portal retorna `portal_session_id` + erro `stripe_customer_missing`; docs alinhadas. 【F:backend/app/schema/billing.py†L45-L52】【F:docs/api/billing.md†L113-L140】
- [x] Degradação `billing_unconfigured` validada. 【F:backend/app/routers/billing.py†L21-L186】【F:backend/tests/test_billing_api.py†L18-L110】
- [x] Enforcement de plano/limites em `/v1/fees/apply`. 【F:backend/app/routers/fees.py†L132-L185】
- [x] Métricas `billing_events_total`, `checkout_sessions_created_total`, `entitlement_denials_total`. 【F:docs/certification/EVIDENCE/metrics_dump.txt†L1-L40】
- [x] Cadeia Alembic única com upgrade/downgrade. 【F:backend/alembic/versions/202510020001_billing_stripe_integration.py†L1-L92】
- [x] Seeds determinísticos (`seed_data.py`). 【F:backend/seed_data.py†L1-L210】
- [x] `pytest -q` (61 testes) cobrindo billing/webhooks. 【F:docs/certification/EVIDENCE/pytest.txt†L1-L40】
- [x] Smokes `analytics`, `reports`, `security` PASS; `billing-only` SKIP documentado sem Stripe. 【F:docs/certification/EVIDENCE/analytics_smoke.txt†L1-L3】【F:docs/certification/EVIDENCE/security_smoke.txt†L1-L7】【F:docs/certification/EVIDENCE/billing_smoke.txt†L1-L1】
- [x] Postman Billing folder atualizado (`portal_session_id` + códigos). 【F:docs/postman/state-tax-wizard.postman_collection.json†L1134-L1186】【F:docs/postman/README.md†L59-L110】
- [x] Frontend Billing consome os endpoints com fallback. 【F:src/pages/Billing.tsx†L1-L220】
- [x] Docs README/STATUS/backlog/Stripe guide sincronizadas. 【F:README.md†L80-L150】【F:docs/billing/stripe.md†L1-L110】

## Evidências
- [x] `migrate.txt` (`alembic upgrade head`). 【F:docs/certification/EVIDENCE/migrate.txt†L1-L10】
- [x] `api_logs.txt` (boot uvicorn). 【F:docs/certification/EVIDENCE/api_logs.txt†L1-L8】
- [x] `metrics_dump.txt` inclui `checkout_sessions_created_total` e `entitlement_denials_total`. 【F:docs/certification/EVIDENCE/metrics_dump.txt†L1-L30】
- [x] `md_index.txt` (≤300 linhas) atualizado. 【F:docs/certification/EVIDENCE/md_index.txt†L1-L40】

## Preparação M6 – próximos gates
1. Integrations SDK + métricas `integration_*` criadas e documentadas.
2. WooCommerce plugin com build/test (`composer test`) e guia de instalação.
3. Shopify app proxy/webhook com testes (`npm run test`) e instruções de partner setup.
4. Makefile/CI estendidos (`woocommerce-build`, `shopify-build`, `integrations-smoke`).
5. Postman folder “Integrations” + Newman job opcional.
6. Evidências novas (`integrations_smoke.txt`, `newman_integrations.txt`) ≤512 KB.
7. `docs/certification/DECISION.md` e `ACTION_PLAN.md` atualizados após entrega.
8. Branch `feature/m6-integrations-alpha-2025-10-04` com PR “Integrations Alpha – WooCommerce & Shopify connectors”.
