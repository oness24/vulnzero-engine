.PHONY: help install install-dev clean test test-unit test-integration test-e2e coverage lint format type-check security-check docker-build docker-up docker-down migrate migrate-create db-upgrade db-downgrade run-api run-celery pre-commit

.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
BLACK := $(PYTHON) -m black
ISORT := $(PYTHON) -m isort
FLAKE8 := $(PYTHON) -m flake8
MYPY := $(PYTHON) -m mypy
BANDIT := $(PYTHON) -m bandit
SAFETY := $(PYTHON) -m safety

help: ## Show this help message
	@echo "VulnZero - Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install-dev: ## Install development dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e .
	pre-commit install

clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .eggs/
	rm -rf .pytest_cache/ .coverage htmlcov/ .mypy_cache/

test: ## Run all tests
	$(PYTEST) -v

test-unit: ## Run unit tests only
	$(PYTEST) -v -m unit tests/unit/

test-integration: ## Run integration tests only
	$(PYTEST) -v -m integration tests/integration/

test-e2e: ## Run end-to-end tests only
	$(PYTEST) -v -m e2e tests/e2e/

coverage: ## Run tests with coverage report
	$(PYTEST) --cov=vulnzero --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

lint: ## Run all linters
	$(FLAKE8) vulnzero/ tests/
	$(PYLINT) vulnzero/

format: ## Format code with black and isort
	$(BLACK) vulnzero/ tests/
	$(ISORT) vulnzero/ tests/

format-check: ## Check code formatting without changing files
	$(BLACK) --check vulnzero/ tests/
	$(ISORT) --check-only vulnzero/ tests/

type-check: ## Run type checking with mypy
	$(MYPY) vulnzero/

security-check: ## Run security checks
	$(BANDIT) -r vulnzero/ -f json -o bandit-report.json || true
	$(SAFETY) check --json || true
	@echo "Security reports generated: bandit-report.json"

pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

docker-build: ## Build Docker images
	docker-compose build

docker-up: ## Start Docker containers
	docker-compose up -d

docker-down: ## Stop Docker containers
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f

migrate: ## Create a new database migration
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

db-upgrade: ## Apply database migrations
	alembic upgrade head

db-downgrade: ## Rollback last database migration
	alembic downgrade -1

db-reset: ## Reset database (drop and recreate)
	@echo "WARNING: This will destroy all data. Press Ctrl+C to cancel."
	@sleep 3
	alembic downgrade base
	alembic upgrade head

run-api: ## Run the API server locally
	uvicorn vulnzero.services.api_gateway.main:app --reload --host 0.0.0.0 --port 8000

run-celery: ## Run Celery worker
	celery -A vulnzero.services.worker worker --loglevel=info

shell: ## Open Python shell with app context
	$(PYTHON) -i scripts/shell.py

db-seed: ## Seed database with sample data
	$(PYTHON) scripts/seed_database.py

quality: format type-check lint security-check ## Run all quality checks

ci: install-dev quality test coverage ## Run full CI pipeline locally

setup: install-dev db-upgrade ## Initial project setup

dev: docker-up run-api ## Start development environment
