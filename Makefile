.PHONY: help install install-dev setup clean test test-cov lint format type-check security-check run dev migrate docker-up docker-down docker-logs docker-build

# Default target
.DEFAULT_GOAL := help

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

# ============================================
# Installation & Setup
# ============================================

install: ## Install production dependencies
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	pip install -r requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	pip install -r requirements-dev.txt
	pip install -e .
	@echo "$(GREEN)✓ Development dependencies installed$(NC)"

setup: install-dev ## Complete development environment setup
	@echo "$(BLUE)Setting up development environment...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)Creating .env from .env.example$(NC)"; \
		cp .env.example .env; \
		echo "$(YELLOW)⚠ Please edit .env with your configuration$(NC)"; \
	fi
	@echo "$(BLUE)Setting up pre-commit hooks...$(NC)"
	pre-commit install
	@echo "$(BLUE)Starting database services...$(NC)"
	docker-compose up -d postgres redis
	@echo "$(YELLOW)Waiting for database to be ready...$(NC)"
	@sleep 5
	@echo "$(GREEN)✓ Development environment ready$(NC)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Edit .env with your configuration"
	@echo "  2. Run 'make migrate' to set up database"
	@echo "  3. Run 'make dev' to start development server"

clean: ## Clean up generated files
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

# ============================================
# Database
# ============================================

migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	alembic upgrade head
	@echo "$(GREEN)✓ Migrations complete$(NC)"

migrate-create: ## Create a new migration (usage: make migrate-create message="your message")
	@echo "$(BLUE)Creating migration: $(message)$(NC)"
	alembic revision --autogenerate -m "$(message)"
	@echo "$(GREEN)✓ Migration created$(NC)"

migrate-rollback: ## Rollback last migration
	@echo "$(YELLOW)Rolling back last migration...$(NC)"
	alembic downgrade -1
	@echo "$(GREEN)✓ Rollback complete$(NC)"

# ============================================
# Development
# ============================================

run: ## Run the API server (production mode)
	@echo "$(BLUE)Starting VulnZero API server...$(NC)"
	uvicorn services.api_gateway.main:app --host 0.0.0.0 --port 8000

dev: ## Run the API server (development mode with auto-reload)
	@echo "$(BLUE)Starting VulnZero in development mode...$(NC)"
	uvicorn services.api_gateway.main:app --host 0.0.0.0 --port 8000 --reload

celery-worker: ## Run Celery worker
	@echo "$(BLUE)Starting Celery worker...$(NC)"
	celery -A services.api_gateway.celery_app worker --loglevel=info

celery-beat: ## Run Celery beat scheduler
	@echo "$(BLUE)Starting Celery beat...$(NC)"
	celery -A services.api_gateway.celery_app beat --loglevel=info

web-dev: ## Run frontend development server
	@echo "$(BLUE)Starting web dashboard...$(NC)"
	cd web && npm run dev

# ============================================
# Testing
# ============================================

test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	pytest

test-cov: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	pytest --cov=vulnzero --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)✓ Coverage report generated: htmlcov/index.html$(NC)"

test-watch: ## Run tests in watch mode
	@echo "$(BLUE)Running tests in watch mode...$(NC)"
	pytest-watch

test-fast: ## Run tests in parallel
	@echo "$(BLUE)Running tests in parallel...$(NC)"
	pytest -n auto

# ============================================
# Code Quality
# ============================================

lint: ## Run all linters
	@echo "$(BLUE)Running linters...$(NC)"
	@echo "$(YELLOW)Running flake8...$(NC)"
	flake8 vulnzero/ services/ shared/ tests/
	@echo "$(YELLOW)Running pylint...$(NC)"
	pylint vulnzero/ services/ shared/
	@echo "$(GREEN)✓ Linting complete$(NC)"

format: ## Format code with black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	@echo "$(YELLOW)Running isort...$(NC)"
	isort vulnzero/ services/ shared/ tests/
	@echo "$(YELLOW)Running black...$(NC)"
	black vulnzero/ services/ shared/ tests/
	@echo "$(GREEN)✓ Formatting complete$(NC)"

format-check: ## Check if code is formatted correctly
	@echo "$(BLUE)Checking code formatting...$(NC)"
	isort --check-only vulnzero/ services/ shared/ tests/
	black --check vulnzero/ services/ shared/ tests/

type-check: ## Run type checking with mypy
	@echo "$(BLUE)Running type checks...$(NC)"
	mypy vulnzero/ services/ shared/
	@echo "$(GREEN)✓ Type checking complete$(NC)"

security-check: ## Run security checks with bandit
	@echo "$(BLUE)Running security checks...$(NC)"
	bandit -r vulnzero/ services/ shared/
	@echo "$(GREEN)✓ Security checks complete$(NC)"

check-all: format-check lint type-check security-check test ## Run all checks
	@echo "$(GREEN)✓ All checks passed!$(NC)"

# ============================================
# Docker
# ============================================

docker-up: ## Start all Docker services
	@echo "$(BLUE)Starting Docker services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo "$(YELLOW)Use 'make docker-logs' to view logs$(NC)"

docker-up-api: ## Start Docker services with API
	@echo "$(BLUE)Starting Docker services with API...$(NC)"
	docker-compose --profile api up -d
	@echo "$(GREEN)✓ Services started$(NC)"

docker-up-full: ## Start all Docker services (API + Web + Monitoring)
	@echo "$(BLUE)Starting all Docker services...$(NC)"
	docker-compose --profile api --profile web --profile monitoring --profile tools up -d
	@echo "$(GREEN)✓ All services started$(NC)"
	@echo ""
	@echo "$(YELLOW)Access points:$(NC)"
	@echo "  API: http://localhost:8000"
	@echo "  Web: http://localhost:3000"
	@echo "  Grafana: http://localhost:3001"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  PgAdmin: http://localhost:5050"
	@echo "  Redis Commander: http://localhost:8081"

docker-down: ## Stop all Docker services
	@echo "$(BLUE)Stopping Docker services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

docker-down-volumes: ## Stop Docker services and remove volumes
	@echo "$(RED)⚠ This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		echo "$(GREEN)✓ Services and volumes removed$(NC)"; \
	fi

docker-logs: ## View Docker logs
	@echo "$(BLUE)Viewing Docker logs (Ctrl+C to exit)...$(NC)"
	docker-compose logs -f

docker-logs-api: ## View API logs
	docker-compose logs -f api-gateway

docker-build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker-compose build
	@echo "$(GREEN)✓ Build complete$(NC)"

docker-restart: ## Restart Docker services
	@echo "$(BLUE)Restarting Docker services...$(NC)"
	docker-compose restart
	@echo "$(GREEN)✓ Services restarted$(NC)"

docker-ps: ## Show running Docker containers
	docker-compose ps

# ============================================
# Utilities
# ============================================

shell: ## Open Python shell with app context
	@echo "$(BLUE)Opening Python shell...$(NC)"
	ipython

db-shell: ## Connect to PostgreSQL database
	@echo "$(BLUE)Connecting to database...$(NC)"
	docker-compose exec postgres psql -U vulnzero_user -d vulnzero

redis-cli: ## Connect to Redis CLI
	@echo "$(BLUE)Connecting to Redis...$(NC)"
	docker-compose exec redis redis-cli

generate-secret: ## Generate a secure secret key
	@echo "$(BLUE)Generating secret key...$(NC)"
	@python -c "import secrets; print(secrets.token_urlsafe(32))"

# ============================================
# Documentation
# ============================================

docs: ## Generate documentation
	@echo "$(BLUE)Generating documentation...$(NC)"
	cd docs && mkdocs build
	@echo "$(GREEN)✓ Documentation generated$(NC)"

docs-serve: ## Serve documentation locally
	@echo "$(BLUE)Serving documentation at http://localhost:8001$(NC)"
	cd docs && mkdocs serve -a localhost:8001

# ============================================
# CI/CD
# ============================================

ci: format-check lint type-check security-check test-cov ## Run all CI checks
	@echo "$(GREEN)✓ CI checks passed!$(NC)"

pre-commit: format lint type-check ## Run pre-commit checks
	@echo "$(GREEN)✓ Pre-commit checks passed!$(NC)"
