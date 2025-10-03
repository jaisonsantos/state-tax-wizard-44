# Consistency Patch Log (Pendências Detectadas)

## Diferenças código ↔ documentação ↔ tooling
- ✅ Coleção Postman "Billing" cobre entitlements, usage, checkout, portal e webhook com detecção de `billing_unconfigured`, alinhando o que `docs/billing/stripe.md` descreve com o comportamento real dos endpoints. 【F:docs/postman/state-tax-wizard.postman_collection.json†L940-L1259】【F:docs/billing/stripe.md†L15-L60】【F:backend/app/routers/billing.py†L1-L220】
- ✅ Evidências (`migrate.txt`, `api_logs.txt`, smokes, metrics) renovadas para sustentar o gate de certificação e as referências em `docs/AGENTE.md`/`DECISION.md`. 【F:docs/certification/EVIDENCE/migrate.txt†L1-L10】【F:docs/certification/EVIDENCE/api_logs.txt†L1-L8】【F:docs/certification/EVIDENCE/security_smoke.txt†L1-L7】
- ✅ Documentos de segurança atualizados para referenciar `assert_store_access`, além de playbooks de segredos/incidentes agora disponíveis em `docs/security/`. 【F:docs/backlog/14_milestone_04_security.md†L6-L60】【F:docs/security/secrets.md†L1-L120】【F:docs/security/incident-response.md†L1-L120】
- ✅ Referências ao arquivo `newman_billing.txt` clarificadas como opcionais para evitar inconsistências com o `.gitignore`. 【F:docs/billing/stripe.md†L80-L110】【F:docs/certification/EVIDENCE/README.md†L12-L30】

## Próximas ações de consistência
1. Monitorar Milestone 6 para garantir que novos conectores (WooCommerce/Shopify) mantenham HMAC e métricas alinhadas com documentação existente. 【F:docs/backlog/16_milestone_06_integrations.md†L1-L160】

