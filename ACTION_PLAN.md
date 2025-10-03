# Action Plan – Milestone 6 (Platform Integrations Alpha)

Este documento resume os pilares da próxima iteração e aponta para o plano operacional detalhado em `docs/certification/ACTION_PLAN.md`.

## Objetivo

Entregar conectores oficiais para WooCommerce e Shopify que consumam `/v1/fees/*` com HMAC, exponham métricas `integration_*`, e mantenham a certificação da Milestone 5 intacta (pytest, smokes, Postman). 【F:docs/certification/ACTION_PLAN.md†L1-L73】【F:docs/backlog/16_milestone_06_integrations.md†L1-L160】

## Trilhas principais

1. **Backend & Observabilidade** – Expor endpoints auxiliares (`/v1/integrations/*`), registrar métricas `integration_requests_total`/`integration_failures_total`, e garantir compatibilidade com as migrações existentes. Comandos: `pytest -q`, `alembic upgrade head`, `curl -s $SMOKE_METRICS_URL | grep integration_`. 【F:docs/certification/ACTION_PLAN.md†L8-L33】
2. **Plugins WooCommerce/Shopify** – Implementar plugin PHP e app Remix/Node com suites (`composer test`, `npm run test`), embalando artefatos (`woocommerce-build`, `shopify-build`) para CI. 【F:docs/certification/ACTION_PLAN.md†L34-L63】
3. **Frontend & Docs** – Adicionar seção "Integrations" na UI/admin, atualizar README/Postman, e documentar troubleshooting e métricas. 【F:docs/certification/ACTION_PLAN.md†L64-L73】【F:docs/postman/README.md†L1-L120】

## Riscos e mitigação

- **Dependências externas:** Necessário provisionar chaves Woo/Shopify e ambientes de teste; fallback documentado para executar suites em modo stub. 【F:docs/backlog/16_milestone_06_integrations.md†L87-L160】
- **Tempo de pipeline:** Executar `composer test` + `npm run test` pode alongar CI; usar cache e paralelismo onde possível. 【F:docs/certification/ACTION_PLAN.md†L34-L63】
- **Guardrails existentes:** Manter `docs/certification/CHECKLIST.md` atualizado em cada execução para garantir que regressões de M5 sejam detectadas rapidamente. 【F:docs/certification/CHECKLIST.md†L1-L34】

## Definition of Done

- Build/test dos plugins e endpoints auxiliares documentados com evidências ≤512 KB.
- Métricas `integration_*` expostas e referenciadas em observabilidade/postman.
- Checklist de certificação concluído (todos os gates de M5 + novos gates de M6). 【F:docs/certification/CHECKLIST.md†L1-L34】
