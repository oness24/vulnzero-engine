"""
Tests for alert manager
"""

import pytest
from services.monitoring.alerts import AlertManager, AlertSeverity, AlertChannel


@pytest.fixture
def alert_manager():
    """Create alert manager"""
    return AlertManager()


def test_create_alert(alert_manager):
    """Test creating an alert"""
    alert = alert_manager.create_alert(
        title="Test Alert",
        message="This is a test alert",
        severity=AlertSeverity.WARNING,
        deployment_id=1,
    )

    assert alert["id"] == 1
    assert alert["title"] == "Test Alert"
    assert alert["severity"] == "warning"
    assert alert["deployment_id"] == 1
    assert alert["acknowledged"] is False
    assert alert["resolved"] is False


def test_create_alert_with_metadata(alert_manager):
    """Test creating alert with metadata"""
    metadata = {"key": "value", "count": 42}

    alert = alert_manager.create_alert(
        title="Test Alert",
        message="Test",
        severity=AlertSeverity.INFO,
        metadata=metadata,
    )

    assert alert["metadata"] == metadata


def test_acknowledge_alert(alert_manager):
    """Test acknowledging an alert"""
    alert = alert_manager.create_alert(
        title="Test",
        message="Test",
        severity=AlertSeverity.INFO,
    )

    result = alert_manager.acknowledge_alert(alert["id"])

    assert result is True
    assert alert_manager.alerts[0]["acknowledged"] is True
    assert "acknowledged_at" in alert_manager.alerts[0]


def test_acknowledge_nonexistent_alert(alert_manager):
    """Test acknowledging non-existent alert"""
    result = alert_manager.acknowledge_alert(999)

    assert result is False


def test_resolve_alert(alert_manager):
    """Test resolving an alert"""
    alert = alert_manager.create_alert(
        title="Test",
        message="Test",
        severity=AlertSeverity.WARNING,
    )

    result = alert_manager.resolve_alert(alert["id"])

    assert result is True
    assert alert_manager.alerts[0]["resolved"] is True
    assert "resolved_at" in alert_manager.alerts[0]


def test_resolve_nonexistent_alert(alert_manager):
    """Test resolving non-existent alert"""
    result = alert_manager.resolve_alert(999)

    assert result is False


def test_get_active_alerts(alert_manager):
    """Test getting active alerts"""
    # Create resolved and unresolved alerts
    alert1 = alert_manager.create_alert(
        title="Alert 1",
        message="Test",
        severity=AlertSeverity.WARNING,
    )
    alert2 = alert_manager.create_alert(
        title="Alert 2",
        message="Test",
        severity=AlertSeverity.ERROR,
    )

    # Resolve one
    alert_manager.resolve_alert(alert1["id"])

    active = alert_manager.get_active_alerts()

    assert len(active) == 1
    assert active[0]["id"] == alert2["id"]


def test_get_active_alerts_by_deployment(alert_manager):
    """Test getting active alerts for specific deployment"""
    alert_manager.create_alert(
        title="Alert 1",
        message="Test",
        severity=AlertSeverity.WARNING,
        deployment_id=1,
    )
    alert_manager.create_alert(
        title="Alert 2",
        message="Test",
        severity=AlertSeverity.WARNING,
        deployment_id=2,
    )

    active = alert_manager.get_active_alerts(deployment_id=1)

    assert len(active) == 1
    assert active[0]["deployment_id"] == 1


def test_get_active_alerts_by_severity(alert_manager):
    """Test getting active alerts by minimum severity"""
    alert_manager.create_alert(
        title="Info Alert",
        message="Test",
        severity=AlertSeverity.INFO,
    )
    alert_manager.create_alert(
        title="Error Alert",
        message="Test",
        severity=AlertSeverity.ERROR,
    )

    active = alert_manager.get_active_alerts(min_severity=AlertSeverity.ERROR)

    assert len(active) == 1
    assert active[0]["severity"] == "error"


def test_add_notification_channel(alert_manager):
    """Test adding notification channel"""
    result = alert_manager.add_notification_channel(
        channel_type=AlertChannel.EMAIL,
        config={"recipients": ["test@example.com"]},
    )

    assert result is True
    assert len(alert_manager.notification_channels) == 1
    assert alert_manager.notification_channels[0]["type"] == "email"


def test_remove_notification_channel(alert_manager):
    """Test removing notification channel"""
    alert_manager.add_notification_channel(
        channel_type=AlertChannel.EMAIL,
        config={},
    )

    result = alert_manager.remove_notification_channel("email")

    assert result is True
    assert len(alert_manager.notification_channels) == 0


def test_remove_nonexistent_channel(alert_manager):
    """Test removing non-existent channel"""
    result = alert_manager.remove_notification_channel("nonexistent")

    assert result is False


def test_should_notify_channel(alert_manager):
    """Test channel notification filtering"""
    channel = {
        "type": "email",
        "min_severity": "warning",
    }

    # Should notify for warning and above
    assert alert_manager._should_notify_channel(channel, AlertSeverity.WARNING) is True
    assert alert_manager._should_notify_channel(channel, AlertSeverity.ERROR) is True
    assert alert_manager._should_notify_channel(channel, AlertSeverity.CRITICAL) is True

    # Should not notify for info
    assert alert_manager._should_notify_channel(channel, AlertSeverity.INFO) is False


def test_create_deployment_alert(alert_manager):
    """Test creating deployment-specific alert"""
    alert = alert_manager.create_deployment_alert(
        deployment_id=1,
        alert_type="deployment_started",
        details={"message": "Deployment started"},
    )

    assert alert["deployment_id"] == 1
    assert "Deployment 1 Started" in alert["title"]
    assert alert["severity"] == "info"


def test_create_deployment_failed_alert(alert_manager):
    """Test creating deployment failure alert"""
    alert = alert_manager.create_deployment_alert(
        deployment_id=1,
        alert_type="deployment_failed",
        details={"message": "Deployment failed"},
    )

    assert alert["severity"] == "error"


def test_create_rollback_alert(alert_manager):
    """Test creating rollback alert"""
    alert = alert_manager.create_deployment_alert(
        deployment_id=1,
        alert_type="rollback_triggered",
        details={"message": "Rollback triggered"},
    )

    assert alert["severity"] == "critical"


def test_get_alert_summary(alert_manager):
    """Test getting alert summary"""
    # Create various alerts
    alert_manager.create_alert("Alert 1", "Test", AlertSeverity.INFO)
    alert_manager.create_alert("Alert 2", "Test", AlertSeverity.WARNING)
    alert_manager.create_alert("Alert 3", "Test", AlertSeverity.ERROR)

    # Resolve one
    alert_manager.resolve_alert(1)

    summary = alert_manager.get_alert_summary(hours=24)

    assert summary["total_alerts"] == 3
    assert summary["by_severity"]["info"] == 1
    assert summary["by_severity"]["warning"] == 1
    assert summary["by_severity"]["error"] == 1
    assert summary["resolved_alerts"] == 1
    assert summary["active_alerts"] == 2


def test_notify_log(alert_manager):
    """Test log notification"""
    alert = {
        "id": 1,
        "title": "Test Alert",
        "message": "Test message",
        "severity": "info",
    }

    # Should not raise exception
    alert_manager._notify_log(alert)


def test_notify_email(alert_manager):
    """Test email notification (placeholder)"""
    channel = {"recipients": ["test@example.com"]}
    alert = {"id": 1, "title": "Test", "message": "Test"}

    # Should not raise exception
    alert_manager._notify_email(channel, alert)


def test_notify_slack(alert_manager):
    """Test Slack notification (placeholder)"""
    channel = {"webhook_url": "https://hooks.slack.com/test"}
    alert = {"id": 1, "title": "Test", "message": "Test"}

    # Should not raise exception
    alert_manager._notify_slack(channel, alert)


def test_notify_webhook(alert_manager):
    """Test webhook notification (placeholder)"""
    channel = {"url": "https://example.com/webhook"}
    alert = {"id": 1, "title": "Test", "message": "Test"}

    # Should not raise exception
    alert_manager._notify_webhook(channel, alert)


def test_send_notifications(alert_manager):
    """Test sending notifications to configured channels"""
    # Add notification channel
    alert_manager.add_notification_channel(
        channel_type=AlertChannel.LOG,
        config={"min_severity": "warning"},
    )

    # Create alert
    alert = alert_manager.create_alert(
        title="Test Alert",
        message="Test",
        severity=AlertSeverity.ERROR,
    )

    # Notifications should have been sent (via _send_notifications)
    assert len(alert_manager.notification_channels) == 1
