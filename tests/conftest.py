"""
Pytest configuration and shared fixtures
"""

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
from services.api_gateway.main import app
from services.api_gateway.auth import create_access_token

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
