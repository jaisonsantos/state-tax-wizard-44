# Consistency Patch Log – Pós-M7

## Divergências sanadas
- `STATUS.md`, backlog M7, API docs e guia HMAC agora descrevem webhooks outbound Taxo, catálogo completo e próximos passos (M8 Launch). 【F:STATUS.md†L1-L200】【F:docs/backlog/17_milestone_07_webhooks.md†L1-L160】【F:docs/webhooks/README.md†L1-L80】
- Postman (pasta "Webhooks"), smoke test (`--webhooks-only`) e Makefile (`webhooks-smoke`) foram alinhados ao novo contrato `X-Taxo-*`. 【F:docs/postman/state-tax-wizard.postman_collection.json†L1850-L2140】【F:backend/smoke_test.py†L838-L969】【F:Makefile†L60-L90】
- `docs/observability.md`, runbooks e launch assets agora referenciam métricas `webhooks_delivery_*`, DLQ, e runbook de rotação.
- Certificação (`DECISION.md`, `ACTION_PLAN.md`, `CHECKLIST.md`) atualizada para marcar M7=PASS e iniciar M8 Init.

## Pendências residuais (acompanhar na próxima rodada)
1. Capturar métricas reais de um ambiente com Prometheus (`curl $METRICS_URL | grep webhooks`) para substituir nota SKIP em `metrics_dump.txt`.
2. Executar `make webhooks-smoke` em ambiente com Docker Compose e anexar evidência completa (script manual disponível).
3. Adicionar captura de tela/UI para `docs/webhooks/configuration.md` quando front-end puder ser executado no ambiente.
4. Validar pipeline CI atualizado (job Newman + smoke) após orquestração M8.
