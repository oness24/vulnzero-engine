# VulnZero Testing Guide

## Test Structure

```
tests/
├── conftest.py                 # Pytest configuration and shared fixtures
├── test_config.py              # Configuration module tests
├── test_models.py              # Database model tests
├── test_schemas.py             # Pydantic schema validation tests
├── api/
│   ├── test_auth.py            # Authentication endpoint tests
│   ├── test_vulnerabilities.py # Vulnerability management tests
│   ├── test_assets.py          # Asset management tests
│   ├── test_patches.py         # Patch management tests
│   ├── test_deployments.py     # Deployment management tests
│   └── test_system.py          # System health and metrics tests
├── security/                   # Security-focused tests
│   ├── test_authentication.py  # Auth security tests
│   ├── test_sql_injection.py   # SQL injection prevention
│   ├── test_security_headers.py # Security headers middleware (40+ tests)
│   └── test_llm_sanitizer.py   # LLM prompt injection sanitizer (50+ tests)
├── integration/                # Integration tests
│   ├── test_end_to_end.py      # E2E workflow tests
│   ├── test_service_integration.py
│   └── test_security_integration.py # Security feature integration
└── unit/                       # Unit tests organized by module
    ├── api/                    # API unit tests
    ├── models/                 # Model unit tests
    ├── services/               # Service unit tests
    └── shared/                 # Shared module unit tests
        ├── middleware/         # Middleware tests
        └── utils/              # Utility tests
```

## Running Tests

### Run All Tests
```bash
make test
```

### Run Specific Test Files
```bash
pytest tests/test_config.py -v
pytest tests/api/test_auth.py -v
```

### Run with Coverage
```bash
make coverage
```

### Run Specific Test Markers
```bash
pytest -m unit              # Run only unit tests
pytest -m integration       # Run only integration tests
```

## Test Coverage

### Configuration Tests (test_config.py)
- ✅ Default values validation
- ✅ Custom values configuration
- ✅ Deployment strategy validation
- ✅ CORS origins parsing
- ✅ Allowed hosts parsing
- ✅ LLM configuration
- ✅ Feature flags

### Database Model Tests (test_models.py)
- ✅ Vulnerability CRUD operations
- ✅ Vulnerability uniqueness constraints
- ✅ Asset creation and management
- ✅ Asset-Vulnerability relationships
- ✅ Patch creation and validation
- ✅ Confidence score range validation
- ✅ Deployment creation
- ✅ Deployment relationships
- ✅ Audit log creation
- ✅ Remediation job creation
- ✅ Cascade delete operations

### Pydantic Schema Tests (test_schemas.py)
- ✅ VulnerabilityCreate validation
- ✅ CVSS score range validation
- ✅ AssetCreate validation
- ✅ Criticality range validation
- ✅ Partial updates support
- ✅ Patch approval/rejection schemas
- ✅ Deployment rollback schema
- ✅ User login schema
- ✅ Pagination and filtering schemas
- ✅ ORM model conversion

### Authentication Tests (api/test_auth.py)
- ✅ JWT access token creation
- ✅ JWT refresh token creation
- ✅ Token validation and decoding
- ✅ Invalid token handling
- ✅ Successful login
- ✅ Invalid credentials rejection
- ✅ Token refresh flow
- ✅ Invalid refresh token handling
- ✅ Logout functionality
- ✅ Protected endpoint access control
- ✅ Role-based authorization

### Vulnerability API Tests (api/test_vulnerabilities.py)
- ✅ List vulnerabilities (empty and with data)
- ✅ Pagination support
- ✅ Filter by severity
- ✅ Filter by CVSS score
- ✅ Get specific vulnerability
- ✅ Not found handling
- ✅ Create new vulnerability
- ✅ Duplicate CVE ID prevention
- ✅ Update vulnerability
- ✅ Get vulnerability statistics
- ✅ Trigger manual scan
- ✅ Authentication requirements
- ✅ Role-based access control

### Asset API Tests (api/test_assets.py)
- ✅ List assets
- ✅ Filter by type
- ✅ Get specific asset
- ✅ Not found handling
- ✅ Create new asset
- ✅ Duplicate asset_id prevention
- ✅ Update asset
- ✅ Get asset vulnerabilities

### Patch API Tests (api/test_patches.py)
- ✅ List patches
- ✅ Filter by test status
- ✅ Get specific patch
- ✅ Not found handling
- ✅ Approve patch
- ✅ Reject approval for untested patches
- ✅ Reject patch

### Deployment API Tests (api/test_deployments.py)
- ✅ List deployments
- ✅ Filter by status
- ✅ Filter by asset
- ✅ Get specific deployment
- ✅ Not found handling
- ✅ Rollback successful deployment
- ✅ Prevent rollback for invalid statuses
- ✅ Prevent duplicate rollbacks

### System API Tests (api/test_system.py)
- ✅ Health check endpoint
- ✅ Database health status
- ✅ Metrics endpoint
- ✅ Metrics authentication
- ✅ Root endpoint

### Security Headers Tests (security/test_security_headers.py) **NEW**
- ✅ Development mode CSP (permissive for HMR)
- ✅ Production mode CSP (strict, no unsafe-inline/eval)
- ✅ HSTS header (production only, 1-year max-age)
- ✅ X-Frame-Options (DENY for clickjacking prevention)
- ✅ X-Content-Type-Options (nosniff for MIME-sniffing prevention)
- ✅ Referrer-Policy (strict-origin-when-cross-origin)
- ✅ Permissions-Policy (restricts dangerous features)
- ✅ X-XSS-Protection (1; mode=block)
- ✅ Headers applied to all endpoints (including errors)
- ✅ Headers applied to JSON responses
- ✅ Headers applied to multiple requests
- ✅ No duplicate headers
- ✅ Environment-aware configuration
- **Coverage**: 100% (40+ test cases)

### LLM Sanitizer Tests (security/test_llm_sanitizer.py) **NEW**
- ✅ Instruction override detection
- ✅ System impersonation detection
- ✅ Role manipulation detection
- ✅ Instruction leak detection
- ✅ Jailbreak attempt detection (DAN mode, evil mode, etc.)
- ✅ Code execution detection (exec, eval, __import__)
- ✅ Command injection detection (shell metacharacters)
- ✅ SQL injection detection (' OR 1=1--, etc.)
- ✅ Path traversal detection (../../etc/passwd)
- ✅ XSS/HTML injection detection
- ✅ False positive prevention (legitimate vuln descriptions)
- ✅ Sanitization levels (Permissive, Moderate, Strict)
- ✅ Length truncation (10,000 char max)
- ✅ Unicode character handling
- ✅ Special character handling
- ✅ Multiple pattern detection
- ✅ Parameterized tests for all attack types
- **Coverage**: 95%+ (50+ test cases)

### Security Integration Tests (integration/test_security_integration.py) **NEW**
- ✅ Security headers on all endpoints
- ✅ LLM injection blocking
- ✅ Legitimate request allowance
- ✅ Headers persist through LLM processing
- ✅ Multiple security layers working together
- ✅ Headers on error responses
- ✅ No information leakage in errors
- ✅ Concurrent request handling
- ✅ Security overhead measurement
- ✅ Defense-in-depth validation (sanitization + CSP)
- **Coverage**: End-to-end security workflows

## Fixtures Available

### Database Fixtures
- `test_engine` - Test database engine (SQLite in-memory)
- `db_session` - Async database session
- `client` - HTTP test client with database override

### Authentication Fixtures
- `admin_token` - Admin JWT token
- `operator_token` - Operator JWT token
- `viewer_token` - Viewer JWT token
- `auth_headers` - Authorization headers with admin token

### Data Fixtures
- `sample_vulnerability` - Single test vulnerability
- `sample_asset` - Single test asset
- `sample_patch` - Single test patch
- `sample_deployment` - Single test deployment
- `multiple_vulnerabilities` - List of 5 test vulnerabilities

## Test Database

Tests use SQLite in-memory database for:
- **Speed**: No disk I/O
- **Isolation**: Each test gets fresh database
- **Simplicity**: No setup required

## Writing New Tests

### Example: Testing a new endpoint

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_my_endpoint(client: AsyncClient, auth_headers: dict):
    """Test description"""
    response = await client.get("/api/v1/my-endpoint", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "expected_field" in data
```

### Example: Testing with database

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from shared.models.models import MyModel

@pytest.mark.asyncio
async def test_my_model(db_session: AsyncSession):
    """Test description"""
    obj = MyModel(name="test")
    db_session.add(obj)
    await db_session.commit()
    await db_session.refresh(obj)

    assert obj.id is not None
```

## Continuous Integration

Tests run automatically on:
- Pull requests
- Pushes to main branch
- Manual workflow dispatch

CI pipeline:
1. Install dependencies
2. Run linters (ruff, mypy)
3. Run tests with coverage
4. Generate coverage report
5. Upload to Codecov (if configured)

## Coverage Goals

- **Unit Tests**: >80% coverage
- **Integration Tests**: All critical workflows
- **E2E Tests**: Top user journeys (future)

## Test Markers

Mark tests with pytest markers:
```python
@pytest.mark.unit          # Unit tests
@pytest.mark.integration   # Integration tests
@pytest.mark.security      # Security tests **NEW**
@pytest.mark.slow          # Slow-running tests
@pytest.mark.requires_llm  # Requires LLM API keys
@pytest.mark.requires_db   # Requires database
@pytest.mark.requires_docker # Requires Docker
```

Run specific markers:
```bash
# Run only unit tests
pytest -m unit

# Run only security tests
pytest -m security

# Skip slow tests
pytest -m "not slow"

# Skip tests requiring LLM API keys
pytest -m "not requires_llm"

# Run security and integration tests
pytest -m "security or integration"
```
