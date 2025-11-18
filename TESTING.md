# VulnZero Testing Guide

## Test Structure

```
tests/
├── conftest.py                 # Pytest configuration and shared fixtures
├── test_config.py              # Configuration module tests
├── test_models.py              # Database model tests
├── test_schemas.py             # Pydantic schema validation tests
└── api/
    ├── test_auth.py            # Authentication endpoint tests
    ├── test_vulnerabilities.py # Vulnerability management tests
    ├── test_assets.py          # Asset management tests
    ├── test_patches.py         # Patch management tests
    ├── test_deployments.py     # Deployment management tests
    └── test_system.py          # System health and metrics tests
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
@pytest.mark.unit
@pytest.mark.integration
@pytest.mark.slow
```

Run specific markers:
```bash
pytest -m unit
pytest -m "not slow"
```
