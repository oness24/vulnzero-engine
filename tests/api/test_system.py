"""
Tests for system and health endpoints
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint"""
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert "version" in data
    assert "timestamp" in data
    assert "services" in data
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_health_check_database_status(client: AsyncClient):
    """Test that health check includes database status"""
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()

    assert "database" in data["services"]
    # Should be healthy since we're using test database
    assert data["services"]["database"] == "healthy"


@pytest.mark.asyncio
async def test_metrics_endpoint(
    client: AsyncClient,
    auth_headers: dict,
    multiple_vulnerabilities,
):
    """Test metrics endpoint"""
    response = await client.get("/api/v1/metrics", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert "vulnerabilities_scanned" in data
    assert "patches_generated" in data
    assert "deployments_completed" in data
    assert "remediation_rate" in data
    assert "avg_time_to_remediate" in data

    # Should have vulnerabilities from fixture
    assert data["vulnerabilities_scanned"] >= 5


@pytest.mark.asyncio
async def test_metrics_requires_authentication(client: AsyncClient):
    """Test that metrics endpoint requires authentication"""
    response = await client.get("/api/v1/metrics")

    assert response.status_code == 403  # Forbidden


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test root endpoint"""
    response = await client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "VulnZero API"
    assert data["status"] == "operational"
    assert "version" in data
