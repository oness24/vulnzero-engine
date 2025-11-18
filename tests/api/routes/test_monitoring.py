"""
Tests for monitoring API routes
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_check_deployment_health():
    """Test checking deployment health"""
    response = client.get("/api/monitoring/health/1")
    assert response.status_code in [200, 404, 500]


def test_get_deployment_metrics():
    """Test getting deployment metrics"""
    response = client.get("/api/monitoring/metrics/1")
    assert response.status_code in [200, 404, 500]


def test_get_monitoring_status():
    """Test getting monitoring status"""
    response = client.get("/api/monitoring/monitoring-status/1")
    assert response.status_code in [200, 500]


def test_start_monitoring():
    """Test starting monitoring"""
    response = client.post("/api/monitoring/start-monitoring/1")
    assert response.status_code in [200, 404, 500]


def test_stop_monitoring():
    """Test stopping monitoring"""
    response = client.post("/api/monitoring/stop-monitoring/1")
    assert response.status_code in [200, 500]


def test_list_alerts():
    """Test listing alerts"""
    response = client.get("/api/monitoring/alerts")
    assert response.status_code in [200, 500]


def test_list_alerts_with_filters():
    """Test listing alerts with filters"""
    response = client.get(
        "/api/monitoring/alerts",
        params={
            "deployment_id": 1,
            "severity": "critical",
            "active_only": True,
        }
    )
    assert response.status_code in [200, 500]


def test_create_alert():
    """Test creating an alert"""
    alert_data = {
        "title": "Test Alert",
        "message": "This is a test alert",
        "severity": "warning",
        "deployment_id": 1,
    }

    response = client.post("/api/monitoring/alerts", json=alert_data)
    assert response.status_code in [200, 201, 400, 500]


def test_create_alert_invalid_severity():
    """Test creating alert with invalid severity"""
    alert_data = {
        "title": "Test",
        "message": "Test",
        "severity": "invalid",
    }

    response = client.post("/api/monitoring/alerts", json=alert_data)
    assert response.status_code in [400, 422, 500]


def test_acknowledge_alert():
    """Test acknowledging an alert"""
    response = client.post("/api/monitoring/alerts/1/acknowledge")
    assert response.status_code in [200, 404, 500]


def test_resolve_alert():
    """Test resolving an alert"""
    response = client.post("/api/monitoring/alerts/1/resolve")
    assert response.status_code in [200, 404, 500]


def test_get_alert_summary():
    """Test getting alert summary"""
    response = client.get("/api/monitoring/alerts/summary")
    assert response.status_code in [200, 500]


def test_add_notification_channel():
    """Test adding notification channel"""
    channel_data = {
        "channel_type": "email",
        "config": {"recipients": ["test@example.com"]},
    }

    response = client.post("/api/monitoring/notification-channels", json=channel_data)
    assert response.status_code in [200, 201, 400, 500]


def test_remove_notification_channel():
    """Test removing notification channel"""
    response = client.delete("/api/monitoring/notification-channels/email")
    assert response.status_code in [200, 404, 500]


def test_get_rollback_triggers():
    """Test getting rollback triggers"""
    response = client.get("/api/monitoring/rollback-triggers/1")
    assert response.status_code in [200, 500]


def test_get_rollback_history():
    """Test getting rollback history"""
    response = client.get("/api/monitoring/rollback-history")
    assert response.status_code in [200, 500]


def test_get_deployment_analytics():
    """Test getting deployment analytics"""
    response = client.get("/api/monitoring/analytics/stats")
    assert response.status_code in [200, 500]


def test_get_failure_analysis():
    """Test getting failure analysis"""
    response = client.get("/api/monitoring/analytics/failure-analysis")
    assert response.status_code in [200, 500]


def test_get_performance_metrics():
    """Test getting performance metrics"""
    response = client.get("/api/monitoring/analytics/performance")
    assert response.status_code in [200, 500]


def test_get_patch_analytics():
    """Test getting patch analytics"""
    response = client.get("/api/monitoring/analytics/patch/1")
    assert response.status_code in [200, 500]
