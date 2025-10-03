# Decision Log — Milestone Alignment (M5 → M6)

## Milestone status

- **LAST_COMPLETED_MILESTONE:** M5 — Billing & Stripe Integration. Migrações executam limpas com o `GUID` portátil, StripeService persiste `contact_email`, e os fluxos de entitlements/usage/checkout/portal estão cobertos por testes e smokes. 【F:docs/certification/EVIDENCE/migrate.txt†L1-L10】【F:backend/app/services/stripe_service.py†L1-L220】【F:docs/certification/EVIDENCE/analytics_smoke.txt†L1-L3】【F:docs/certification/EVIDENCE/security_smoke.txt†L1-L7】
- **CURRENT_ACTIVE_MILESTONE:** M6 — Platform Integrations Alpha. Conectores WooCommerce/Shopify, métricas `integration_*` e tooling dedicados permanecem no backlog como próximo incremento. 【F:docs/backlog/16_milestone_06_integrations.md†L1-L160】【F:docs/certification/ACTION_PLAN.md†L1-L73】
- **NEXT_SLICE (1–2 semanas):** Entregar plugins Woo/Shopify e atualizar UI/CI/doc tooling conforme plano em `ACTION_PLAN.md`, preservando a certificação de M5 com evidências atualizadas a cada execução. 【F:docs/certification/ACTION_PLAN.md†L1-L73】【F:docs/certification/CHECKLIST.md†L1-L34】

## Key findings

- **Stack de billing estabilizado:** Cadeia Alembic aplicada em SQLite, counters Prometheus (`billing_events_total`, `checkout_sessions_created_total`, `entitlement_denials_total`) expostos em `/metrics`, e degradação graciosa `billing_unconfigured` coberta por testes de API e smoke. 【F:docs/certification/EVIDENCE/migrate.txt†L1-L10】【F:backend/app/observability.py†L31-L88】【F:backend/tests/test_billing_api.py†L18-L105】【F:docs/certification/EVIDENCE/billing_smoke.txt†L1-L1】
- **Coleção Postman alinhada aos runbooks:** Pasta "Billing" agora executa entitlements, usage, checkout, portal e webhook, marcando `BILLING_SKIPPED` quando Stripe está desabilitado – exatamente o comportamento descrito em `docs/billing/stripe.md`. 【F:docs/postman/state-tax-wizard.postman_collection.json†L940-L1259】【F:docs/billing/stripe.md†L15-L60】
- **Observabilidade & QA documentadas:** Evidências (`api_logs.txt`, `metrics_dump.txt`, smokes e pytest) foram regeneradas e linkadas em `docs/AGENTE.md`/`DECISION.md`, permitindo reproduzir o gate de certificação sem lacunas. 【F:docs/certification/EVIDENCE/api_logs.txt†L1-L8】【F:docs/certification/EVIDENCE/metrics_dump.txt†L1-L18】【F:docs/certification/EVIDENCE/pytest.txt†L1-L50】【F:docs/AGENTE.md†L40-L90】

## Risks & dependencies

- **Chaves Stripe em ambientes não-prod:** É preciso provisionar `STRIPE_SECRET_KEY`/`STRIPE_WEBHOOK_SECRET` em pipelines que queiram executar checkout/portal end-to-end; caso contrário os fluxos permanecem em modo SKIP. 【F:docs/billing/stripe.md†L15-L60】
- **Integrações externas (M6):** Sucesso da próxima iteração depende de credenciais WooCommerce/Shopify e de métricas novas (`integration_requests_total`, `integration_failures_total`) documentadas e observáveis. 【F:docs/backlog/16_milestone_06_integrations.md†L87-L160】
- **Cobertura automatizada:** Plugins externos exigirão suites adicionais (PHP/Node). Incorporar esses comandos em CI sem estourar o tempo de execução é risco moderado. 【F:docs/certification/ACTION_PLAN.md†L24-L63】

## API / documentação divergences

1. Novas integrações ainda não possuem referência em `docs/api/` – definir contrato REST ao abrir M6 para evitar drift entre plugins e backend. 【F:docs/backlog/16_milestone_06_integrations.md†L87-L160】
2. Métricas `integration_*` precisam ser adicionadas ao guia de observabilidade assim que implementadas. 【F:docs/security/observability.md†L1-L160】

## Impact

- Milestone 5 pode ser demonstrada com pytest + smokes + Postman, liberando o time para focar nas integrações da M6.
- Operações contam com evidências recentes e instruções claras no `docs/AGENTE.md` para reproduzir o gate de billing.
- Próxima iteração deve priorizar automações para Woo/Shopify, mantendo o mesmo rigor de evidências (≤512 KB) e métricas de baixa cardinalidade. 【F:docs/AGENTE.md†L40-L120】【F:docs/certification/CHECKLIST.md†L1-L34】
