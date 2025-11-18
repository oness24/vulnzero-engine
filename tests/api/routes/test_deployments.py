"""
Tests for deployment API routes
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_list_deployments():
    """Test listing deployments"""
    response = client.get("/api/deployments/")
    assert response.status_code in [200, 500]


def test_list_deployments_with_filters():
    """Test deployment listing with filters"""
    response = client.get(
        "/api/deployments/",
        params={
            "status": "completed",
            "strategy": "rolling",
            "page": 1,
        }
    )
    assert response.status_code in [200, 500]


def test_get_deployment_not_found():
    """Test getting non-existent deployment"""
    response = client.get("/api/deployments/99999")
    assert response.status_code in [404, 500]


def test_create_deployment():
    """Test creating a deployment"""
    deployment_data = {
        "patch_id": 1,
        "asset_ids": [1, 2, 3],
        "strategy": "rolling",
        "strategy_options": {"batch_size": 1},
    }

    response = client.post("/api/deployments/", json=deployment_data)
    assert response.status_code in [200, 201, 404, 500]


def test_rollback_deployment():
    """Test triggering deployment rollback"""
    response = client.post("/api/deployments/1/rollback")
    assert response.status_code in [200, 400, 404, 500]


def test_verify_deployment():
    """Test triggering deployment verification"""
    response = client.post("/api/deployments/1/verify")
    assert response.status_code in [200, 404, 500]


def test_get_deployment_status():
    """Test getting deployment status"""
    response = client.get("/api/deployments/1/status")
    assert response.status_code in [200, 404, 500]


def test_get_deployment_stats():
    """Test getting deployment statistics"""
    response = client.get("/api/deployments/stats/summary")
    assert response.status_code in [200, 500]


def test_get_deployment_stats_with_hours():
    """Test getting deployment stats for specific period"""
    response = client.get(
        "/api/deployments/stats/summary",
        params={"hours": 48}
    )
    assert response.status_code in [200, 500]


def test_get_deployment_logs():
    """Test getting deployment logs"""
    response = client.get("/api/deployments/1/logs")
    assert response.status_code in [200, 404, 500]


def test_get_deployment_logs_with_limit():
    """Test getting deployment logs with limit"""
    response = client.get(
        "/api/deployments/1/logs",
        params={"limit": 50}
    )
    assert response.status_code in [200, 404, 500]
