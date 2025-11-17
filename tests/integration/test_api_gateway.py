"""Integration tests for VulnZero API Gateway."""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from vulnzero.services.api_gateway.main import app
from vulnzero.shared.database import get_db, Base
from vulnzero.shared.models import (
    Patch,
    PatchStatus,
    Vulnerability,
    VulnerabilityStatus,
)


# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def test_db():
    """Create test database for each test."""
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_vulnerability(test_db):
    """Create a sample vulnerability for testing."""
    vuln = Vulnerability(
        cve_id="CVE-2023-TEST",
        title="Test Vulnerability",
        description="This is a test vulnerability",
        severity="high",
        cvss_score=7.5,
        status=VulnerabilityStatus.NEW,
        package_name="test-package",
        vulnerable_version="1.0.0",
        fixed_version="1.0.1",
    )
    test_db.add(vuln)
    test_db.commit()
    test_db.refresh(vuln)
    return vuln


@pytest.fixture
def sample_patch(test_db, sample_vulnerability):
    """Create a sample patch for testing."""
    patch = Patch(
        patch_id="PATCH-TEST-001",
        vulnerability_id=sample_vulnerability.id,
        patch_content="#!/bin/bash\necho 'Test patch'",
        rollback_script="#!/bin/bash\necho 'Test rollback'",
        status=PatchStatus.GENERATED,
        confidence_score=0.85,
        llm_model="gpt-4",
    )
    test_db.add(patch)
    test_db.commit()
    test_db.refresh(patch)
    return patch


# Health Check Tests


@pytest.mark.integration
def test_health_check(client):
    """Test basic health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "VulnZero API Gateway"
    assert "timestamp" in data


@pytest.mark.integration
def test_database_health(client, test_db):
    """Test database health check."""
    response = client.get("/api/v1/health/database")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["component"] == "database"


@pytest.mark.integration
def test_readiness_check(client, test_db):
    """Test readiness probe."""
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


@pytest.mark.integration
def test_liveness_check(client):
    """Test liveness probe."""
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


# Vulnerability Tests


@pytest.mark.integration
def test_list_vulnerabilities_empty(client, test_db):
    """Test listing vulnerabilities when database is empty."""
    response = client.get("/api/v1/vulnerabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["vulnerabilities"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20


@pytest.mark.integration
def test_list_vulnerabilities(client, sample_vulnerability):
    """Test listing vulnerabilities."""
    response = client.get("/api/v1/vulnerabilities")
    assert response.status_code == 200
    data = response.json()
    assert len(data["vulnerabilities"]) == 1
    assert data["total"] == 1

    vuln = data["vulnerabilities"][0]
    assert vuln["cve_id"] == "CVE-2023-TEST"
    assert vuln["severity"] == "high"
    assert vuln["cvss_score"] == 7.5


@pytest.mark.integration
def test_list_vulnerabilities_filter_by_severity(client, sample_vulnerability):
    """Test filtering vulnerabilities by severity."""
    response = client.get("/api/v1/vulnerabilities?severity=high")
    assert response.status_code == 200
    data = response.json()
    assert len(data["vulnerabilities"]) == 1

    response = client.get("/api/v1/vulnerabilities?severity=critical")
    assert response.status_code == 200
    data = response.json()
    assert len(data["vulnerabilities"]) == 0


@pytest.mark.integration
def test_list_vulnerabilities_pagination(client, test_db):
    """Test vulnerability pagination."""
    # Create multiple vulnerabilities
    for i in range(25):
        vuln = Vulnerability(
            cve_id=f"CVE-2023-{i:04d}",
            title=f"Test Vulnerability {i}",
            description=f"Description {i}",
            severity="medium",
            status=VulnerabilityStatus.NEW,
        )
        test_db.add(vuln)
    test_db.commit()

    # Get first page
    response = client.get("/api/v1/vulnerabilities?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["vulnerabilities"]) == 10
    assert data["total"] == 25
    assert data["page"] == 1

    # Get second page
    response = client.get("/api/v1/vulnerabilities?page=2&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["vulnerabilities"]) == 10
    assert data["page"] == 2


@pytest.mark.integration
def test_get_vulnerability_by_id(client, sample_vulnerability):
    """Test getting vulnerability by ID."""
    response = client.get(f"/api/v1/vulnerabilities/{sample_vulnerability.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["cve_id"] == "CVE-2023-TEST"
    assert data["id"] == sample_vulnerability.id


@pytest.mark.integration
def test_get_vulnerability_not_found(client):
    """Test getting non-existent vulnerability."""
    response = client.get("/api/v1/vulnerabilities/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.integration
def test_get_vulnerability_by_cve(client, sample_vulnerability):
    """Test getting vulnerability by CVE ID."""
    response = client.get("/api/v1/vulnerabilities/cve/CVE-2023-TEST")
    assert response.status_code == 200
    data = response.json()
    assert data["cve_id"] == "CVE-2023-TEST"


@pytest.mark.integration
def test_create_vulnerability(client, test_db):
    """Test creating a new vulnerability."""
    payload = {
        "cve_id": "CVE-2024-NEW",
        "title": "New Vulnerability",
        "description": "This is a new vulnerability",
        "severity": "critical",
        "cvss_score": 9.8,
        "package_name": "new-package",
        "vulnerable_version": "2.0.0",
        "fixed_version": "2.0.1",
    }

    response = client.post("/api/v1/vulnerabilities", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["cve_id"] == "CVE-2024-NEW"
    assert data["severity"] == "critical"
    assert data["cvss_score"] == 9.8


@pytest.mark.integration
def test_vulnerability_statistics(client, test_db):
    """Test vulnerability statistics."""
    # Create vulnerabilities with different severities
    severities = ["critical", "high", "medium", "low"]
    for i, severity in enumerate(severities):
        for j in range(i + 1):  # Create 1 critical, 2 high, 3 medium, 4 low
            vuln = Vulnerability(
                cve_id=f"CVE-2023-{severity}-{j}",
                title=f"{severity} vuln {j}",
                severity=severity,
                status=VulnerabilityStatus.NEW,
            )
            test_db.add(vuln)
    test_db.commit()

    response = client.get("/api/v1/vulnerabilities/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_vulnerabilities"] == 10  # 1+2+3+4
    assert data["critical_count"] == 1
    assert data["high_count"] == 2
    assert data["medium_count"] == 3
    assert data["low_count"] == 4


# Patch Tests


@pytest.mark.integration
def test_list_patches_empty(client, test_db):
    """Test listing patches when database is empty."""
    response = client.get("/api/v1/patches")
    assert response.status_code == 200
    data = response.json()
    assert data["patches"] == []
    assert data["total"] == 0


@pytest.mark.integration
def test_list_patches(client, sample_patch):
    """Test listing patches."""
    response = client.get("/api/v1/patches")
    assert response.status_code == 200
    data = response.json()
    assert len(data["patches"]) == 1

    patch = data["patches"][0]
    assert patch["patch_id"] == "PATCH-TEST-001"
    assert patch["confidence_score"] == 0.85


@pytest.mark.integration
def test_list_patches_filter_by_status(client, sample_patch):
    """Test filtering patches by status."""
    response = client.get("/api/v1/patches?status=generated")
    assert response.status_code == 200
    data = response.json()
    assert len(data["patches"]) == 1

    response = client.get("/api/v1/patches?status=approved")
    assert response.status_code == 200
    data = response.json()
    assert len(data["patches"]) == 0


@pytest.mark.integration
def test_get_patch_by_id(client, sample_patch):
    """Test getting patch by ID with full details."""
    response = client.get(f"/api/v1/patches/{sample_patch.patch_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["patch_id"] == "PATCH-TEST-001"
    assert "patch_content" in data
    assert "rollback_script" in data
    assert data["patch_content"] == "#!/bin/bash\necho 'Test patch'"


@pytest.mark.integration
def test_get_patch_not_found(client):
    """Test getting non-existent patch."""
    response = client.get("/api/v1/patches/PATCH-NONEXISTENT")
    assert response.status_code == 404


@pytest.mark.integration
def test_approve_patch(client, sample_patch):
    """Test approving a patch."""
    payload = {
        "approver": "test@example.com",
        "notes": "Looks good",
    }

    response = client.post(
        f"/api/v1/patches/{sample_patch.patch_id}/approve",
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == PatchStatus.APPROVED
    assert data["approved_by"] == "test@example.com"
    assert data["approved_at"] is not None


@pytest.mark.integration
def test_reject_patch(client, sample_patch):
    """Test rejecting a patch."""
    payload = {
        "rejector": "test@example.com",
        "reason": "Safety concerns",
    }

    response = client.post(
        f"/api/v1/patches/{sample_patch.patch_id}/reject",
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == PatchStatus.REJECTED
    assert data["rejection_reason"] == "Safety concerns"


@pytest.mark.integration
def test_patch_statistics(client, test_db, sample_vulnerability):
    """Test patch statistics."""
    # Create patches with different statuses
    statuses = [
        PatchStatus.GENERATED,
        PatchStatus.GENERATED,
        PatchStatus.APPROVED,
        PatchStatus.REJECTED,
    ]

    for i, status in enumerate(statuses):
        patch = Patch(
            patch_id=f"PATCH-STATS-{i}",
            vulnerability_id=sample_vulnerability.id,
            patch_content="test",
            status=status,
            confidence_score=0.8,
        )
        test_db.add(patch)
    test_db.commit()

    response = client.get("/api/v1/patches/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_patches"] == 4
    assert data["approved"] == 1
    assert data["rejected"] == 1
    assert data["pending_review"] == 2


@pytest.mark.integration
def test_get_patches_for_vulnerability(client, sample_patch, sample_vulnerability):
    """Test getting all patches for a vulnerability."""
    response = client.get(
        f"/api/v1/patches/vulnerability/{sample_vulnerability.id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["patch_id"] == "PATCH-TEST-001"


# Error Handling Tests


@pytest.mark.integration
def test_invalid_severity_filter(client):
    """Test invalid severity filter returns 400."""
    response = client.get("/api/v1/vulnerabilities?severity=invalid")
    assert response.status_code == 400
    assert "Invalid severity" in response.json()["detail"]


@pytest.mark.integration
def test_invalid_status_filter(client):
    """Test invalid status filter returns 400."""
    response = client.get("/api/v1/vulnerabilities?status=invalid")
    assert response.status_code == 400
    assert "Invalid status" in response.json()["detail"]


# Root Endpoint Test


@pytest.mark.integration
def test_root_endpoint(client):
    """Test root endpoint returns API info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "VulnZero API"
    assert data["version"] == "0.1.0"
    assert data["docs"] == "/docs"
    assert data["status"] == "operational"
