# Service Level Objectives – Webhook Launch

## Escopo
Cobre webhooks outbound, geração de relatórios e suporte associado ao launch M8.

## Objetivos
| SLO | Meta | Janela | Medição | Alertas |
| --- | --- | --- | --- | --- |
| Entrega de webhooks P95 | ≤ 5s | 28 dias | `histogram_quantile(0.95, sum(rate(webhooks_delivery_seconds_bucket[5m])) by (le))` | Warning ≥ 4s (15 min), Critical ≥ 5s (15 min) |
| Taxa de sucesso | ≥ 99.5% | 28 dias | `sum(rate(webhooks_delivery_total{status="delivered"}[1h])) / sum(rate(webhooks_delivery_total[1h]))` | Warning < 99.5%, Critical < 99% |
| DLQ zerada | 0 eventos | 1h | `increase(webhooks_dead_letter_total[15m])` + monitoramento de estoque DLQ | Warning >0 (5 min), Critical >0 (30 min) |
| Precisão de relatórios | 100% | por release | Auditoria manual (MN/CO) + `pytest -k report_ready` | Critical: discrepância detectada |
| Disponibilidade API | 99.9% | 30 dias | Uptime monitor `/healthz` | Warning < 99.9%, Critical < 99.5% |

## Acordos de suporte
- Tempo de resposta inicial ≤ 30 min (horário comercial) / 1h (off-hours).
- Tempo para mitigação ≤ 2h para incidentes S1.
- Comunicação recorrente a cada 30 min enquanto incidente aberto.

## Instrumentação necessária
- Expor `/metrics` com `webhooks_delivery_total`, `webhooks_delivery_seconds`, `webhooks_failed_total`, `webhooks_dead_letter_total`.
- Configurar scraping Prometheus (intervalo 15s) em staging/produção.
- Dashboard Grafana com widgets preconfigurados (ver `docs/observability.md`).

## Processos
- Revisão mensal de SLOs (observability + suporte).
- Postmortem obrigatório para violações de sucesso (<99.5%) ou DLQ>0 >30min.
- Atualizar `docs/launch/GO_LIVE_CHECKLIST_M8.md` após cada revisão.

## Futuro
- Adicionar SLO de throughput (eventos/minuto) conforme crescimento.
- Integrar métricas ao status page automaticamente.
