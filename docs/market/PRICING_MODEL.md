# Modelo de Preços – State Tax Wizard

> Fonte de verdade para estratégia comercial, benefícios por tier e políticas de uso.

## Estratégia
- **Modelo:** adoption-first – planos acessíveis para acelerar ativações e migrar para tier superior via automação.
- **Moeda:** USD.
- **Grace de uso:** alertar a partir de **80%** do limite mensal; bloqueio duro somente ao atingir 100% (exceto ambientes `APP_ENV=dev`).
- **Overage:**
  - **Free / Starter / Pro / Plus:** sem overage – bloqueio ao atingir o limite.
  - **Enterprise:** consumo acima do commit é permitido; registramos métrica `enterprise_overage_total{plan}` e reconciliamos manualmente.

## Tabela resumida

| Plano (key) | Preço mensal | Preço anual | Limite de entregas | Overage | Principais benefícios |
| --- | --- | --- | --- | --- | --- |
| Free / Dev (`free`) | USD 0 | USD 0 | Até 20/mês | Não aplicável | CO/MN cálculo básico, dashboard, suporte comunidade |
| Starter (`starter`) | USD 10 | USD 100 | Até 100/mês | Não | Cálculo & aplicação automática, updates, relatório mensal, suporte e-mail D+1 |
| Pro (`pro`) | USD 29 | USD 290 | Até 1.000/mês | Não | Tudo do Starter + CSV avançado, Webhooks/API, suporte prioritário |
| Plus (`plus`) | USD 79 | USD 790 | Até 5.000/mês | Não | Tudo do Pro + Multi-store, onboarding assistido, SLA |
| Enterprise 10k (`enterprise_e10k`) | USD 149 | USD 1.484,04 | Commit 10.000/mês | USD 0,02 por entrega | Tudo do Plus + acompanhamento dedicado, overage monitorado |
| Enterprise 25k (`enterprise_e25k`) | USD 299 | USD 2.978,04 | Commit 25.000/mês | USD 0,015 por entrega | Escalonamento para redes médias, governança compartilhada |
| Enterprise 50k (`enterprise_e50k`) | USD 499 | USD 4.970,04 | Commit 50.000/mês | USD 0,01 por entrega | Enterprise completo com SLA estendido e playbook customizado |

## Regras operacionais
- **Alertas de uso:**
  - API `/v1/billing/usage` expõe `warn_threshold_pct` e `warnings[]` quando ≥80% do limite. Métrica `entitlement_warnings_total{plan}` alimenta dashboards.
  - Frontend exibe barra de progresso + callout para avisos; bloqueio dispara modal sugerindo upgrade.
- **Bloqueio:** `EntitlementService.enforce_transaction_limit()` retorna `403 transaction_limit_exceeded` (exceto em `APP_ENV=dev`, onde apenas registra log).
- **Enterprise:** consumo acima do commit gera log estruturado e incrementa `enterprise_overage_total{plan}`; cobrança feita fora do ciclo automático (M9: Stripe usage / Shopify usage charge).
- **Stripe:** price IDs são configuráveis via variáveis de ambiente: `STRIPE_PRICE_ID_STARTER`, `STRIPE_PRICE_ID_PRO`, `STRIPE_PRICE_ID_PLUS`, `STRIPE_PRICE_ID_E10K`, `STRIPE_PRICE_ID_E25K`, `STRIPE_PRICE_ID_E50K`. Ausência → `503 billing_unconfigured` nos endpoints de checkout/portal.

## Referências
- API contracts atualizados em [`docs/api/billing.md`](../api/billing.md).
- Observabilidade (`entitlement_warnings_total`, `enterprise_overage_total`) documentada em [`docs/observability.md`](../observability.md).
- Procedimentos Stripe e variáveis `.env` em [`docs/billing/stripe.md`](../billing/stripe.md).
