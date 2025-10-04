# CHECKLIST – M7 Gate Review

## Correções Rápidas (anti-drift)
- [x] `STATUS.md` reflete o comportamento real do billing. 【STATUS.md:6】
- [x] `hmac_secret` documentado apenas em `store_settings`. 【backend/app/models/models.py:56】【docs/security/hmac.md:1】
- [x] Replay store com índice `(store_id, nonce)` e downgrade válido. 【backend/app/models/models.py:205】
- [x] Contrato HMAC (`timestamp\nnonce\nbody`) documentado com exemplos. 【docs/security/hmac.md:17】
- [x] Métricas existentes de baixa cardinalidade. 【backend/app/observability.py:11】
- [x] Logs com `nonce_preview` e campos estáveis. 【backend/app/security/hmac.py:60】
- [x] Smoke harness aceita `--security-only` e `SMOKE_*`. 【backend/smoke_test.py:780】
- [x] Backlogs M2–M5 marcados como shipped. 【docs/backlog/15_milestone_05_billing.md:1】

## Gate M5 (regressão obrigatória)
- [x] Portal retorna `portal_session_id` + `stripe_customer_missing`. 【backend/app/schema/billing.py:45】【docs/api/billing.md:113】
- [x] Degradação `billing_unconfigured` coberta por testes. 【backend/app/routers/billing.py:21】【backend/tests/test_billing_api.py:18】
- [x] Enforcement de plano/limites em `/v1/fees/apply`. 【backend/app/routers/fees.py:132】
- [x] Métricas `billing_events_total`, `checkout_sessions_created_total`, `entitlement_denials_total`. 【docs/certification/EVIDENCE/metrics_dump.txt:1】
- [x] Cadeia Alembic única com downgrade. 【backend/alembic/versions/202510020001_billing_stripe_integration.py:1】
- [x] Seeds determinísticos. 【backend/seed_data.py:1】
- [x] `pytest -q` verde. 【docs/certification/EVIDENCE/pytest.txt:1】
- [x] Smokes `analytics`, `reports`, `security` PASS; `billing` SKIP controlado. 【docs/certification/EVIDENCE/analytics_smoke.txt:1】【docs/certification/EVIDENCE/billing_smoke.txt:1】
- [x] Postman Billing alinhado. 【docs/postman/state-tax-wizard.postman_collection.json:893】
- [x] Frontend Billing atualizado. 【src/pages/Billing.tsx:1】
- [x] Docs sincronizadas. 【README.md:174】【docs/billing/stripe.md:1】

## Gate M6 – Integrations Alpha (concluído)
- [x] Conectores WooCommerce/Shopify implementados sob `integrations/` com feature flags e packaging. 【integrations/woocommerce/state-tax-wizard.php†L1-L140】【integrations/shopify/src/server.ts†L1-L34】
- [x] SDK/HMAC helpers (TypeScript) publicados e consumidos pelos conectores. 【integrations/sdk/typescript/src/index.ts†L1-L60】
- [x] UI/Onboarding exibe provedor ativo, notas e CTA de instalação. 【src/pages/Settings.tsx†L1-L320】
- [x] Contratos mapeados em `docs/integrations/` + Postman fixtures. 【docs/integrations/woocommerce.md†L1-L120】【docs/postman/state-tax-wizard.postman_collection.json†L900-L980】
- [x] `make integrations-smoke` registrado (PASS/skip documentado). 【Makefile†L1-L160】【backend/smoke_test.py†L360-L880】
- [x] Observabilidade expõe `integrations_requests_total` / `integrations_errors_total`. 【backend/app/observability.py†L59-L150】【docs/security/observability.md†L1-L40】
- [x] Postman pasta “Integrations” cobre positivos/negativos. 【docs/postman/state-tax-wizard.postman_collection.json†L900-L980】
- [x] Docs Quickstart + troubleshooting para cada conector. 【docs/integrations/woocommerce.md†L1-L120】【docs/integrations/support.md†L1-L120】
- [x] Evidências ≤512 KB (smokes/Newman/logs/metrics) arquivadas.
- [x] Compatibilidade M2–M5 preservada (pytest/smokes atuais). 【docs/certification/EVIDENCE/pytest.txt†L1】【docs/certification/EVIDENCE/integrations_smoke.txt†L1】

## Gate M7 – Webhooks & Lifecycle (concluído)
- [x] Endpoint `/v1/billing/webhooks/stripe` com verificação de assinatura, idempotência (`processed_webhooks`), retries/backoff e DLQ. 【F:backend/app/routers/billing.py†L200-L270】【F:backend/app/services/webhook_service.py†L40-L220】【F:backend/app/models/models.py†L220-L260】
- [x] Métricas `webhooks_received_total`, `webhooks_processed_total`, `webhook_processing_latency_ms` documentadas e expostas. 【F:backend/app/observability.py†L77-L160】【F:docs/security/observability.md†L1-L60】
- [x] Atualização de `subscriptions`/`stores` conforme eventos `customer.subscription.*` e `invoice.payment_*` com auditoria. 【F:backend/app/services/webhook_service.py†L200-L360】
- [x] Replay autenticado (`/webhooks/stripe/replay/{event_id}`) com evidências via smoke/Postman. 【F:backend/app/routers/billing.py†L240-L270】【F:backend/smoke_test.py†L820-L960】【F:docs/postman/state-tax-wizard.postman_collection.json†L1700-L1900】
- [x] Pytest + `make webhooks-smoke` + Postman Webhooks (positivos/negativos) com evidências ≤512 KB. 【F:backend/tests/test_billing_webhook_endpoint.py†L1-L140】【F:docs/certification/EVIDENCE/webhooks_smoke.txt†L1-L40】
- [x] Docs sincronizadas (`docs/api/billing.md`, `docs/billing/stripe.md`, `docs/observability.md`, `docs/AGENTE.md`, backlog/STATUS). 【F:docs/api/billing.md†L1-L220】【F:docs/billing/stripe.md†L1-L220】【F:docs/AGENTE.md†L1-L160】【F:docs/backlog/17_milestone_07_webhooks.md†L1-L200】【F:STATUS.md†L6-L70】

## Gate M8 – Launch Readiness (em andamento)
- [ ] Dashboards/alertas configurados para métricas críticas (`webhooks_*`, `integrations_*`, `billing_*`) — blueprint disponível em `docs/observability.md`.
- [x] Estratégia de retenção/limpeza para `processed_webhooks` documentada (ver `docs/observability.md`).
- [ ] QA final (`pytest -q`, `make full-validation`, Postman/Smokes completos) com evidências ≤512 KB.
- [ ] Runbooks, README, STATUS, backlog M8 atualizados com passos de deploy/rollback.
- [ ] Consistency patch cobrindo sincronização final (docs ↔ código ↔ tooling).
