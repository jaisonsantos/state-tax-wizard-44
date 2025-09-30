.PHONY: dev up down build clean logs logs-api migrate seed dev-tools shell-api shell-db smoke reports-smoke

# Choose docker compose flavor (v2 default)
COMPOSE := docker compose

# Development - run all services (foreground)
dev:
	$(COMPOSE) up --build

# Start services (detached)
up:
	$(COMPOSE) up -d

# Stop services
down:
	$(COMPOSE) down

# Build services
build:
	$(COMPOSE) build

# Clean up everything
clean:
	$(COMPOSE) down -v
	docker system prune -f

# View logs
logs:
	$(COMPOSE) logs -f

# View API logs only
logs-api:
	$(COMPOSE) logs -f api

# Run database migrations
migrate:
	$(COMPOSE) exec api python -m alembic upgrade head

# Seed database
seed:
	$(COMPOSE) exec api python seed_data.py

# Run with PGAdmin (profile tools)
dev-tools:
	$(COMPOSE) --profile tools up --build

# Backend shell
shell-api:
	$(COMPOSE) exec api bash

# Database shell
shell-db:
	$(COMPOSE) exec db psql -U user -d rdf

# End-to-end smoke test across login, fees, audit, and reports
smoke: up migrate seed
	$(COMPOSE) exec api python smoke_test.py

# Focused smoke for report exports
reports-smoke: up migrate seed
	$(COMPOSE) exec api python smoke_test.py --reports-only
