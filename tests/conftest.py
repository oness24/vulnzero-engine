"""
Pytest Configuration and Fixtures

Shared fixtures for VulnZero test suite.
"""

import pytest
import os
import sys
import importlib.util
from datetime import datetime, timedelta
from typing import Generator
from unittest.mock import Mock, MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool


from fastapi.testclient import TestClient

# Import models and config
from shared.models.base import Base
from shared.models import (
    Vulnerability, Asset, Patch, Deployment,
    VulnerabilityStatus, AssetType, AssetStatus,
    PatchType, PatchStatus, DeploymentStatus, DeploymentStrategy
)
from shared.config.settings import Settings


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """
    Create a test database session.

    Uses in-memory SQLite for fast tests.
    """
    # Create in-memory SQLite database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db: Session) -> Session:
    """Alias for test_db fixture"""
    return test_db


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_vulnerability(test_db: Session) -> Vulnerability:
    """Create a sample vulnerability"""
    vuln = Vulnerability(
        cve_id="CVE-2024-12345",
        title="Sample SQL Injection Vulnerability",
        description="A critical SQL injection vulnerability in web application",
        severity="critical",
        cvss_score=9.8,
        status=VulnerabilityStatus.NEW,
        discovered_at=datetime.utcnow(),
        affected_package="webapp",
        affected_version="1.0.0",
        fixed_version="1.0.1",
        priority_score=95.5,
        scanner_source="manual",
        raw_data={"test": "data"}
    )
    test_db.add(vuln)
    test_db.commit()
    test_db.refresh(vuln)
    return vuln


@pytest.fixture
def sample_asset(test_db: Session) -> Asset:
    """Create a sample asset"""
    asset = Asset(
        asset_id="asset-fixture-001",
        name="Test Server 01",
        hostname="test-server-01",
        ip_address="192.168.1.100",
        type=AssetType.SERVER,
        status=AssetStatus.ACTIVE,
        os_type="Ubuntu",
        os_version="22.04",
        asset_metadata={"environment": "test", "region": "us-east-1"}
    )
    test_db.add(asset)
    test_db.commit()
    test_db.refresh(asset)
    return asset


@pytest.fixture
def sample_patch(test_db: Session, sample_vulnerability: Vulnerability) -> Patch:
    """Create a sample patch"""
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        title="Fix for CVE-2024-12345",
        description="Patch to fix SQL injection",
        patch_type=PatchType.SCRIPT_EXECUTION,
        patch_content="#!/bin/bash\napt-get update && apt-get install -y webapp=1.0.1",
        rollback_script="#!/bin/bash\napt-get install -y webapp=1.0.0",
        status=PatchStatus.GENERATED,
        confidence_score=85.5,
        validation_passed=True,
        llm_provider="openai",
        llm_model="gpt-4"
    )
    test_db.add(patch)
    test_db.commit()
    test_db.refresh(patch)
    return patch


@pytest.fixture
def sample_deployment(test_db: Session, sample_patch: Patch, sample_asset: Asset) -> Deployment:
    """Create a sample deployment"""
    deployment = Deployment(
        deployment_id="deploy-fixture-001",
        patch_id=sample_patch.id,
        asset_id=sample_asset.id,
        strategy=DeploymentStrategy.ROLLING,
        deployment_method="ansible",
        status=DeploymentStatus.PENDING
    )
    test_db.add(deployment)
    test_db.commit()
    test_db.refresh(deployment)
    return deployment


# =============================================================================
# API Fixtures
# =============================================================================

@pytest.fixture
def api_client() -> TestClient:
    """
    Create FastAPI test client.

    Note: Imports here to avoid circular dependencies
    """
    from services.api_gateway.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict:
    """Generate authentication headers with mock JWT token"""
    # For testing, use a mock token
    # In real tests, you'd generate a valid JWT
    return {
        "Authorization": "Bearer mock-jwt-token-for-testing"
    }


@pytest.fixture
def admin_user() -> dict:
    """Mock admin user data"""
    return {
        "id": 1,
        "email": "admin@test.com",
        "role": "admin",
        "is_active": True
    }


@pytest.fixture
def operator_user() -> dict:
    """Mock operator user data"""
    return {
        "id": 2,
        "email": "operator@test.com",
        "role": "operator",
        "is_active": True
    }


# =============================================================================
# Mock External Services
# =============================================================================

@pytest.fixture
def mock_openai():
    """Mock OpenAI API"""
    with patch('openai.OpenAI') as mock:
        # Mock response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="mocked patch content"))]
        mock_response.usage = Mock(total_tokens=100)

        mock.return_value.chat.completions.create.return_value = mock_response
        yield mock


@pytest.fixture
def mock_anthropic():
    """Mock Anthropic API"""
    with patch('anthropic.Anthropic') as mock:
        # Mock response
        mock_response = Mock()
        mock_response.content = [Mock(text="mocked patch content")]
        mock_response.usage = Mock(input_tokens=50, output_tokens=50)

        mock.return_value.messages.create.return_value = mock_response
        yield mock


@pytest.fixture
def mock_docker():
    """Mock Docker client"""
    with patch('docker.from_env') as mock:
        mock_client = MagicMock()
        mock_container = MagicMock()

        # Mock container methods
        mock_container.id = "test-container-id"
        mock_container.status = "running"
        mock_container.exec_run.return_value = (0, b"success")

        mock_client.containers.create.return_value = mock_container
        mock_client.containers.get.return_value = mock_container

        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_celery():
    """Mock Celery task"""
    with patch('celery.Task.delay') as mock:
        mock_task = Mock()
        mock_task.id = "test-task-id"
        mock.return_value = mock_task
        yield mock


@pytest.fixture
def mock_subprocess():
    """Mock subprocess for Ansible execution"""
    with patch('subprocess.run') as mock:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Ansible playbook executed successfully"
        mock_result.stderr = ""

        mock.return_value = mock_result
        yield mock


@pytest.fixture
def mock_psutil():
    """Mock psutil for system metrics"""
    with patch('psutil.cpu_percent') as cpu_mock, \
         patch('psutil.virtual_memory') as mem_mock, \
         patch('psutil.disk_usage') as disk_mock, \
         patch('psutil.net_io_counters') as net_mock:

        # Mock CPU
        cpu_mock.return_value = 50.0

        # Mock Memory
        mem_mock.return_value = Mock(
            percent=60.0,
            available=4 * 1024 ** 3  # 4 GB
        )

        # Mock Disk
        disk_mock.return_value = Mock(
            percent=70.0,
            free=100 * 1024 ** 3  # 100 GB
        )

        # Mock Network
        net_mock.return_value = Mock(
            bytes_sent=1000000,
            bytes_recv=2000000
        )

        yield {
            'cpu': cpu_mock,
            'memory': mem_mock,
            'disk': disk_mock,
            'network': net_mock
        }


# =============================================================================
# Configuration Fixtures
# =============================================================================

@pytest.fixture
def test_settings() -> Settings:
    """Create test settings"""
    return Settings(
        DATABASE_URL="sqlite:///:memory:",
        JWT_SECRET_KEY="test-secret-key",
        JWT_ALGORITHM="HS256",
        OPENAI_API_KEY="test-openai-key",
        ANTHROPIC_API_KEY="test-anthropic-key",
    )


# =============================================================================
# Helper Fixtures
# =============================================================================

@pytest.fixture
def freeze_time():
    """Freeze time for testing"""
    fixed_time = datetime(2024, 1, 1, 12, 0, 0)
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value = fixed_time
        mock_datetime.now.return_value = fixed_time
        yield fixed_time


@pytest.fixture
def sample_patch_script() -> str:
    """Sample bash patch script"""
    return """#!/bin/bash
set -e

# Update package lists
apt-get update

# Install security update
apt-get install -y webapp=1.0.1

# Restart service
systemctl restart webapp

echo "Patch applied successfully"
"""


@pytest.fixture
def sample_rollback_script() -> str:
    """Sample bash rollback script"""
    return """#!/bin/bash
set -e

# Rollback to previous version
apt-get install -y webapp=1.0.0

# Restart service
systemctl restart webapp

echo "Rollback completed successfully"
"""


# =============================================================================
# Cleanup Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Cleanup temporary files after each test"""
    yield
    # Cleanup code here if needed
    pass


# =============================================================================
# Pytest Hooks
# =============================================================================

def pytest_configure(config):
    """Configure pytest"""
    # Set environment variables for testing
    os.environ['TESTING'] = 'true'
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['JWT_SECRET_KEY'] = 'test-secret-key'


def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    # Add markers automatically based on test location
    for item in items:
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


# =============================================================================
# Async Test Fixtures (Additional)
# =============================================================================

import asyncio
from typing import AsyncGenerator, Generator
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from shared.models.database import Base, get_db
from shared.models.models import (
    Vulnerability,
    Asset,
    Patch,
    Deployment,
    VulnerabilityStatus,
    VulnerabilitySeverity,
    AssetType,
    TestStatus,
    DeploymentStatus,
    DeploymentMethod,
)
from api.main import app
from api.routes.auth import create_access_token

# Test database URL (use in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine():
    """Create a test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session"""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client with database dependency override"""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def admin_token() -> str:
    """Create an admin JWT token for testing"""
    token_data = {
        "sub": "test_admin",
        "user_id": 1,
        "role": "admin",
    }
    return create_access_token(token_data)


@pytest.fixture
def operator_token() -> str:
    """Create an operator JWT token for testing"""
    token_data = {
        "sub": "test_operator",
        "user_id": 2,
        "role": "operator",
    }
    return create_access_token(token_data)


@pytest.fixture
def viewer_token() -> str:
    """Create a viewer JWT token for testing"""
    token_data = {
        "sub": "test_viewer",
        "user_id": 3,
        "role": "viewer",
    }
    return create_access_token(token_data)


@pytest.fixture
def auth_headers(admin_token: str) -> dict:
    """Create authorization headers with admin token"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
async def sample_vulnerability(db_session: AsyncSession) -> Vulnerability:
    """Create a sample vulnerability for testing"""
    vulnerability = Vulnerability(
        cve_id="CVE-2024-0001",
        title="Test SQL Injection Vulnerability",
        description="A critical SQL injection vulnerability in test application",
        severity=VulnerabilitySeverity.CRITICAL,
        status=VulnerabilityStatus.NEW,
        cvss_score=9.8,
        cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        affected_package="test-package",
        vulnerable_version="1.0.0",
        fixed_version="1.0.1",
        priority_score=95.0,
        exploit_available=True,
    )
    db_session.add(vulnerability)
    await db_session.commit()
    await db_session.refresh(vulnerability)
    return vulnerability


@pytest.fixture
async def sample_asset(db_session: AsyncSession) -> Asset:
    """Create a sample asset for testing"""
    asset = Asset(
        asset_id="asset-001",
        type=AssetType.SERVER,
        hostname="test-server-01",
        ip_address="192.168.1.100",
        os_type="Ubuntu",
        os_version="22.04",
        os_architecture="x86_64",
        criticality=8,
        environment="production",
        is_active=True,
    )
    db_session.add(asset)
    await db_session.commit()
    await db_session.refresh(asset)
    return asset


@pytest.fixture
async def sample_patch(db_session: AsyncSession, sample_vulnerability: Vulnerability) -> Patch:
    """Create a sample patch for testing"""
    patch = Patch(
        patch_id="patch-001",
        vulnerability_id=sample_vulnerability.id,
        patch_type="script",
        patch_content="#!/bin/bash\napt-get update && apt-get install test-package=1.0.1",
        rollback_content="#!/bin/bash\napt-get install test-package=1.0.0",
        llm_provider="openai",
        llm_model="gpt-4",
        confidence_score=0.95,
        validation_passed=True,
        test_status=TestStatus.PASSED,
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)
    return patch


@pytest.fixture
async def sample_deployment(
    db_session: AsyncSession,
    sample_patch: Patch,
    sample_asset: Asset,
) -> Deployment:
    """Create a sample deployment for testing"""
    deployment = Deployment(
        deployment_id="deploy-001",
        patch_id=sample_patch.id,
        asset_id=sample_asset.id,
        deployment_method=DeploymentMethod.ANSIBLE,
        deployment_strategy="canary",
        status=DeploymentStatus.PENDING,
    )
    db_session.add(deployment)
    await db_session.commit()
    await db_session.refresh(deployment)
    return deployment


@pytest.fixture
async def multiple_vulnerabilities(db_session: AsyncSession) -> list[Vulnerability]:
    """Create multiple vulnerabilities for testing listing/filtering"""
    vulnerabilities = [
        Vulnerability(
            cve_id=f"CVE-2024-000{i}",
            title=f"Test Vulnerability {i}",
            description=f"Description for vulnerability {i}",
            severity=severity,
            status=VulnerabilityStatus.NEW,
            cvss_score=score,
            priority_score=score * 10,
        )
        for i, (severity, score) in enumerate(
            [
                (VulnerabilitySeverity.CRITICAL, 9.5),
                (VulnerabilitySeverity.HIGH, 7.8),
                (VulnerabilitySeverity.MEDIUM, 5.5),
                (VulnerabilitySeverity.LOW, 3.2),
                (VulnerabilitySeverity.CRITICAL, 9.0),
            ],
            start=1,
        )
    ]

    for vuln in vulnerabilities:
        db_session.add(vuln)

    await db_session.commit()

    for vuln in vulnerabilities:
        await db_session.refresh(vuln)

    return vulnerabilities
