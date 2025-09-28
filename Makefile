.PHONY: dev up down build clean logs migrate seed

# Development - run all services
dev:
	docker-compose up --build

# Start services
up:
	docker-compose up -d

# Stop services
down:
	docker-compose down

# Build services
build:
	docker-compose build

# Clean up everything
clean:
	docker-compose down -v
	docker system prune -f

# View logs
logs:
	docker-compose logs -f

# View API logs only
logs-api:
	docker-compose logs -f api

# Run database migrations
migrate:
	docker-compose exec api python -m alembic upgrade head

# Seed database
seed:
	docker-compose exec api python seed_data.py

# Run with PGAdmin
dev-tools:
	docker-compose --profile tools up --build

# Backend shell
shell-api:
	docker-compose exec api bash

# Database shell
shell-db:
	docker-compose exec postgres psql -U user -d rdf