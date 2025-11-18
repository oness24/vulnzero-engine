# VulnZero CI/CD Pipeline Guide

## Overview

This document explains the Continuous Integration and Continuous Deployment (CI/CD) pipeline for the VulnZero platform.

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitHub Actions CI/CD                      │
└─────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
            ┌───────▼────────┐       ┌───────▼────────┐
            │  Backend Jobs  │       │ Frontend Jobs  │
            └───────┬────────┘       └───────┬────────┘
                    │                         │
        ┌───────────┼───────────┐  ┌─────────┼─────────┐
        │           │           │  │         │         │
    ┌───▼───┐  ┌───▼───┐  ┌───▼──▼──┐  ┌───▼───┐ ┌───▼────┐
    │ Lint  │  │ Tests │  │Security│  │ Tests │ │ Build  │
    └───┬───┘  └───┬───┘  └───┬────┘  └───┬───┘ └───┬────┘
        │          │          │           │         │
        └──────────┴──────────┴───────────┴─────────┘
                              │
                    ┌─────────▼──────────┐
                    │ Integration Check  │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │   Docker Build     │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │ Deploy (on main)   │
                    └────────────────────┘
```

---

## Jobs Breakdown

### 1. Backend Linting (`backend-lint`)

**Purpose:** Ensure Python code quality and consistency

**Tools:**
- **ruff**: Fast Python linter
- **black**: Code formatter (check-only mode)
- **isort**: Import statement organizer
- **mypy**: Static type checker

**Configuration:**
- Config: `pyproject.toml`
- Line length: 100 characters
- Target: Python 3.11+

**Run Time:** ~1 minute

---

### 2. Backend Tests (`backend-tests`)

**Purpose:** Run comprehensive test suite with coverage

**Services:**
- PostgreSQL 15
- Redis 7

**Coverage Targets:**
- Minimum: 80%
- Threshold: 2%
- Modules: `api/`, `services/`, `shared/`

**Test Configuration:**
```ini
[tool.pytest.ini_options]
minversion = "7.0"
addopts = [
    "-ra",
    "-q",
    "--strict-markers",
    "--cov=api",
    "--cov=services",
    "--cov=shared",
    "--cov-report=xml",
    "--cov-report=html",
]
```

**Artifacts:**
- Coverage report (XML for Codecov)
- HTML coverage report

**Run Time:** ~3-5 minutes

---

### 3. Frontend Linting (`frontend-lint`)

**Purpose:** Ensure JavaScript/React code quality

**Tools:**
- ESLint with React plugin
- Prettier (via ESLint)

**Configuration:**
- Config: `web/.eslintrc.js`
- Parser: Babel ESLint
- Rules: React best practices

**Run Time:** ~1 minute

---

### 4. Frontend Tests (`frontend-tests`)

**Purpose:** Run component and integration tests

**Framework:** Vitest + React Testing Library

**Coverage Targets:**
- Minimum: 80%
- Test files: `**/*.test.{js,jsx}`

**Test Categories:**
- Unit tests: Individual components
- Integration tests: Page components with API mocking
- E2E tests: Full user workflows (Playwright)

**Artifacts:**
- Coverage report (JSON for Codecov)
- Test results

**Run Time:** ~2-3 minutes

---

### 5. Frontend Build (`frontend-build`)

**Purpose:** Verify production build succeeds

**Build Tool:** Vite

**Environment:**
```env
VITE_API_BASE_URL=https://api.vulnzero.example.com
VITE_WS_BASE_URL=https://api.vulnzero.example.com
VITE_ENVIRONMENT=production
```

**Build Checks:**
- Size analysis
- Largest files report
- Build artifact validation

**Artifacts:**
- Production bundle (`dist/`)

**Run Time:** ~1-2 minutes

---

### 6. Security Scanning (`security-scan`)

**Purpose:** Detect vulnerabilities in dependencies

**Tool:** Trivy

**Scan Type:** Filesystem scan
**Severity:** CRITICAL, HIGH

**Output:**
- SARIF format
- Uploaded to GitHub Security tab

**Run Time:** ~2 minutes

---

### 7. Integration Check (`integration-check`)

**Purpose:** Ensure all required jobs passed

**Dependencies:**
- backend-lint
- backend-tests
- frontend-lint
- frontend-tests
- frontend-build
- security-scan

**Behavior:**
- Runs even if previous jobs fail (`if: always()`)
- Fails CI if any required job failed
- Allows optional jobs to fail (linting with `continue-on-error`)

---

### 8. Docker Build (`docker-build`)

**Purpose:** Build production Docker image

**Trigger:** Only on `main` branch push

**Features:**
- Multi-stage build (builder + runtime)
- Non-root user (vulnzero:1000)
- Health check included
- Optimized layer caching

**Image Tags:**
- `branch-<sha>`: Git SHA
- `latest`: Most recent main build
- `v1.2.3`: Semantic version tags

**Run Time:** ~3-5 minutes

---

### 9. Deploy Notification (`deploy-notification`)

**Purpose:** Notify team of successful deployment

**Trigger:** Only after successful Docker build on `main`

**Future Enhancements:**
- Slack notification
- Discord webhook
- Email notification
- Deployment tracking

---

## Workflow Triggers

### Push to Main/Develop
```yaml
on:
  push:
    branches: [main, develop]
```

**Runs:** All jobs including Docker build (main only)

### Pull Request
```yaml
on:
  pull_request:
    branches: [main, develop]
```

**Runs:** All jobs except Docker build and deployment

---

## Code Coverage

### Codecov Integration

**Configuration:** `codecov.yml`

**Targets:**
- Project: 80% (threshold: 2%)
- Patch: 80% (threshold: 5%)

**Flags:**
- `backend`: Python code coverage
- `frontend`: JavaScript code coverage

**Reports:**
- Comment on PRs with coverage diff
- Show coverage trends
- File-level coverage view

### Coverage Exclusions
- Test files
- `__init__.py`
- Migrations
- Generated files

---

## Environment Variables

### Required Secrets

#### Backend Tests
```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/vulnzero_test
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=test-key-not-real
ANTHROPIC_API_KEY=test-key-not-real
SECRET_KEY=test-secret-key-for-ci
```

#### Docker Registry (Optional)
```bash
DOCKER_USERNAME=your-dockerhub-username
DOCKER_PASSWORD=your-dockerhub-password
```

### Frontend Environment Variables
```bash
VITE_API_BASE_URL=https://api.vulnzero.example.com
VITE_WS_BASE_URL=https://api.vulnzero.example.com
VITE_ENVIRONMENT=production
```

---

## Local Development

### Run Backend Tests Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests with coverage
pytest --cov=api --cov=services --cov=shared --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Run Frontend Tests Locally
```bash
# Install dependencies
cd web
npm install

# Run tests
npm test

# Run tests with coverage
npm test -- --coverage

# Run tests in watch mode
npm test -- --watch
```

### Run Linters Locally

**Backend:**
```bash
# Run ruff
ruff check .

# Check formatting with black
black --check .

# Check imports with isort
isort --check-only .

# Run type checker
mypy . --ignore-missing-imports
```

**Frontend:**
```bash
cd web

# Run ESLint
npm run lint

# Fix linting issues
npm run lint -- --fix
```

### Build Docker Image Locally
```bash
# Build image
docker build -t vulnzero:local .

# Run container
docker run -p 8000:8000 vulnzero:local

# Test health endpoint
curl http://localhost:8000/health
```

---

## Troubleshooting

### Backend Tests Failing

**Issue:** Database connection errors

**Solution:**
```bash
# Ensure PostgreSQL is running
docker run -d -p 5432:5432 \
  -e POSTGRES_PASSWORD=postgres \
  postgres:15

# Ensure Redis is running
docker run -d -p 6379:6379 redis:7
```

**Issue:** Import errors

**Solution:**
```bash
# Verify PYTHONPATH
export PYTHONPATH=/path/to/vulnzero-engine:$PYTHONPATH

# Or use pytest with explicit path
python -m pytest tests/
```

### Frontend Tests Failing

**Issue:** Module not found errors

**Solution:**
```bash
# Clear node_modules and reinstall
rm -rf web/node_modules
rm web/package-lock.json
cd web && npm install
```

**Issue:** Tests timing out

**Solution:**
```javascript
// Increase timeout in test
it('long running test', async () => {
  // ...
}, 10000) // 10 seconds
```

### Docker Build Failing

**Issue:** Context too large

**Solution:**
```bash
# Verify .dockerignore is working
docker build --no-cache -t vulnzero:test .

# Check context size
du -sh .
```

**Issue:** Layer caching not working

**Solution:**
```bash
# Clear build cache
docker builder prune -a

# Rebuild without cache
docker build --no-cache -t vulnzero:local .
```

---

## Performance Optimization

### Caching Strategy

1. **Pip Dependencies:** Cached by GitHub Actions
2. **npm Dependencies:** Cached by GitHub Actions
3. **Docker Layers:** Cached via GitHub Actions cache

### Parallel Execution

Jobs run in parallel where possible:
- Backend lint + tests run simultaneously with frontend jobs
- All jobs complete before integration check
- Docker build only runs after integration check passes

### Estimated Total Run Time

**Full Pipeline (PR):**
- Linting: 1-2 minutes (parallel)
- Tests: 3-5 minutes (parallel)
- Build: 1-2 minutes
- Security: 2 minutes
- **Total: ~5-7 minutes**

**Full Pipeline (Main branch):**
- All PR jobs: 5-7 minutes
- Docker build: 3-5 minutes
- **Total: ~8-12 minutes**

---

## Future Enhancements

### Week 2
- [ ] Add E2E tests with Playwright
- [ ] Implement deployment to staging environment
- [ ] Add performance regression testing

### Week 3+
- [ ] Kubernetes deployment
- [ ] Blue-green deployments
- [ ] Automatic rollback on failure
- [ ] Load testing in CI
- [ ] Visual regression testing

---

## Monitoring and Alerts

### GitHub Actions Status

View status: `https://github.com/<org>/<repo>/actions`

### Codecov Dashboard

View coverage: `https://codecov.io/gh/<org>/<repo>`

### Security Alerts

View: Repository → Security → Code scanning alerts

---

**Last Updated:** 2025-11-18
**Maintained by:** VulnZero DevOps Team
