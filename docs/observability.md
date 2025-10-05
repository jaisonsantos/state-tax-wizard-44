# Observability Playbook – Webhooks Launch

## 1. Dashboards
O painel **"Taxo – Webhooks"** foi publicado e versionado em `docs/observability/webhooks_dashboard.json`. O arquivo contém a exportação completa do Grafana (UID `taxo-webhooks`) com os componentes abaixo:

- **Delivery Success Rate** – `sum(rate(webhooks_delivery_total{status="delivered"}[5m])) / sum(rate(webhooks_delivery_total[5m]))` (limite amarelo <99.7%, vermelho <99.5%).
- **Delivery Latency (p95)** – `histogram_quantile(0.95, sum(rate(webhooks_delivery_seconds_bucket[5m])) by (le, event))` com meta <5s e quebras por `event`.
- **Failures by Reason** – tabela `increase(webhooks_failed_total[5m])` com colunas `event`, `reason`, `store_id`.
- **Dead Letters** – gráfico `increase(webhooks_dead_letter_total[5m])` e tabela de eventos pendentes (`webhook_events{status="dead_letter"}`).
- **Attempt Timeline** – barras empilhadas com `increase(webhook_delivery_attempts_total[5m])` para identificar backoff.
- **Related Counters** – `rate(fees_applied_total[5m])`, `rate(report_exports_total[5m])`, `rate(billing_events_total[5m])` para correlação cross-domain.

O JSON exportado inclui variáveis de ambiente (`$datasource`, `$environment`) para reaproveitamento entre staging/produção. Após importar no Grafana, atualize apenas o datasource Prometheus e o folder destino.

## 2. Alertas Prometheus
O arquivo `docs/observability/prometheus_alerts_webhooks.yaml` consolida as regras abaixo prontas para inclusão no Prometheus (compatível com Alertmanager v0.27+):

- **TaxoWebhookLatencyP95High** – dispara em 5m consecutivos com p95 >5s; severidade `warning`.
- **TaxoWebhookDeliveryErrors** – dispara quando `increase(webhooks_failed_total[10m]) > 0`; severidade `critical`.
- **TaxoWebhookDeadLetter** – dispara quando `increase(webhooks_dead_letter_total[15m]) > 0`; severidade `critical` com instruções de replay.

As regras usam o rótulo `service="taxo-api"` para facilitar roteamento no Alertmanager. Ajuste o namespace conforme ambiente.

## 3. Retenção & Manutenção
- `webhook_events`: manter histórico 30 dias para auditoria. Criar job semanal removendo `status='delivered'` com `updated_at < NOW() - 30d`.
- `webhook_delivery_attempts`: manter 14 dias ou até extração para data warehouse.
- Expor métricas de limpeza (`webhooks_cleanup_deleted_total`).

## 4. Evidence Capture
- `make metrics-dump` (ou `curl -s $METRICS_URL | grep webhooks`) antes de cada release; anexar saída atualizada a `docs/certification/EVIDENCE/metrics_dump.txt`. O job `Backend CI / smoke-newman` executa automaticamente `curl http://127.0.0.1:8000/metrics` e publica o artefato `metrics-webhooks.txt`.
- `python backend/smoke_test.py --webhooks-only` gera logs e payloads (consulte `docs/certification/EVIDENCE/webhooks_smoke.txt`). A mesma execução roda em CI logo após os testes unitários.
- Postman/Newman (`--folder Webhooks`) produz relatório CLI; o pipeline salva o sumário em `docs/certification/EVIDENCE/newman_webhooks.md` (≤512 KB) sempre que a branch principal é atualizada.

## 5. Runbooks Relacionados
- [`docs/webhooks/runbook.md`](docs/webhooks/runbook.md) – incidentes, replay, rotação HMAC.
- [`docs/launch/RUNBOOKS.md`](docs/launch/RUNBOOKS.md) – deploy/rollback.
- [`docs/SUPPORT_PLAYBOOK.md`](docs/SUPPORT_PLAYBOOK.md) – comunicação ao cliente.

## 6. Anti-drift / Checks
- `rg "Stripe" backend/app/observability.py` → garantir que painéis não dependem mais de provider stripe-only.
- Validar que `webhooks_delivery_total` possui labels fixos (`event`, `status`) evitando cardinalidade alta.
- Monitorar uso de `log_webhook_delivery` para evitar logar payloads completos (somente IDs/erros truncados).

Com dashboards, alertas e runbooks alinhados ao novo serviço, o lançamento pode avançar para ensaio em produção (M8).

## 7. Billing telemetry
- `entitlement_warnings_total{plan}` – incrementado sempre que `/v1/billing/usage` retorna `warnings[]` (≥80% do limite). Útil para campanhas pró-upgrade.
- `entitlement_denials_total{feature,plan}` – já existente; continua registrando bloqueios `transaction_limit_exceeded` (exceto `APP_ENV=dev`).
- `enterprise_overage_total{plan}` – aumenta quando stores enterprise excedem o commit; correlacionar com `billing_events_total{event="enterprise_overage_detected"}`.
- Exemplos de consulta:
  - `increase(entitlement_warnings_total[1d])` – hotspots de uso próximo ao limite.
  - `increase(enterprise_overage_total[1d]) by (plan)` – clientes que demandam upgrade de commit.
  - `rate(billing_events_total{event=~"checkout_session_created|checkout_session_returned"}[5m])` – funil de upgrade.
