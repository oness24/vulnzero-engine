"""
Pytest Configuration and Fixtures

Shared fixtures for VulnZero test suite.
"""

import pytest
import os
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
    PatchType, PatchStatus, DeploymentStatus
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
def sample_deployment(test_db: Session, sample_patch: Patch) -> Deployment:
    """Create a sample deployment"""
    deployment = Deployment(
        patch_id=sample_patch.id,
        strategy="rolling",
        status=DeploymentStatus.PENDING,
        total_assets=10,
        successful_assets=0,
        failed_assets=0
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
