# Action Plan – Milestone 8 (Launch Readiness Init)

Resumo executivo do plano descrito em `docs/certification/ACTION_PLAN.md`. Esta versão destaca pilares, riscos e comandos principais para a próxima rodada de execução.

## Objetivo
Garantir que os webhooks outbound recém-implementados possam ir a produção com observabilidade, suporte e runbooks prontos.

## Trilhas principais
1. **Backend & Webhooks** – Ensaiar deploy/rollback, automatizar `python backend/smoke_test.py --webhooks-only`, e registrar processo de rotação emergencial de segredo. Comandos: `pytest -q`, `poetry run alembic upgrade head`, `python backend/smoke_test.py --webhooks-only`.
2. **Observabilidade** – Publicar dashboards/alertas (`webhooks_delivery_*`) conforme `docs/observability.md`, capturar métricas reais (`curl $METRICS_URL | grep webhooks`).
3. **Postman/QA** – Rodar Newman para pasta "Webhooks", anexar relatórios ≤512 KB, manter README alinhado.
4. **Suporte & Comunicação** – Finalizar playbook (`docs/SUPPORT_PLAYBOOK.md`), templates de status page e matriz de severidade.
5. **Governança** – Atualizar `docs/launch/GO_LIVE_CHECKLIST_M8.md`, `docs/SLO.md`, revisar backlog M8 (`docs/backlog/18_milestone_08_launch.md`).

## Riscos e mitigação
- **Falta de stack Prometheus/Grafana:** documentado como SKIP; priorizar provisionamento antes do go-live.
- **Dependência de Docker para smokes:** alternativa CLI (`python backend/smoke_test.py --webhooks-only --capture-server ...`).
- **Coordenação multi-times (EngOps/Support/Product):** usar ritos descritos na checklist (daily sync, go/no-go).

## Definition of Done
- Dashboards e alertas configurados; captura de métricas anexada.
- Smokes/Newman executando em CI com evidências recentes.
- Runbooks e playbook de suporte aprovados pelos owners.
- Checklist M8 (`docs/certification/CHECKLIST.md`) marcado 100%.
