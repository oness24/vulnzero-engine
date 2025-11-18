"""
Tests for vulnerability management endpoints
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.models import Vulnerability, VulnerabilityStatus


@pytest.mark.asyncio
async def test_list_vulnerabilities_empty(client: AsyncClient, auth_headers: dict):
    """Test listing vulnerabilities when none exist"""
    response = await client.get("/api/v1/vulnerabilities", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_vulnerabilities(
    client: AsyncClient,
    auth_headers: dict,
    multiple_vulnerabilities: list[Vulnerability],
):
    """Test listing vulnerabilities with data"""
    response = await client.get("/api/v1/vulnerabilities", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 5
    assert data["total"] == 5
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_vulnerabilities_pagination(
    client: AsyncClient,
    auth_headers: dict,
    multiple_vulnerabilities: list[Vulnerability],
):
    """Test vulnerability pagination"""
    response = await client.get(
        "/api/v1/vulnerabilities?page=1&page_size=2",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 3


@pytest.mark.asyncio
async def test_list_vulnerabilities_filter_by_severity(
    client: AsyncClient,
    auth_headers: dict,
    multiple_vulnerabilities: list[Vulnerability],
):
    """Test filtering vulnerabilities by severity"""
    response = await client.get(
        "/api/v1/vulnerabilities?severity=critical",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Should have 2 critical vulnerabilities
    assert data["total"] == 2
    for item in data["items"]:
        assert item["severity"] == "critical"


@pytest.mark.asyncio
async def test_list_vulnerabilities_filter_by_cvss(
    client: AsyncClient,
    auth_headers: dict,
    multiple_vulnerabilities: list[Vulnerability],
):
    """Test filtering vulnerabilities by minimum CVSS score"""
    response = await client.get(
        "/api/v1/vulnerabilities?min_cvss=7.0",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Should have vulnerabilities with CVSS >= 7.0
    for item in data["items"]:
        assert item["cvss_score"] >= 7.0


@pytest.mark.asyncio
async def test_get_vulnerability(
    client: AsyncClient,
    auth_headers: dict,
    sample_vulnerability: Vulnerability,
):
    """Test getting a specific vulnerability"""
    response = await client.get(
        f"/api/v1/vulnerabilities/{sample_vulnerability.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == sample_vulnerability.id
    assert data["cve_id"] == sample_vulnerability.cve_id
    assert data["title"] == sample_vulnerability.title


@pytest.mark.asyncio
async def test_get_vulnerability_not_found(client: AsyncClient, auth_headers: dict):
    """Test getting a non-existent vulnerability"""
    response = await client.get("/api/v1/vulnerabilities/99999", headers=auth_headers)

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_create_vulnerability(client: AsyncClient, auth_headers: dict):
    """Test creating a new vulnerability"""
    vulnerability_data = {
        "cve_id": "CVE-2024-NEW",
        "title": "New Vulnerability",
        "description": "A newly discovered vulnerability",
        "severity": "high",
        "cvss_score": 8.5,
        "affected_package": "new-package",
        "vulnerable_version": "1.0.0",
        "fixed_version": "1.0.1",
    }

    response = await client.post(
        "/api/v1/vulnerabilities",
        json=vulnerability_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()

    assert data["cve_id"] == "CVE-2024-NEW"
    assert data["title"] == "New Vulnerability"
    assert data["severity"] == "high"
    assert data["status"] == "new"


@pytest.mark.asyncio
async def test_create_duplicate_vulnerability(
    client: AsyncClient,
    auth_headers: dict,
    sample_vulnerability: Vulnerability,
):
    """Test creating a vulnerability with duplicate CVE ID"""
    vulnerability_data = {
        "cve_id": sample_vulnerability.cve_id,  # Duplicate!
        "title": "Duplicate",
        "severity": "high",
    }

    response = await client.post(
        "/api/v1/vulnerabilities",
        json=vulnerability_data,
        headers=auth_headers,
    )

    assert response.status_code == 409  # Conflict


@pytest.mark.asyncio
async def test_update_vulnerability(
    client: AsyncClient,
    auth_headers: dict,
    sample_vulnerability: Vulnerability,
):
    """Test updating a vulnerability"""
    update_data = {
        "status": "remediated",
        "priority_score": 100.0,
    }

    response = await client.patch(
        f"/api/v1/vulnerabilities/{sample_vulnerability.id}",
        json=update_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "remediated"
    assert data["priority_score"] == 100.0


@pytest.mark.asyncio
async def test_get_vulnerability_stats(
    client: AsyncClient,
    auth_headers: dict,
    multiple_vulnerabilities: list[Vulnerability],
):
    """Test getting vulnerability statistics"""
    response = await client.get("/api/v1/vulnerabilities/stats", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 5
    assert "by_severity" in data
    assert "by_status" in data
    assert "remediation_rate" in data


@pytest.mark.asyncio
async def test_trigger_scan(client: AsyncClient, auth_headers: dict):
    """Test triggering a manual vulnerability scan"""
    response = await client.post("/api/v1/vulnerabilities/scan", headers=auth_headers)

    assert response.status_code == 202  # Accepted
    data = response.json()

    assert "message" in data
    assert "task_id" in data


@pytest.mark.asyncio
async def test_vulnerabilities_require_authentication(client: AsyncClient):
    """Test that vulnerability endpoints require authentication"""
    # Try without auth headers
    response = await client.get("/api/v1/vulnerabilities")

    assert response.status_code == 403  # Forbidden


@pytest.mark.asyncio
async def test_create_vulnerability_requires_operator_role(
    client: AsyncClient,
    viewer_token: str,
):
    """Test that creating vulnerabilities requires operator role"""
    headers = {"Authorization": f"Bearer {viewer_token}"}

    vulnerability_data = {
        "cve_id": "CVE-2024-TEST",
        "title": "Test",
        "severity": "high",
    }

    response = await client.post(
        "/api/v1/vulnerabilities",
        json=vulnerability_data,
        headers=headers,
    )

    assert response.status_code == 403  # Forbidden - viewer role insufficient
