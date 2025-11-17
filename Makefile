.PHONY: help setup install dev clean test lint format docker-build docker-up docker-down migrate db-upgrade db-downgrade seed-db run logs

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)VulnZero - Available Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

setup: ## Initial project setup
	@echo "$(BLUE)Setting up VulnZero...$(NC)"
	@cp -n .env.example .env || true
	@echo "$(GREEN)✓ Environment file created (.env)$(NC)"
	@python3 -m venv venv
	@echo "$(GREEN)✓ Virtual environment created$(NC)"
	@echo "$(YELLOW)Run 'source venv/bin/activate' to activate the virtual environment$(NC)"

install: ## Install Python dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	@pip install --upgrade pip
	@pip install -r requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	@pip install -r requirements.txt
	@pip install pre-commit
	@pre-commit install
	@echo "$(GREEN)✓ Development environment ready$(NC)"

clean: ## Clean up temporary files and caches
	@echo "$(BLUE)Cleaning up...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@rm -f .coverage
	@echo "$(GREEN)✓ Cleaned up$(NC)"

test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	@pytest -v --cov=services --cov=shared --cov-report=term-missing
	@echo "$(GREEN)✓ Tests completed$(NC)"

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	@pytest -v -m unit
	@echo "$(GREEN)✓ Unit tests completed$(NC)"

test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	@pytest -v -m integration
	@echo "$(GREEN)✓ Integration tests completed$(NC)"

test-e2e: ## Run end-to-end tests only
	@echo "$(BLUE)Running e2e tests...$(NC)"
	@pytest -v -m e2e
	@echo "$(GREEN)✓ E2E tests completed$(NC)"

coverage: ## Generate test coverage report
	@echo "$(BLUE)Generating coverage report...$(NC)"
	@pytest --cov=services --cov=shared --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/index.html$(NC)"

lint: ## Run linters (ruff, mypy)
	@echo "$(BLUE)Running linters...$(NC)"
	@ruff check services/ shared/ tests/
	@mypy services/ shared/
	@echo "$(GREEN)✓ Linting completed$(NC)"

format: ## Format code with black and ruff
	@echo "$(BLUE)Formatting code...$(NC)"
	@black services/ shared/ tests/
	@ruff check --fix services/ shared/ tests/
	@echo "$(GREEN)✓ Code formatted$(NC)"

type-check: ## Run type checking with mypy
	@echo "$(BLUE)Running type checks...$(NC)"
	@mypy services/ shared/
	@echo "$(GREEN)✓ Type checking completed$(NC)"

docker-build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	@docker-compose build
	@echo "$(GREEN)✓ Docker images built$(NC)"

docker-up: ## Start all services with Docker Compose
	@echo "$(BLUE)Starting services...$(NC)"
	@docker-compose up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo "$(YELLOW)API Gateway: http://localhost:8000$(NC)"
	@echo "$(YELLOW)Grafana: http://localhost:3001$(NC)"
	@echo "$(YELLOW)Flower: http://localhost:5555$(NC)"
	@echo "$(YELLOW)Prometheus: http://localhost:9090$(NC)"

docker-down: ## Stop all services
	@echo "$(BLUE)Stopping services...$(NC)"
	@docker-compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

docker-down-volumes: ## Stop all services and remove volumes
	@echo "$(BLUE)Stopping services and removing volumes...$(NC)"
	@docker-compose down -v
	@echo "$(GREEN)✓ Services stopped and volumes removed$(NC)"

docker-restart: ## Restart all services
	@echo "$(BLUE)Restarting services...$(NC)"
	@docker-compose restart
	@echo "$(GREEN)✓ Services restarted$(NC)"

docker-logs: ## Show logs from all services
	@docker-compose logs -f

docker-ps: ## Show running containers
	@docker-compose ps

migrate: ## Create a new database migration
	@echo "$(BLUE)Creating migration...$(NC)"
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"
	@echo "$(GREEN)✓ Migration created$(NC)"

db-upgrade: ## Apply database migrations
	@echo "$(BLUE)Applying migrations...$(NC)"
	@alembic upgrade head
	@echo "$(GREEN)✓ Migrations applied$(NC)"

db-downgrade: ## Rollback last database migration
	@echo "$(BLUE)Rolling back migration...$(NC)"
	@alembic downgrade -1
	@echo "$(GREEN)✓ Migration rolled back$(NC)"

db-reset: ## Reset database (drop and recreate)
	@echo "$(RED)WARNING: This will destroy all data!$(NC)"
	@read -p "Are you sure? [y/N]: " confirm; \
	if [ "$$confirm" = "y" ]; then \
		docker-compose down -v; \
		docker-compose up -d postgres redis; \
		sleep 5; \
		alembic upgrade head; \
		echo "$(GREEN)✓ Database reset$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

seed-db: ## Seed database with sample data
	@echo "$(BLUE)Seeding database...$(NC)"
	@python scripts/seed_database.py
	@echo "$(GREEN)✓ Database seeded$(NC)"

run-api: ## Run API Gateway locally
	@echo "$(BLUE)Starting API Gateway...$(NC)"
	@uvicorn services.api_gateway.main:app --reload --host 0.0.0.0 --port 8000

run-worker: ## Run Celery worker locally
	@echo "$(BLUE)Starting Celery worker...$(NC)"
	@celery -A shared.celery_app worker --loglevel=info

run-beat: ## Run Celery beat scheduler locally
	@echo "$(BLUE)Starting Celery beat...$(NC)"
	@celery -A shared.celery_app beat --loglevel=info

run-flower: ## Run Flower (Celery monitoring)
	@echo "$(BLUE)Starting Flower...$(NC)"
	@celery -A shared.celery_app flower --port=5555

logs: ## Tail logs from all services
	@docker-compose logs -f --tail=100

logs-api: ## Tail API Gateway logs
	@docker-compose logs -f --tail=100 api-gateway

logs-worker: ## Tail Celery worker logs
	@docker-compose logs -f --tail=100 celery-worker

shell: ## Open Python shell with app context
	@python -i -c "from shared.config import settings; print('VulnZero Shell - Settings loaded')"

db-shell: ## Open PostgreSQL shell
	@docker-compose exec postgres psql -U vulnzero -d vulnzero

redis-shell: ## Open Redis CLI
	@docker-compose exec redis redis-cli

check: lint test ## Run all checks (lint + test)

ci: clean install lint test ## Run CI pipeline locally

pre-commit: format lint ## Run pre-commit checks

all: clean install docker-build docker-up db-upgrade ## Full setup and start
	@echo "$(GREEN)✓ VulnZero is ready!$(NC)"

# Production commands
prod-build: ## Build production Docker images
	@echo "$(BLUE)Building production images...$(NC)"
	@docker-compose -f docker-compose.prod.yml build
	@echo "$(GREEN)✓ Production images built$(NC)"

prod-up: ## Start production services
	@echo "$(BLUE)Starting production services...$(NC)"
	@docker-compose -f docker-compose.prod.yml up -d
	@echo "$(GREEN)✓ Production services started$(NC)"

prod-down: ## Stop production services
	@echo "$(BLUE)Stopping production services...$(NC)"
	@docker-compose -f docker-compose.prod.yml down
	@echo "$(GREEN)✓ Production services stopped$(NC)"

# Default target
.DEFAULT_GOAL := help
