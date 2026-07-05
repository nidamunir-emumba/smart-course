.PHONY: help infra up down logs migrate revision seed api worker consumer test lint fmt

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "\033[36m%-12s\033[0m %s\n", $$1, $$2}'

infra: ## Start infra only (no app services)
	docker compose up -d postgres mongo redis qdrant rabbitmq kafka schema-registry temporal temporal-ui jaeger otel-collector prometheus grafana

up: ## Start the entire stack (infra + app services)
	docker compose up -d --build

down: ## Stop everything and remove containers
	docker compose down

logs: ## Tail logs for all services
	docker compose logs -f

migrate: ## Apply DB migrations
	alembic upgrade head

revision: ## Create a new migration (make revision m="add courses")
	alembic revision --autogenerate -m "$(m)"

seed: ## Seed demo courses with long-form lessons (runs in the api container)
	docker compose exec api python -m scripts.seed

api: ## Run the API locally (needs infra up)
	uvicorn app.main:app --reload --port 8000

worker: ## Run the Temporal worker locally
	python -m app.workflows.worker

celery: ## Run the Celery worker locally
	celery -A app.tasks.celery_app.celery worker --loglevel=info

consumer: ## Run Kafka event consumers locally
	python -m app.events.run_consumers

test: ## Run tests
	pytest

lint: ## Lint + type-check
	ruff check app && mypy app

fmt: ## Auto-format and fix imports
	ruff check --fix app && ruff format app
