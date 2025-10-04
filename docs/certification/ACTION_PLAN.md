# ACTION_PLAN – Milestone 8 (Launch Readiness)

## Objetivo Geral
Preparar a plataforma para GA consolidando observabilidade, runbooks e QA final após o shipment de webhooks Stripe.

## Observabilidade & Operações
- Construir dashboards/alertas para as métricas chave (`webhooks_*`, `billing_*`, `integrations_*`, `decision_latency_ms`).
- Documentar procedimentos em `docs/observability.md` e `docs/security/incident-response.md` para responder a quedas/dlq.
- Definir estratégia de retenção/limpeza para `processed_webhooks` (TTL, job oportunista) e registrar em runbooks.

## Billing & Webhooks
- Exercitar cenários de reversals/entitlements end-to-end (assinatura cancelada, pagamento falho, replay) usando fixtures/smokes + Postman.
- Validar que relatórios/analytics refletem corretamente eventos processados e DLQ (capturar evidências adicionais).
- Automatizar checklist de replay (`make webhooks-smoke` + script CLI) e anexar logs truncados.

## QA & Evidências
- Rodar `pytest -q` + `make full-validation` com ênfase em `webhooks-smoke`/`integrations-smoke`.
- Atualizar evidências (`webhooks_smoke.txt`, `metrics_dump.txt`, `api_logs.txt`, `newman_webhooks.txt`) ≤512 KB.
- Consolidar matriz de testes em `docs/certification/CHECKLIST.md` marcando Gates M8.

## Documentação
- Atualizar `STATUS.md`, `README.md` (seção Operações), `docs/billing/stripe.md` (runbook de replay) e `docs/security/observability.md` com artefatos finais.
- Registrar riscos/resoluções em `docs/certification/CONSISTENCY_PATCH.md`.
- Preparar nota de release com instruções de produção (rollout/rollback) e anexos de evidência.

## Definition of Done
1. Dashboards/alertas configurados e documentados (capturar comandos/prints ≤512 KB).
2. Evidências de QA final anexadas (`pytest.txt`, `full_validation.txt`, `webhooks_smoke.txt`, `metrics_dump.txt`, `api_logs.txt`, `newman_webhooks.txt`).
3. Documentação alinhada (README, STATUS, backlog M8, observability, incident response, AGENTE).
4. Consistency patch atualizado listando sincronia entre docs ↔ código ↔ tooling.
5. Plano de lançamento (deploy, rollback, suporte) descrito em `docs/certification/DECISION.md`/`ACTION_PLAN.md` pronto para auditoria.
