# ACTION_PLAN – Milestone 6 (Integrations Alpha)

## Objetivo Geral
Entregar conectores de integração (WooCommerce + Shopify) sustentados por SDKs e métricas compartilhadas, mantendo a estabilidade conquistada em M5. O trabalho deve sair de um branch dedicado (`feature/m6-integrations-alpha-2025-10-04`) e preservar o checklist de certificação (`docs/certification/CHECKLIST.md`).

## Billing & Core Backend
- **Garantir compatibilidade**: monitorar impactos do plugin/app sobre `/v1/fees/*`, `/v1/billing/*` e segurança HMAC.
- **Comandos**: `pytest -q`, `pytest -q backend/tests/test_integrations_*` (novos).
- **Riscos**: aumento de carga em `/v1/fees/apply`; mitigar com testes de carga leves e alertas (`rate_limit_throttles_total`).
- **Rollback**: feature flags (`INTEGRATIONS_WOO_ENABLED`, `INTEGRATIONS_SHOPIFY_ENABLED`) desligadas + rollback do deploy.

## WooCommerce Plugin
- Criar diretório `integrations/woocommerce/` (plugin PHP) com hooks para `woocommerce_cart_calculate_fees` e `woocommerce_checkout_order_processed`.
- Implementar cliente HMAC usando contrato `timestamp\nnonce\nbody` e métricas locais.
- **Comandos**: `composer install`, `composer test`, `npm run lint` (se usar assets).
- **Entrega**: ZIP empacotado (`package.sh`) + README detalhando instalação, configuração (`store_id`, `hmac_secret`) e troubleshooting.
- **Riscos**: compatibilidade com WooCommerce < 8.0; documentar suporte mínimo e fallback.

## Shopify App POC
- Aplicativo Remix/Node em `integrations/shopify/` com app proxy (`/apps/tax-wizard/quote`) e webhook `orders/create`.
- Sincronizar "fee product" oculto, chamar `/v1/fees/apply`, registrar metafields.
- **Comandos**: `npm install`, `npm run lint`, `npm run test`, `shopify app dev` (documentar saída/variáveis).
- **Riscos**: limite de taxa de app proxy; implementar retries com `Retry-After` e logar falhas para `integration_failures_total`.

## Shared SDK / Tooling
- Criar `integrations/sdk/typescript` com cliente HMAC reutilizável (exportado para Woo/Shopify).
- Publicar pacote npm privado (ou tarball) + docs de consumo.
- Atualizar Postman com folder "Integrations" (payloads Woo/Shopify) e scripts de assinatura.
- Atualizar Makefile com metas `woocommerce-build`, `shopify-build`, `integrations-smoke`.

## Observability & Metrics
- Adicionar contadores `integration_requests_total{platform,route}` e `integration_failures_total{platform,reason}` no backend (`backend/app/observability.py`).
- Expandir `/metrics` evidenciado em `docs/certification/EVIDENCE/metrics_dump.txt`.
- Documentar novos sinais em `docs/security/observability.md`.

## QA & Evidence
- Atualizar `docs/certification/CHECKLIST.md` com gates M6 (integrations code, sdk, metrics, docs, smokes, Newman).
- Executar `pytest -q`, `python smoke_test.py --analytics-only/--reports-only/--security-only`, `python smoke_test.py --billing-only` (SKIP aceitável sem Stripe), `integrations-smoke` (novo) com backends simulados.
- Capturar novas evidências (`api_logs.txt`, `migrate.txt`, `pytest.txt`, smokes, `metrics_dump.txt`, `md_index.txt`) sem exceder 512 KB.

## Documentação
- Atualizar `README.md`, `STATUS.md`, backlog M6, `docs/integrations/woocommerce.md`, `docs/integrations/shopify.md` (novos) e `docs/postman/README.md`.
- Registrar riscos/rollback por camada em `docs/certification/DECISION.md` (próxima rodada) e manter `CONSISTENCY_PATCH.md` sincronizado.

## Definition of Done
1. Plugins WooCommerce & Shopify entregam fluxo completo (instalação, assinatura HMAC, logs, rollback) com testes automatizados onde aplicável.
2. SDK compartilhado (TS) publicado e consumido pelos conectores.
3. Métricas `integration_*` disponíveis em `/metrics` e documentadas.
4. Makefile/CI executam build/test lint das integrações e coletam evidências.
5. `docs/certification/CHECKLIST.md` (M6) totalmente marcado e evidência ≤512 KB arquivada.
