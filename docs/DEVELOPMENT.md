# VulnZero Development Guide

This guide will help you set up your development environment for VulnZero.

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL 15+ (or use Docker)
- Redis 7+ (or use Docker)
- Git

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/oness24/vulnzero-engine.git
cd vulnzero-engine
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
make install-dev
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your configuration
# At minimum, set:
# - OPENAI_API_KEY or ANTHROPIC_API_KEY
# - DATABASE_URL (if not using Docker)
```

### 4. Start Development Services

**Option A: Using Docker Compose (Recommended)**

```bash
# Start all services (PostgreSQL, Redis, API, Celery)
make docker-up

# View logs
make docker-logs

# Stop services
make docker-down
```

**Option B: Manual Setup**

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Run database migrations
make db-upgrade

# Start API server in one terminal
make run-api

# Start Celery worker in another terminal
make run-celery
```

### 5. Initialize Database

```bash
# Create database schema
vulnzero init

# Or using Make
make db-upgrade
```

### 6. Verify Installation

```bash
# Check CLI is working
vulnzero --help

# Check services health
vulnzero check-health

# Run tests
make test
```

## Development Workflow

### Running Tests

```bash
# Run all tests
make test

# Run only unit tests
make test-unit

# Run with coverage
make coverage

# Run specific test file
pytest tests/unit/test_models.py -v
```

### Code Quality

```bash
# Format code (black + isort)
make format

# Run linters
make lint

# Type checking
make type-check

# Security checks
make security-check

# Run all quality checks
make quality
```

### Database Migrations

```bash
# Create a new migration
make migrate
# (You'll be prompted for a message)

# Apply migrations
make db-upgrade

# Rollback last migration
make db-downgrade

# Reset database (WARNING: deletes all data)
make db-reset
```

### Pre-commit Hooks

Pre-commit hooks run automatically before each commit:

```bash
# Install hooks
pre-commit install

# Run manually on all files
make pre-commit

# Skip hooks for a specific commit (not recommended)
git commit --no-verify
```

## Project Structure

```
vulnzero-engine/
├── vulnzero/                 # Main application code
│   ├── services/             # Microservices
│   │   ├── aggregator/       # Vulnerability aggregation
│   │   ├── patch_generator/  # AI patch generation
│   │   ├── testing_engine/   # Digital twin testing
│   │   ├── deployment_engine/# Deployment orchestration
│   │   ├── monitoring/       # Monitoring & rollback
│   │   └── api_gateway/      # REST API
│   ├── shared/               # Shared modules
│   │   ├── models/           # Database models
│   │   ├── utils/            # Utilities
│   │   └── config/           # Configuration
│   └── cli.py                # CLI tool
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── e2e/                  # End-to-end tests
├── infrastructure/           # Infrastructure as code
│   ├── docker/               # Dockerfiles
│   ├── terraform/            # Terraform configs
│   └── kubernetes/           # K8s manifests
├── docs/                     # Documentation
├── scripts/                  # Utility scripts
└── alembic/                  # Database migrations
```

## Common Tasks

### Adding a New Database Model

1. Create model file in `vulnzero/shared/models/`
2. Import in `vulnzero/shared/models/__init__.py`
3. Create migration: `make migrate`
4. Apply migration: `make db-upgrade`
5. Write tests in `tests/unit/test_models.py`

### Adding a New API Endpoint

1. Create/update file in `vulnzero/services/api_gateway/`
2. Define Pydantic models for request/response
3. Implement endpoint logic
4. Write tests in `tests/integration/`
5. Update API documentation

### Adding a New CLI Command

1. Add command to `vulnzero/cli.py`
2. Use Click decorators
3. Add help text and examples
4. Test manually: `vulnzero <command> --help`

## Debugging

### Using IPython

```python
# Add this anywhere in your code
import ipdb; ipdb.set_trace()

# Or use breakpoint() (Python 3.7+)
breakpoint()
```

### Using VS Code

Add to `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "vulnzero.services.api_gateway.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "jinja": true
    }
  ]
}
```

### Viewing Logs

```bash
# Docker logs
docker-compose logs -f api
docker-compose logs -f celery-worker

# Application logs (if running locally)
tail -f logs/vulnzero.log
```

## Environment Variables

Key environment variables (see `.env.example` for complete list):

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | dev/staging/prod | `development` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://...` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `OPENAI_API_KEY` | OpenAI API key | None (required) |
| `ANTHROPIC_API_KEY` | Anthropic API key | None (optional) |
| `JWT_SECRET_KEY` | JWT signing key | Random (change in prod) |

## Troubleshooting

### Database Connection Errors

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check connection
psql -h localhost -U vulnzero -d vulnzero

# Reset database
make db-reset
```

### Import Errors

```bash
# Reinstall in development mode
pip install -e .

# Check PYTHONPATH
echo $PYTHONPATH
```

### Docker Issues

```bash
# Clean up Docker resources
docker-compose down -v
docker system prune -a

# Rebuild images
make docker-build
```

## Contributing

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes
3. Run tests: `make test`
4. Run quality checks: `make quality`
5. Commit: `git commit -m "Add my feature"`
6. Push: `git push origin feature/my-feature`
7. Create Pull Request

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Docker Documentation](https://docs.docker.com/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)

## Getting Help

- Check existing issues: https://github.com/oness24/vulnzero-engine/issues
- Read `IMPROVEMENTS.md` for recommendations
- Review `claude.md` for implementation guidelines

---

Happy coding! 🚀
