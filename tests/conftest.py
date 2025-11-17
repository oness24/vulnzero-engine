"""Pytest configuration and shared fixtures."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from vulnzero.shared.models import Base


@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine."""
    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_db_engine):
    """Create a new database session for each test."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = TestingSessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def sample_vulnerability_data():
    """Sample vulnerability data for testing."""
    return {
        "cve_id": "CVE-2024-0001",
        "title": "Test Vulnerability",
        "description": "This is a test vulnerability",
        "severity": "high",
        "cvss_score": 8.5,
        "package_name": "test-package",
        "vulnerable_version": "1.0.0",
        "fixed_version": "1.0.1",
    }


@pytest.fixture
def sample_asset_data():
    """Sample asset data for testing."""
    return {
        "asset_id": "asset-001",
        "hostname": "test-server-01",
        "ip_address": "10.0.1.100",
        "os_type": "ubuntu",
        "os_version": "22.04",
        "asset_type": "server",
    }
