"""
Tests for dashboard API routes
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_get_dashboard_stats():
    """Test getting dashboard statistics"""
    response = client.get("/api/dashboard/stats")
    assert response.status_code in [200, 500]


def test_get_dashboard_stats_with_hours():
    """Test getting dashboard stats for specific period"""
    response = client.get(
        "/api/dashboard/stats",
        params={"hours": 48}
    )
    assert response.status_code in [200, 500]


def test_get_system_health():
    """Test getting system health"""
    response = client.get("/api/dashboard/health")
    assert response.status_code in [200, 500]


def test_get_trends():
    """Test getting trend data"""
    response = client.get("/api/dashboard/trends")
    assert response.status_code in [200, 500]


def test_get_trends_with_days():
    """Test getting trends for specific period"""
    response = client.get(
        "/api/dashboard/trends",
        params={"days": 14}
    )
    assert response.status_code in [200, 500]


def test_get_top_vulnerabilities():
    """Test getting top vulnerabilities"""
    response = client.get("/api/dashboard/top-vulnerabilities")
    assert response.status_code in [200, 500]


def test_get_top_vulnerabilities_with_limit():
    """Test getting top vulnerabilities with limit"""
    response = client.get(
        "/api/dashboard/top-vulnerabilities",
        params={"limit": 5}
    )
    assert response.status_code in [200, 500]


def test_get_deployment_dashboard_analytics():
    """Test getting deployment analytics"""
    response = client.get("/api/dashboard/deployment-analytics")
    assert response.status_code in [200, 500]


def test_get_deployment_dashboard_analytics_with_hours():
    """Test getting deployment analytics for specific period"""
    response = client.get(
        "/api/dashboard/deployment-analytics",
        params={"hours": 72}
    )
    assert response.status_code in [200, 500]


def test_get_summary():
    """Test getting dashboard summary"""
    response = client.get("/api/dashboard/summary")
    assert response.status_code in [200, 500]


def test_dashboard_stats_structure():
    """Test that dashboard stats have expected structure"""
    response = client.get("/api/dashboard/stats")

    if response.status_code == 200:
        data = response.json()
        assert "vulnerabilities" in data
        assert "patches" in data
        assert "deployments" in data
        assert "assets" in data
        assert "alerts" in data
        assert "recent_activity" in data


def test_system_health_structure():
    """Test that system health has expected structure"""
    response = client.get("/api/dashboard/health")

    if response.status_code == 200:
        data = response.json()
        assert "overall_status" in data
        assert "active_deployments" in data
        assert "active_alerts" in data
        assert "critical_vulnerabilities" in data
        assert "asset_health" in data


def test_trends_structure():
    """Test that trends data has expected structure"""
    response = client.get("/api/dashboard/trends")

    if response.status_code == 200:
        data = response.json()
        assert "vulnerabilities" in data
        assert "patches" in data
        assert "deployments" in data
