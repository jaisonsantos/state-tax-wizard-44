.PHONY: help dev build up down logs logs-api logs-db test test-quick migrate seed smoke analytics-smoke reports-smoke security-smoke billing-smoke integrations-smoke webhooks-smoke woocommerce-build woocommerce-test shopify-build shopify-test sdk-test clean restart shell-api shell-db metrics newman newman-security newman-billing validate m4-validation m5-validation m6-validation m7-validation cleanup-webhooks metrics-dump full-validation full-validation-all anti-drift evidence-scan evidence-clean stripe-listen

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

dev: ## Build and run all services in foreground (for development)
	docker-compose up --build

build: ## Build Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

logs: ## Tail logs from all services
	docker-compose logs -f

logs-api: ## Tail API logs
	docker-compose logs -f api

logs-db: ## Tail database logs
	docker-compose logs -f db

test: ## Run pytest suite
	docker-compose exec api pytest -v

test-quick: ## Run pytest in quiet mode
	docker-compose exec api pytest -q

migrate: ## Run database migrations
	docker-compose exec api python -m alembic upgrade head

seed: ## Seed demo data
	docker-compose exec api python seed_data.py

smoke: ## Run comprehensive smoke tests
	docker-compose exec api python smoke_test.py

analytics-smoke: ## Smoke test analytics endpoints
	@echo "==> Testing /v1/analytics/overview..."
	@docker-compose exec -T api python smoke_test.py --analytics-only || true

reports-smoke: ## Smoke test report generation
	@echo "==> Testing report endpoints..."
	@docker-compose exec -T api python smoke_test.py --reports-only || true

security-smoke: ## Smoke test HMAC + rate limiting
	@echo "==> Testing security features (HMAC, rate limiting, rotation)..."
	docker-compose exec -T api python smoke_test.py

billing-smoke: ## Smoke test billing endpoints (requires Stripe configuration)
	@echo "==> Testing billing endpoints..."
	docker-compose exec -T api python smoke_test.py --billing-only

integrations-smoke: ## Smoke test integrations endpoints (feature flags)
	@echo "==> Testing integration readiness..."
	docker-compose exec -T api python smoke_test.py --integrations-only

webhooks-smoke: ## Smoke test Stripe webhook ingestion
	@echo "==> Testing webhook ingestion..."
	docker-compose exec -T api python smoke_test.py --webhooks-only

woocommerce-build: ## Package the WooCommerce plugin ZIP
	@echo "==> Packaging WooCommerce plugin..."
	@cd integrations/woocommerce && ./package.sh

woocommerce-test: ## Run WooCommerce plugin PHPUnit tests
	@echo "==> Running WooCommerce PHPUnit tests..."
	@cd integrations/woocommerce && composer install --no-interaction --quiet && ./vendor/bin/phpunit

shopify-build: ## Build Shopify proxy/webhook app
	@echo "==> Building Shopify app..."
	@cd integrations/shopify && npm install --no-audit --no-fund && npm run build

shopify-test: ## Run Shopify integration tests
	@echo "==> Running Shopify Jest suite..."
	@cd integrations/shopify && npm install --no-audit --no-fund && npm test

sdk-test: ## Run TypeScript SDK unit tests
	@echo "==> Running TypeScript SDK tests..."
	@cd integrations/sdk/typescript && npm install --no-audit --no-fund && npm test

clean: ## Remove all containers and volumes
	docker-compose down -v

restart: down up ## Restart all services

shell-api: ## Open shell in API container
	docker-compose exec api bash

shell-db: ## Open psql shell in database
	docker-compose exec db psql -U user -d rdf

metrics: ## Display Prometheus metrics
	@echo "==> Fetching /metrics endpoint..."
	@curl -s http://localhost:8000/metrics | grep -E "(rate_limit|hmac|billing|fees|report)" | head -20

newman: ## Run Postman collection via Newman
	@echo "==> Running Postman collection..."
	@if [ -f docs/postman/local.postman_environment.json ]; then \
		docker run --rm --network=host -v $(PWD)/docs/postman:/etc/newman postman/newman:latest \
			run /etc/newman/state-tax-wizard.postman_collection.json \
			--environment /etc/newman/local.postman_environment.json \
			--reporters cli,json \
			--reporter-json-export /etc/newman/newman-results.json; \
	else \
		echo "⚠ SKIP: docs/postman/local.postman_environment.json not found"; \
	fi

newman-security: ## Run security folder in Postman collection
	@echo "==> Running Postman security tests..."
	@if [ -f docs/postman/local.postman_environment.json ]; then \
		docker run --rm --network=host -v $(PWD)/docs/postman:/etc/newman postman/newman:latest \
			run /etc/newman/state-tax-wizard.postman_collection.json \
			--folder "Security" \
			--environment /etc/newman/local.postman_environment.json \
			--reporters cli; \
	else \
		echo "⚠ SKIP: docs/postman/local.postman_environment.json not found"; \
	fi

newman-billing: ## Run billing folder in Postman collection
	@echo "==> Running Postman billing tests..."
	@if [ -f docs/postman/local.postman_environment.json ]; then \
		docker run --rm --network=host -v $(PWD)/docs/postman:/etc/newman postman/newman:latest \
			run /etc/newman/state-tax-wizard.postman_collection.json \
			--folder "Billing" \
			--environment /etc/newman/local.postman_environment.json \
			--reporters cli; \
	else \
		echo "⚠ SKIP: docs/postman/local.postman_environment.json not found"; \
	fi

validate: test smoke metrics ## Run all validation steps
	@echo "==> All validation complete!"

m4-validation: security-smoke metrics ## Validate M4 (Security)
	@echo "==> M4 Security validation complete. Check EVIDENCE/ for outputs."

m5-validation: billing-smoke ## Validate M5 (Billing)
	@echo "==> M5 Billing validation complete. Check EVIDENCE/ for outputs."

m6-validation: integrations-smoke ## Validate M6 (Integrations)
	@echo "==> M6 Integrations validation complete. Check EVIDENCE/ for outputs."

m7-validation: webhooks-smoke ## Validate M7 (Webhooks)
	@echo "==> M7 Webhooks validation complete. Check EVIDENCE/ for outputs."

# --- Evidência / utilitários ---

# Limpa processed_webhooks (roda o SQL dentro do container do Postgres)
cleanup-webhooks:
	@mkdir -p docs/certification/EVIDENCE
	cat scripts/cleanup_processed_webhooks.sql \
	| docker-compose exec -T db psql -U user -d rdf -v ON_ERROR_STOP=1

# Dump rápido de métricas relevantes p/ evidência
metrics-dump:
	@mkdir -p docs/certification/EVIDENCE
	curl -s http://localhost:8000/metrics \
	| grep -E "webhook|billing" \
	| tee docs/certification/EVIDENCE/metrics_dump.txt

# --- Validações ---

# Versão enxuta (certificação): tests + smokes + métricas
full-validation:
	@mkdir -p docs/certification/EVIDENCE
	docker-compose exec -T api pytest -q | tee docs/certification/EVIDENCE/pytest.txt
	$(MAKE) webhooks-smoke
	$(MAKE) billing-smoke | tee docs/certification/EVIDENCE/billing_smoke.txt
	$(MAKE) metrics-dump

# Versão completa antiga (se quiser manter por compatibilidade)
full-validation-all: test smoke analytics-smoke reports-smoke security-smoke billing-smoke metrics newman
	@echo "==> Full validation complete!"

# Evidence scans (small, to avoid huge artifacts)
evidence-scan: ## Generate small anti-drift evidence files
	@mkdir -p docs/ccertification/EVIDENCE
	rg -n --hidden --no-ignore --color never \
	  -g '!node_modules/**' -g '!.git/**' -g '!dist/**' -g '!build/**' -g '!.cache/**' \
	  -g '!docs/certification/EVIDENCE/**' \
	  'X-(RDF-)?(Signature|Timestamp|Nonce)' docs src backend \
	  | head -n 2000 > docs/certification/EVIDENCE/headers_scan.txt
	rg -n --hidden -g '!node_modules/**' -g '!.git/**' \
	  'hmac_secret.*store' docs backend \
	  | head -n 500 > docs/certification/EVIDENCE/hmac_secret_scan.txt

anti-drift: evidence-scan ## Backwards-compatible alias for legacy jobs

evidence-clean: ## Remove accidentally large evidence files
	@rm -f docs/certification/EVIDENCE/headers_scan.txt
	@rm -f docs/certification/EVIDENCE/*.log docs/certification/EVIDENCE/*~ 2>/dev/null || true

stripe-listen: ## Start Stripe CLI webhook forwarder (keep this running while testing)
	stripe listen --events checkout.session.completed,invoice.paid,invoice.payment_failed,customer.subscription.created,customer.subscription.updated,customer.subscription.deleted --forward-to http://localhost:8000/api/v1/billing/webhooks/stripe
