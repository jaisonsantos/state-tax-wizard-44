# ACTION PLAN – Milestone 8 (Launch Readiness Init)

> Escopo "no-code" consolidado após certificação da M7. Objetivo: preparar go-live seguro (observabilidade, operações, suporte, documentação) antes da rodada de execução.

## 1. Backend & Webhooks
- **Objetivo:** validar que as rotas e serviços recém-implementados permanecem estáveis em produção.
- **Ações:**
  - Publicar guia de deploy/rollback (`docs/launch/RUNBOOKS.md`) e registrar pré-requisitos (`alembic upgrade head`, variáveis `SMOKE_HMAC_SECRET`, `WEBHOOK_CAPTURE_URL`).
  - ✅ Automatizar smoke `python backend/smoke_test.py --webhooks-only` em ambiente CI (job `Backend CI / smoke-newman`) com `pytest -q` como pré-cheque.
  - Definir procedimento de rotação emergencial do HMAC (script + atualização imediata do endpoint) e registrar em runbook.
- **Comandos chave:** `pytest -q`, `poetry run alembic upgrade head`, `python backend/smoke_test.py --webhooks-only`.
- **Riscos:** ausência de Docker em ambientes locais → documentar alternativa com `uvicorn` + servidor de captura manual.
- **DoD:** evidências dos smokes, runbook publicado, owners atribuídos.

## 2. Frontend & Admin
- **Objetivo:** garantir que operadores consigam configurar webhooks com confiança.
- **Ações:**
  - Atualizar guia de UI/settings (`docs/webhooks/configuration.md`) com screenshots/simulações de cada toggle.
  - Verificar que `src/lib/api.ts` inclui novos endpoints (`/v1/webhooks/events`, replay) e documentar uso em Postman.
  - Especificar fallback UX quando `webhook_active=false` ou endpoint vazio (mensagem de alerta).
- **Comandos chave:** `npm run lint`, `npm run build` (ensaios), `pnpm playwright test` (opcional).
- **Riscos:** falta de ambiente front-end; mitigação com mock API via MSW.
- **DoD:** documentação UI atualizada + checklist QA manual para Settings.

## 3. Observabilidade & Metrics
- **Objetivo:** alinhar métricas/alertas a SLOs definidos.
- **Ações:**
  - ✅ Mapear métricas `webhooks_delivery_total`, `webhooks_delivery_seconds`, `webhooks_failed_total`, `webhooks_dead_letter_total` para dashboards (queries em `docs/observability.md` + JSON exportado).
  - ✅ Especificar alertas: P95 >5s por 5 min, falhas consecutivas >3, DLQ >0 por >15 min (`docs/observability/prometheus_alerts_webhooks.yaml`).
  - ✅ Adicionar seção no runbook com passos para coleta manual (`curl $METRICS_URL | grep webhooks`).
- **Comandos chave:** `make metrics-dump` (quando Docker disponível) ou instrução manual.
- **Riscos:** stack Prometheus não provisionado → manter SKIP documentado.
- **DoD:** dashboards/alertas descritos, métricas documentadas em SLO. ✅

## 4. Postman & QA
- **Objetivo:** assegurar cobertura automatizada dos fluxos novos.
- **Ações:**
  - ✅ Atualizar coleção com pasta "Webhooks" (list, replay, inválido, stale, replay) e scripts de assinatura `X-Taxo-*`; testes validam presença de eventos antes do replay.
  - ✅ Criar documentação em `docs/postman/README.md` detalhando preparo do ambiente (captura server, secrets) e execução em CI.
  - ✅ Adicionar passo no CHECKLIST para rodar `newman run ... --folder "Webhooks"`.
- **Comandos chave:** `newman run docs/postman/state-tax-wizard.postman_collection.json --folder Webhooks`.
- **Riscos:** Newman sem Node ≥18 → registrar no README.
- **DoD:** execução Newman registrada e sem falhas críticas (automatizada na pipeline). ✅

## 5. Documentation & Certification
- **Objetivo:** manter alinhamento repo ↔ docs.
- **Ações:**
  - Atualizar `STATUS.md`, backlog M7/M8, `docs/webhooks/*`, `docs/launch/*`, `docs/SLO.md` conforme evoluções.
  - Manter `docs/certification/CHECKLIST.md` marcado por rodada; criar `CONSISTENCY_PATCH.md` sempre que detectar desvio.
  - Publicar `docs/AGENTE.md` com plano executável para próxima rodada (feito) e preparar nota "quando autorizar executar".
- **Comandos chave:** `rg "Stripe" docs -g"*.md"` para varredura anti-drift.
- **Riscos:** deriva documental; mitigar com revisões cruzadas.
- **DoD:** todos os artefatos atualizados e referenciados na decisão.

## 6. Integrations / Partner Success
- **Objetivo:** preparar conectores externos para consumir novos webhooks.
- **Ações:**
  - Registrar no backlog das integrações o endpoint e catálogo (Shopify/WooCommerce) com timeline M8+.
  - Garantir que SDK TypeScript ofereça helpers para assinatura/verificação (TODO em rodada futura).
- **Comandos chave:** `npm run test --workspace integrations/sdk` (verificação futura).
- **Riscos:** escopo além de M8 – sinalizar dependências.
- **DoD:** backlog atualizado com dependências e responsáveis.

## 7. Compliance & Support
- **Objetivo:** alinhar SLO/SLA com suporte nível 1.
- **Ações:**
  - Completar `docs/SUPPORT_PLAYBOOK.md` com macros (ticket, chat) e matriz de severidade.
  - Documentar escalonamento (Suporte → EngOps) com tempos máximos.
- **Comandos chave:** N/A (documentação).
- **DoD:** playbook publicado, SLO referenciado.

## 8. Rollback & Business Continuity
- **Objetivo:** assegurar que falhas em produção possam ser revertidas rapidamente.
- **Ações:**
  - Detalhar rollback parcial (desativar `webhook_active`) x rollback total (reverter deploy) no runbook.
  - Especificar script para migrar eventos DLQ para reprocessamento pós-rollback.
- **DoD:** seção "Rollback" completa em `docs/launch/RUNBOOKS.md`.

> **Saída esperada da próxima rodada:** executar plano acima (código/infra), coletar evidências (`pytest`, smokes, Newman), marcar checklist e abrir PR `Launch – Execute M8 Init`.
