# ============================================================================
# VulnZero Makefile
# ============================================================================
# Common commands for development, testing, and deployment
#
# Usage:
#   make <target>
#
# Examples:
#   make setup          - Initial project setup
#   make test           - Run all tests
#   make docker-up      - Start all Docker services
#   make help           - Show this help message

.PHONY: help
.DEFAULT_GOAL := help

# ============================================================================
# Variables
# ============================================================================
PYTHON := python3.11
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
BLACK := $(PYTHON) -m black
FLAKE8 := $(PYTHON) -m flake8
MYPY := $(PYTHON) -m mypy
ISORT := $(PYTHON) -m isort

DOCKER_COMPOSE := docker-compose
DOCKER := docker

PROJECT_NAME := vulnzero
VENV_DIR := venv
REQUIREMENTS := requirements.txt

# Colors for output
COLOR_RESET := \033[0m
COLOR_BOLD := \033[1m
COLOR_GREEN := \033[32m
COLOR_YELLOW := \033[33m
COLOR_BLUE := \033[34m

# ============================================================================
# Help
# ============================================================================
help: ## Show this help message
	@echo "$(COLOR_BOLD)VulnZero - Available Commands$(COLOR_RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(COLOR_BLUE)%-20s$(COLOR_RESET) %s\n", $$1, $$2}'
	@echo ""

# ============================================================================
# Setup & Installation
# ============================================================================
.PHONY: setup
setup: ## Initial project setup (venv, dependencies, pre-commit)
	@echo "$(COLOR_GREEN)Setting up VulnZero development environment...$(COLOR_RESET)"
	@$(MAKE) venv
	@$(MAKE) install
	@$(MAKE) pre-commit-install
	@$(MAKE) env-file
	@echo "$(COLOR_GREEN)✓ Setup complete! Run 'source venv/bin/activate' to activate virtualenv$(COLOR_RESET)"

.PHONY: venv
venv: ## Create Python virtual environment
	@echo "$(COLOR_BLUE)Creating virtual environment...$(COLOR_RESET)"
	@$(PYTHON) -m venv $(VENV_DIR)
	@echo "$(COLOR_GREEN)✓ Virtual environment created$(COLOR_RESET)"

.PHONY: install
install: ## Install Python dependencies
	@echo "$(COLOR_BLUE)Installing dependencies...$(COLOR_RESET)"
	@$(PIP) install --upgrade pip setuptools wheel
	@$(PIP) install -r $(REQUIREMENTS)
	@echo "$(COLOR_GREEN)✓ Dependencies installed$(COLOR_RESET)"

.PHONY: install-dev
install-dev: ## Install development dependencies
	@echo "$(COLOR_BLUE)Installing development dependencies...$(COLOR_RESET)"
	@$(PIP) install -e ".[dev]"
	@echo "$(COLOR_GREEN)✓ Development dependencies installed$(COLOR_RESET)"

.PHONY: env-file
env-file: ## Create .env file from .env.example
	@if [ ! -f .env ]; then \
		echo "$(COLOR_YELLOW)Creating .env file from .env.example...$(COLOR_RESET)"; \
		cp .env.example .env; \
		echo "$(COLOR_GREEN)✓ .env file created. Please edit it with your configuration.$(COLOR_RESET)"; \
	else \
		echo "$(COLOR_YELLOW).env file already exists. Skipping.$(COLOR_RESET)"; \
	fi

# ============================================================================
# Development
# ============================================================================
.PHONY: run
run: ## Run all services locally
	@echo "$(COLOR_GREEN)Starting VulnZero services...$(COLOR_RESET)"
	@$(MAKE) run-api &
	@$(MAKE) run-workers

.PHONY: run-api
run-api: ## Run API Gateway
	@echo "$(COLOR_BLUE)Starting API Gateway...$(COLOR_RESET)"
	@cd services/api-gateway && uvicorn main:app --reload --host 0.0.0.0 --port 8000

.PHONY: run-workers
run-workers: ## Run Celery workers
	@echo "$(COLOR_BLUE)Starting Celery workers...$(COLOR_RESET)"
	@celery -A shared.celery_app worker --loglevel=info --concurrency=4

.PHONY: run-beat
run-beat: ## Run Celery beat scheduler
	@echo "$(COLOR_BLUE)Starting Celery beat...$(COLOR_RESET)"
	@celery -A shared.celery_app beat --loglevel=info

.PHONY: run-flower
run-flower: ## Run Flower (Celery monitoring)
	@echo "$(COLOR_BLUE)Starting Flower...$(COLOR_RESET)"
	@celery -A shared.celery_app flower --port=5555

.PHONY: run-web
run-web: ## Run web dashboard (React)
	@echo "$(COLOR_BLUE)Starting web dashboard...$(COLOR_RESET)"
	@cd web && npm start

# ============================================================================
# Docker Commands
# ============================================================================
.PHONY: docker-build
docker-build: ## Build all Docker images
	@echo "$(COLOR_BLUE)Building Docker images...$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) build
	@echo "$(COLOR_GREEN)✓ Docker images built$(COLOR_RESET)"

.PHONY: docker-up
docker-up: ## Start all Docker services
	@echo "$(COLOR_BLUE)Starting Docker services...$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) up -d
	@echo "$(COLOR_GREEN)✓ Services started$(COLOR_RESET)"
	@$(MAKE) docker-ps

.PHONY: docker-down
docker-down: ## Stop all Docker services
	@echo "$(COLOR_BLUE)Stopping Docker services...$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) down
	@echo "$(COLOR_GREEN)✓ Services stopped$(COLOR_RESET)"

.PHONY: docker-restart
docker-restart: ## Restart all Docker services
	@$(MAKE) docker-down
	@$(MAKE) docker-up

.PHONY: docker-ps
docker-ps: ## Show running Docker containers
	@echo "$(COLOR_BLUE)Running containers:$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) ps

.PHONY: docker-logs
docker-logs: ## View Docker logs (use SERVICE=<name> for specific service)
	@$(DOCKER_COMPOSE) logs -f $(SERVICE)

.PHONY: docker-shell
docker-shell: ## Access shell in container (use SERVICE=<name>)
	@$(DOCKER_COMPOSE) exec $(SERVICE) /bin/bash

.PHONY: docker-clean
docker-clean: ## Remove all Docker containers, volumes, and images
	@echo "$(COLOR_YELLOW)Removing all Docker resources...$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) down -v --remove-orphans
	@$(DOCKER) system prune -af --volumes
	@echo "$(COLOR_GREEN)✓ Docker resources cleaned$(COLOR_RESET)"

# ============================================================================
# Database Commands
# ============================================================================
.PHONY: db-migrate
db-migrate: ## Run database migrations
	@echo "$(COLOR_BLUE)Running database migrations...$(COLOR_RESET)"
	@alembic upgrade head
	@echo "$(COLOR_GREEN)✓ Migrations complete$(COLOR_RESET)"

.PHONY: db-rollback
db-rollback: ## Rollback last database migration
	@echo "$(COLOR_YELLOW)Rolling back last migration...$(COLOR_RESET)"
	@alembic downgrade -1
	@echo "$(COLOR_GREEN)✓ Rollback complete$(COLOR_RESET)"

.PHONY: db-revision
db-revision: ## Create new database migration (use MESSAGE="description")
	@echo "$(COLOR_BLUE)Creating migration: $(MESSAGE)$(COLOR_RESET)"
	@alembic revision --autogenerate -m "$(MESSAGE)"
	@echo "$(COLOR_GREEN)✓ Migration created$(COLOR_RESET)"

.PHONY: db-seed
db-seed: ## Seed database with sample data
	@echo "$(COLOR_BLUE)Seeding database...$(COLOR_RESET)"
	@$(PYTHON) scripts/seed_database.py
	@echo "$(COLOR_GREEN)✓ Database seeded$(COLOR_RESET)"

.PHONY: db-reset
db-reset: ## Reset database (WARNING: deletes all data)
	@echo "$(COLOR_YELLOW)⚠️  WARNING: This will delete all data!$(COLOR_RESET)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		alembic downgrade base; \
		alembic upgrade head; \
		$(MAKE) db-seed; \
		echo "$(COLOR_GREEN)✓ Database reset$(COLOR_RESET)"; \
	fi

.PHONY: db-shell
db-shell: ## Access PostgreSQL shell
	@$(DOCKER_COMPOSE) exec postgres psql -U vulnzero -d vulnzero

# ============================================================================
# Testing
# ============================================================================
.PHONY: test
test: ## Run all tests
	@echo "$(COLOR_BLUE)Running all tests...$(COLOR_RESET)"
	@$(PYTEST) tests/ -v --tb=short
	@echo "$(COLOR_GREEN)✓ Tests complete$(COLOR_RESET)"

.PHONY: test-unit
test-unit: ## Run unit tests
	@echo "$(COLOR_BLUE)Running unit tests...$(COLOR_RESET)"
	@$(PYTEST) tests/unit/ -v

.PHONY: test-integration
test-integration: ## Run integration tests
	@echo "$(COLOR_BLUE)Running integration tests...$(COLOR_RESET)"
	@$(PYTEST) tests/integration/ -v

.PHONY: test-e2e
test-e2e: ## Run end-to-end tests
	@echo "$(COLOR_BLUE)Running E2E tests...$(COLOR_RESET)"
	@$(PYTEST) tests/e2e/ -v

.PHONY: test-watch
test-watch: ## Run tests in watch mode
	@$(PYTEST) tests/ -v --tb=short -f

.PHONY: coverage
coverage: ## Generate test coverage report
	@echo "$(COLOR_BLUE)Generating coverage report...$(COLOR_RESET)"
	@$(PYTEST) tests/ --cov=services --cov=shared --cov-report=html --cov-report=term
	@echo "$(COLOR_GREEN)✓ Coverage report generated: htmlcov/index.html$(COLOR_RESET)"

.PHONY: coverage-report
coverage-report: ## Open coverage report in browser
	@open htmlcov/index.html || xdg-open htmlcov/index.html

# ============================================================================
# Code Quality
# ============================================================================
.PHONY: format
format: ## Format code with black and isort
	@echo "$(COLOR_BLUE)Formatting code...$(COLOR_RESET)"
	@$(BLACK) services/ shared/ tests/
	@$(ISORT) services/ shared/ tests/
	@echo "$(COLOR_GREEN)✓ Code formatted$(COLOR_RESET)"

.PHONY: lint
lint: ## Run linters (flake8, black, mypy)
	@echo "$(COLOR_BLUE)Running linters...$(COLOR_RESET)"
	@$(BLACK) --check services/ shared/ tests/
	@$(FLAKE8) services/ shared/ tests/
	@$(MYPY) services/ shared/
	@echo "$(COLOR_GREEN)✓ Linting complete$(COLOR_RESET)"

.PHONY: lint-fix
lint-fix: ## Fix linting issues automatically
	@$(MAKE) format

.PHONY: type-check
type-check: ## Run type checking with mypy
	@echo "$(COLOR_BLUE)Running type checker...$(COLOR_RESET)"
	@$(MYPY) services/ shared/

.PHONY: security-check
security-check: ## Run security checks (bandit, safety)
	@echo "$(COLOR_BLUE)Running security checks...$(COLOR_RESET)"
	@bandit -r services/ shared/ -ll
	@safety check
	@echo "$(COLOR_GREEN)✓ Security checks complete$(COLOR_RESET)"

# ============================================================================
# Pre-commit
# ============================================================================
.PHONY: pre-commit-install
pre-commit-install: ## Install pre-commit hooks
	@echo "$(COLOR_BLUE)Installing pre-commit hooks...$(COLOR_RESET)"
	@pre-commit install
	@echo "$(COLOR_GREEN)✓ Pre-commit hooks installed$(COLOR_RESET)"

.PHONY: pre-commit-run
pre-commit-run: ## Run pre-commit on all files
	@echo "$(COLOR_BLUE)Running pre-commit checks...$(COLOR_RESET)"
	@pre-commit run --all-files

# ============================================================================
# Documentation
# ============================================================================
.PHONY: docs
docs: ## Generate API documentation
	@echo "$(COLOR_BLUE)Generating documentation...$(COLOR_RESET)"
	@cd docs && make html
	@echo "$(COLOR_GREEN)✓ Documentation generated$(COLOR_RESET)"

.PHONY: docs-serve
docs-serve: ## Serve documentation locally
	@echo "$(COLOR_BLUE)Serving documentation at http://localhost:8001$(COLOR_RESET)"
	@cd docs/_build/html && $(PYTHON) -m http.server 8001

# ============================================================================
# Cleanup
# ============================================================================
.PHONY: clean
clean: ## Clean temporary files and caches
	@echo "$(COLOR_BLUE)Cleaning temporary files...$(COLOR_RESET)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name ".coverage" -delete
	@rm -rf htmlcov/
	@rm -rf dist/
	@rm -rf build/
	@echo "$(COLOR_GREEN)✓ Cleanup complete$(COLOR_RESET)"

.PHONY: clean-all
clean-all: clean docker-clean ## Clean everything (files + Docker)
	@echo "$(COLOR_GREEN)✓ Complete cleanup done$(COLOR_RESET)"

# ============================================================================
# Deployment
# ============================================================================
.PHONY: build
build: ## Build production artifacts
	@echo "$(COLOR_BLUE)Building production artifacts...$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) -f docker-compose.prod.yml build
	@echo "$(COLOR_GREEN)✓ Build complete$(COLOR_RESET)"

.PHONY: deploy-staging
deploy-staging: ## Deploy to staging environment
	@echo "$(COLOR_BLUE)Deploying to staging...$(COLOR_RESET)"
	@# Add your staging deployment commands here
	@echo "$(COLOR_GREEN)✓ Deployed to staging$(COLOR_RESET)"

.PHONY: deploy-prod
deploy-prod: ## Deploy to production environment
	@echo "$(COLOR_YELLOW)⚠️  Deploying to PRODUCTION$(COLOR_RESET)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(COLOR_BLUE)Deploying to production...$(COLOR_RESET)"; \
		# Add your production deployment commands here; \
		echo "$(COLOR_GREEN)✓ Deployed to production$(COLOR_RESET)"; \
	fi

# ============================================================================
# Utilities
# ============================================================================
.PHONY: logs
logs: ## View application logs
	@tail -f logs/*.log

.PHONY: shell
shell: ## Start Python shell with app context
	@$(PYTHON) -i scripts/shell.py

.PHONY: check
check: lint test ## Run linters and tests
	@echo "$(COLOR_GREEN)✓ All checks passed$(COLOR_RESET)"

.PHONY: ci
ci: clean install lint test coverage ## Run CI pipeline locally
	@echo "$(COLOR_GREEN)✓ CI pipeline complete$(COLOR_RESET)"

.PHONY: version
version: ## Show current version
	@echo "VulnZero v0.1.0"

.PHONY: deps-update
deps-update: ## Update dependencies
	@echo "$(COLOR_BLUE)Updating dependencies...$(COLOR_RESET)"
	@$(PIP) install --upgrade -r $(REQUIREMENTS)
	@$(PIP) freeze > requirements-lock.txt
	@echo "$(COLOR_GREEN)✓ Dependencies updated$(COLOR_RESET)"

# ============================================================================
# Quick Commands (Aliases)
# ============================================================================
.PHONY: up down restart ps
up: docker-up ## Alias for docker-up
down: docker-down ## Alias for docker-down
restart: docker-restart ## Alias for docker-restart
ps: docker-ps ## Alias for docker-ps
