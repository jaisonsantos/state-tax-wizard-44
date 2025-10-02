# MVP Release Plan — Iterative Milestones

Este plano organiza os épicos em incrementos entregáveis. Cada milestone dura ~1–2 sprints (≈2 semanas) e deve cumprir a **Definition of Done** em `docs/backlog/11_iteration_checklist.md` antes de ser fechado.

> Convenções: sempre que um milestone menciona migração, feature flag ou variável de ambiente, a operação/rollback deve estar documentada em `docs/security/environment.md` e nas notas de release.

---

## Milestone 0 — Foundations (Week 0)

- ✅ Epic 01 concluído (`docs/security/environment.md`, `docs/security/data-model.md`, `docs/security/observability.md`, `make smoke`).
- Rituais de engenharia e checklist de PR definidos.

## Milestone 1 — Secure Core APIs (Weeks 1–2)

- Epic 02 (auth/tenant) entregue.
- ✅ Store settings (Epic 03) via `/v1/stores/{id}/settings`.
- Frontend (Epic 05) usando claims de auth para seletor de loja.
- ✅ Sessões persistidas em `session_tokens`, logout com revogação, menu de conta exposto.

## Milestone 2 — Reporting Confidence (Weeks 3–4)

- ✅ Telemetria de export (Epic 04) + auditoria (`report_export`) + métricas.
- ✅ MN/CO: CSV/JSON, nomes de anexos por cabeçalho, histórico na UI.
- ✅ Playwright/Newman/pytest cobrindo 422, headers e evidências.

## Milestone 3 — Frontend Polish & Analytics (Weeks 5–6)

- ✅ `/v1/analytics/overview` com KPIs, feed com cursor, snapshot de contadores.
- ✅ Dashboard consome analytics; menu de conta mostra metadados de sessão.
- QA: smoke `make analytics-smoke`, testes e2e do dashboard.
- Docs: `docs/api/analytics.md`, `docs/security/ui-guide.md` atualizados.

---

## Milestone 4 — Security & Rate Limiting (Weeks 7–8)

**Escopo (Epic 08)**
- HMAC para chamadas sensíveis (incl. timestamp/nonce) e **replay protection**.
- **Rate limiting** por IP/rota/tenant (limites default + overrides).
- **Security logging** dedicado (auth, assinatura inválida, throttling).
- Playbooks de **secrets management** (rotação, escopos) e hardening de headers.
- Checks de dependências/vuln e gating no CI.

**Entregáveis**
- Middlewares/dep. FastAPI (HMAC, rate limits).
- Métricas/alertas (p95 de rejeições, 429s/min).
- Docs: contrato de assinatura, exemplos e Postman com pre-scripts.

**Exit criteria**
- Testes de relógio desviado/replay + carga de 429.
- Runbook e rollback documentados.

---

## Milestone 5 — Billing & Stripe Integration (Weeks 9–10) ✅

Status: Completed. Evidence and write-up in [`docs/certification/M5_COMPLETION.md`](../certification/M5_COMPLETION.md).

**Escopo (Epic 07)**
- **Customer lifecycle** (criação/sync), **Checkout** e **Billing Portal**.
- **Webhooks Stripe** (invoice/checkout/subscription) em modo seguro.
- **Entitlements**: enforcement no backend por plano, trial, grace-period.
- Faturamento só **test mode** em ambientes não-prod.

**Entregáveis**
- Rotas: `/v1/billing/*`, mapeamentos de IDs (customer/subscription/prod).
- Tabelas/índices para relacionamento e auditoria de eventos.
- Scripts de seed de planos/produtos, Newman collection para fluxo end-to-end.
- Métricas: `billing_events_total`, latência de webhook, falhas por tipo.

**Exit criteria**
- Fluxo: login → checkout → entitlement → portal → cancel/renew validado.
- Reprocessamento idempotente de webhooks e evidências em CI.

---

## Milestone 6 — Platform Integrations Alpha (Weeks 11–12)

**Escopo (Epic 06)**
- **WooCommerce plugin** (admin, store-key, mapeamento de carrinho).
- **Shopify app POC** (limitations: sem Plus → via app proxy/Function).
- **Integration SDK** (JS/TS) com helpers de assinatura e retries.

**Entregáveis**
- Pacotes versionados, guias de instalação, exemplos de payloads.
- Mocks para DevStores + scripts de geração de ordem fake.

**Exit criteria**
- Demonstração dos dois fluxos registrando audit logs e métricas.
- QA de compatibilidade (versões mínimas, lojas demo).

---

## Milestone 7 — Webhooks & Order Lifecycle (Weeks 13–14)

**Escopo (Epic 09)**
- Infra de **webhooks de pedidos** (emitir/consumir), **reversals** e **cancellations**.
- **Idempotency** nos endpoints de lifecycle e reconciliação.
- Alinhamento de **reporting** (reversals visíveis em CSV/JSON e analytics).

**Entregáveis**
- Tabela de eventos pendentes/falhos + job de retry/backoff.
- Schemas de eventos, assinatura (HMAC) e exemplos.
- Métricas/alertas: fila, DLQ, taxa de retry, sucesso por tipo.

**Exit criteria**
- Simulação com falhas transitórias e recuperação auditável.
- Relatórios espelham reversals dentro da janela.

---

## Milestone 8 — Production Readiness & Launch (Weeks 15–16)

**Escopo**
- Infra & observability (dashboards, logs centralizados, backups).
- **Performance & load** (metas p95/p99), hardening de segurança e revisão externa.
- Documentação final (Runbooks, UI guide, API reference), **beta** com clientes piloto e **GA**.

**Entregáveis**
- Checklist de go-live, DR, RPO/RTO, alerts críticos.
- Playbooks de incidentes, SLOs e relatórios de capacidade.

**Exit criteria**
- Execução de dry-run de release, rollback testado, beta OK.
- Aprovação de segurança e conformidade, liberação do GA.

---

## Notas de Planejamento

- Cada milestone deve encerrar com **demo, revisão de stakeholders e atualização dos docs** (linkando PRs, evidências e métricas).
- Itens que “escaparem” são reprojetados no próximo milestone com critério claro de aceitação.
