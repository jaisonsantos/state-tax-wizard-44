# ACTION_PLAN – Milestone 6 (Platform Integrations Alpha)

## Objetivo Geral
Entregar conectores oficiais para WooCommerce e Shopify que consumam os endpoints `/v1/fees/*` com HMAC, registrem métricas e exponham experiências administrativas alinhadas ao backend. Todo o trabalho deve preservar a certificação de M5 (migrar/rodar smokes) e manter documentação/tooling sincronizados.

## Backend
- **WooCommerce Webhook Support**
  - Expor endpoint opcional `/v1/integrations/woocommerce/order` para receber callbacks pós-checkout (idempotente).
  - Comandos: `pytest -q backend/tests/test_integrations_woocommerce.py` (novo), `python smoke_test.py --security-only`.
  - Riscos: validação duplicada de HMAC (WooCommerce usa chave compartilhada distinta). Mitigação: reusar `enforce_hmac` com cabeçalhos dedicados.
  - Rollback: desabilitar rota via feature flag (`INTEGRATIONS_WOO_ENABLED=false`).
- **Shopify Fee Product Helper**
  - Expor utilitário REST `/v1/integrations/shopify/fee-products` para listar/criar produto de fee.
  - Comandos: `pytest -q backend/tests/test_integrations_shopify.py` (novo), `alembic upgrade head` (no-op confirm).
  - Riscos: limites de rate limit Shopify → adicionar retries exponenciais.

## Frontend
- **Admin UI para credenciais de integrações**
  - Adicionar seção "Integrations" em `src/pages/Settings.tsx` listando chaves HMAC, store ID, instruções de plugin.
  - Comandos: `npm run lint`, `npm run build`.
  - Riscos: poluir UI existente; usar feature flag `VITE_ENABLE_INTEGRATIONS`.
  - DoD: instruções copiáveis + link para downloads dos plugins.

## Integrations (WooCommerce)
- Estruturar diretório `integrations/woocommerce/` conforme plano do backlog.
- Implementar classes `FeeCalculator`, `OrderSync`, `Settings` com testes PHPUnit (`composer test`).
- Comandos: `composer install`, `composer test`, `npm run lint` (se usar JS assets).
- Riscos: compatibilidade com versões antigas do WooCommerce; definir suporte oficial (WC 8.0+).
- Rollback: plugin permanece opcional; basta não publicar ZIP.

## Integrations (Shopify)
- Criar app Remix (`integrations/shopify/app/`).
- Configurar `npm install`, `npm run test`, `npm run dev` (local tunnel).
- Garantir que app proxy chama backend com HMAC.
- Riscos: limites de app proxy; validar fallback (graceful skip) quando API indisponível.
- Rollback: revogar app no Shopify Partner dashboard, remover webhook subscriptions.

## Seeds & Data
- Atualizar `backend/seed_data.py` para incluir instruções/links de download nas mensagens de console.
- Comandos: `DATABASE_URL=<...> python backend/seed_data.py`.
- Riscos: poluição de logs; manter mensagens ≤2 linhas.

## Observability
- Adicionar métricas `integration_requests_total{platform,route}` e `integration_failures_total{platform,reason}` em `backend/app/observability.py`.
- Comandos: `curl -s $SMOKE_METRICS_URL | grep integration_`.
- Riscos: cardinalidade – limitar labels a `platform`, `route`, `reason` fixo.

## Docs
- Atualizar `README.md`, `docs/backlog/16_milestone_06_integrations.md`, `docs/integrations/woocommerce.md`, `docs/integrations/shopify.md` (novos) com instalação, troubleshooting e métricas.
- Comandos: `markdownlint docs/integrations/*.md` (se disponível) ou `npm run lint-docs`.

## Postman
- Acrescentar coleção "Integrations" com exemplos de assinatura Woo/Shopify (`docs/postman/state-tax-wizard.postman_collection.json`).
- Comandos: `npm run postman:test` (ou `newman run ...`).
- Riscos: manter corpos idênticos aos plugins.

## QA & CI
- Estender Makefile com alvos `woocommerce-build`, `shopify-build`, `integrations-smoke` (mocking API).
- Atualizar pipeline CI para executar `pytest -q`, `npm run build`, `composer test`, `npm run test` (Shopify).
- Riscos: tempo de pipeline ↑; usar caches (`actions/cache`).

## Definition of Done
1. Backend integrações (WooCommerce + Shopify helpers) com testes e métricas.
2. Plugins compilam, passam testes locais e têm documentação oficial.
3. UI/Docs/Postman atualizados com instruções completas.
4. Makefile/CI executam fluxo end-to-end (build + testes + lint) e publicam evidências ≤512 KB.
5. `docs/certification/CHECKLIST.md` marcado com Gates M6 (a definir) e regressões zero em M5.
