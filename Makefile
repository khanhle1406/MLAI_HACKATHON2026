.PHONY: help setup dev api web test verify docker-up docker-down lint clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Install dependencies
	pip install -e ".[dev]"
	cd apps/web && npm install

dev: ## Start all services locally
	@echo "Starting PostgreSQL and Redis..."
	docker-compose -f docker/docker-compose.yml up -d postgres redis
	@echo "Starting API..."
	python -m uvicorn apps.api.main:app --reload --port 8000 &
	@echo "Starting Web..."
	cd apps/web && npm run dev &

api: ## Start FastAPI backend
	python -m uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

web: ## Start Next.js frontend
	cd apps/web && npm run dev

test: ## Run all tests
	python -m pytest tests/ -v --tb=short

verify: ## Run competition verify harness
	python verify/run_verify.py

docker-up: ## Start all Docker services
	docker-compose -f docker/docker-compose.yml up --build

docker-down: ## Stop all Docker services
	docker-compose -f docker/docker-compose.yml down

lint: ## Run linters
	python -m ruff check core/ apps/ tests/
	python -m mypy core/ --ignore-missing-imports

clean: ## Clean build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache

db-init: ## Initialize database tables
	python -c "import asyncio; from database.session import init_db; asyncio.run(init_db())"

seed: ## Seed benchmark data
	python scripts/seed_data.py
