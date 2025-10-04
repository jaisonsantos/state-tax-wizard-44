# Observability Playbook – Webhooks Launch

## 1. Dashboards
Crie painel Grafana "Taxo – Webhooks" com os componentes abaixo:

- **Delivery Success Rate** – `sum(rate(webhooks_delivery_total{status="delivered"}[5m])) / sum(rate(webhooks_delivery_total[5m]))` (threshold 99.5%).
- **Delivery Latency (p95)** – `histogram_quantile(0.95, sum(rate(webhooks_delivery_seconds_bucket[5m])) by (le, event))` (meta <5s) com legenda por `event`.
- **Failures by Reason** – tabela `increase(webhooks_failed_total[5m])` com colunas `event`, `reason` (esperado: `missing_endpoint`, `missing_hmac_secret`, `http_error`).
- **Dead Letters** – tabela de `webhook_events{status="dead_letter"}` e painel com `increase(webhooks_dead_letter_total[5m])` por `event`.
- **Attempt Timeline** – gráfico de barras `increase(webhook_delivery_attempts_total[5m])` (derive de logs ou use contagem de `attempts_log`).
- **Related Counters** – `rate(fees_applied_total[5m])`, `rate(report_exports_total[5m])`, `rate(billing_events_total[5m])` para correlação.

Armazene o JSON do dashboard no repositório de monitoramento e referencie o link aqui quando disponível.

## 2. Alertas Prometheus (exemplo)
```yaml
- alert: TaxoWebhookLatencyP95High
  expr: histogram_quantile(0.95, sum(rate(webhooks_delivery_seconds_bucket[5m])) by (le)) > 5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Webhook delivery latency above 5s"
    description: "Check capture endpoint availability and DLQ backlog."

- alert: TaxoWebhookDeliveryErrors
  expr: increase(webhooks_failed_total[10m]) > 0
  for: 10m
  labels:
    severity: critical
  annotations:
    summary: "Webhook delivery failures detected"
    description: "Inspect /v1/webhooks/events?status=pending and contact merchant if endpoint misconfigured."

- alert: TaxoWebhookDeadLetter
  expr: increase(webhooks_dead_letter_total[15m]) > 0
  for: 15m
  labels:
    severity: critical
  annotations:
    summary: "Webhook events stuck in DLQ"
    description: "Follow docs/webhooks/runbook.md to replay or disable temporarily."
```

## 3. Retenção & Manutenção
- `webhook_events`: manter histórico 30 dias para auditoria. Criar job semanal removendo `status='delivered'` com `updated_at < NOW() - 30d`.
- `webhook_delivery_attempts`: manter 14 dias ou até extração para data warehouse.
- Expor métricas de limpeza (`webhooks_cleanup_deleted_total`).

## 4. Evidence Capture
- `make metrics-dump` (ou `curl -s $METRICS_URL | grep webhooks`) antes de cada release; anexar saída a `docs/certification/EVIDENCE/metrics_dump.txt`.
- `python backend/smoke_test.py --webhooks-only` gera logs e payloads (consulte `docs/certification/EVIDENCE/webhooks_smoke.txt`).
- Postman/Newman (`--folder Webhooks`) produz relatório JSON; anexar sumário ≤512 KB.

## 5. Runbooks Relacionados
- [`docs/webhooks/runbook.md`](docs/webhooks/runbook.md) – incidentes, replay, rotação HMAC.
- [`docs/launch/RUNBOOKS.md`](docs/launch/RUNBOOKS.md) – deploy/rollback.
- [`docs/SUPPORT_PLAYBOOK.md`](docs/SUPPORT_PLAYBOOK.md) – comunicação ao cliente.

## 6. Anti-drift / Checks
- `rg "Stripe" backend/app/observability.py` → garantir que painéis não dependem mais de provider stripe-only.
- Validar que `webhooks_delivery_total` possui labels fixos (`event`, `status`) evitando cardinalidade alta.
- Monitorar uso de `log_webhook_delivery` para evitar logar payloads completos (somente IDs/erros truncados).

Com dashboards, alertas e runbooks alinhados ao novo serviço, o lançamento pode avançar para ensaio em produção (M8).
