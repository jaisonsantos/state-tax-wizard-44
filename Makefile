.PHONY: help dev build up down logs logs-api logs-db test test-quick migrate seed smoke analytics-smoke reports-smoke security-smoke billing-smoke clean restart shell-api shell-db metrics newman newman-security newman-billing validate m4-validation m5-validation full-validation anti-drift evidence-scan evidence-clean

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
	docker-compose exec api alembic upgrade head

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

clean: ## Remove all containers and volumes
	docker-compose down -v

restart: down up ## Restart all services

shell-api: ## Open shell in API container
	docker-compose exec api bash

shell-db: ## Open psql shell in database
	docker-compose exec db psql -U postgres -d rdf

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

full-validation: test smoke analytics-smoke reports-smoke security-smoke billing-smoke metrics newman ## Complete validation suite
	@echo "==> Full validation complete!"

# Varreduras de evidência (limitadas para evitar artefatos gigantes)
evidence-scan: ## Generate small anti-drift evidence files
	@mkdir -p docs/certification/EVIDENCE
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
