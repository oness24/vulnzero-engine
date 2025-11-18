"""
Alert Manager

Manages alert generation, routing, and notifications.
"""

import logging
import os
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from sqlalchemy.orm import Session

from services.monitoring.detectors.anomaly_detector import Anomaly, AnomalySeverity
from shared.models import AuditLog, AuditAction

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class Alert:
    """
    Represents an alert.
    """
    id: Optional[int]
    title: str
    message: str
    severity: AlertSeverity
    status: AlertStatus
    source: str  # deployment_id, asset_id, etc.
    anomaly_type: Optional[str]
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class AlertManager:
    """
    Manages alerts, notifications, and escalations.
    """

    def __init__(self, db: Session):
        """
        Initialize alert manager.

        Args:
            db: Database session
        """
        self.db = db
        self.logger = logging.getLogger(__name__)

        # Alert deduplication window (5 minutes)
        self.dedup_window_minutes = 5

        # Notification channels
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        self.email_enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"

    def create_alert_from_anomaly(
        self,
        anomaly: Anomaly,
        deployment_id: int
    ) -> Alert:
        """
        Create alert from detected anomaly.

        Args:
            anomaly: Detected anomaly
            deployment_id: Associated deployment ID

        Returns:
            Created alert
        """
        # Map anomaly severity to alert severity
        severity_map = {
            AnomalySeverity.LOW: AlertSeverity.LOW,
            AnomalySeverity.MEDIUM: AlertSeverity.MEDIUM,
            AnomalySeverity.HIGH: AlertSeverity.HIGH,
            AnomalySeverity.CRITICAL: AlertSeverity.CRITICAL,
        }

        alert = Alert(
            id=None,  # Would be set by database
            title=f"Anomaly Detected: {anomaly.anomaly_type.value}",
            message=anomaly.message,
            severity=severity_map[anomaly.severity],
            status=AlertStatus.ACTIVE,
            source=f"deployment_{deployment_id}",
            anomaly_type=anomaly.anomaly_type.value,
            created_at=datetime.utcnow(),
            metadata={
                "deployment_id": deployment_id,
                "metric_name": anomaly.metric_name,
                "metric_value": anomaly.metric_value,
                "threshold": anomaly.threshold,
                "confidence": anomaly.confidence,
                "labels": anomaly.labels
            }
        )

        self.logger.info(
            f"Created alert: {alert.title} (severity={alert.severity.value})"
        )

        return alert

    def should_send_alert(self, alert: Alert) -> bool:
        """
        Check if alert should be sent (deduplication).

        Args:
            alert: Alert to check

        Returns:
            True if should send
        """
        # For MVP: Simple deduplication logic
        # In production: Query alert database for recent similar alerts

        # Always send critical alerts
        if alert.severity == AlertSeverity.CRITICAL:
            return True

        # For other severities, implement basic deduplication
        # This would check if a similar alert was sent recently
        return True

    def send_alert(self, alert: Alert, channels: Optional[List[str]] = None):
        """
        Send alert to notification channels.

        Args:
            alert: Alert to send
            channels: List of channels ('slack', 'email', 'webhook')
        """
        if not self.should_send_alert(alert):
            self.logger.debug(f"Alert deduplicated: {alert.title}")
            return

        # Default channels based on severity
        if channels is None:
            if alert.severity == AlertSeverity.CRITICAL:
                channels = ["slack", "email"]
            elif alert.severity == AlertSeverity.HIGH:
                channels = ["slack"]
            else:
                channels = []

        # Send to each channel
        for channel in channels:
            try:
                if channel == "slack":
                    self._send_slack(alert)
                elif channel == "email":
                    self._send_email(alert)
                elif channel == "webhook":
                    self._send_webhook(alert)
            except Exception as e:
                self.logger.error(f"Error sending alert to {channel}: {e}", exc_info=True)

    def _send_slack(self, alert: Alert):
        """
        Send alert to Slack.

        Args:
            alert: Alert to send
        """
        if not self.slack_webhook:
            self.logger.warning("Slack webhook not configured")
            return

        # Emoji based on severity
        emoji_map = {
            AlertSeverity.LOW: ":information_source:",
            AlertSeverity.MEDIUM: ":warning:",
            AlertSeverity.HIGH: ":rotating_light:",
            AlertSeverity.CRITICAL: ":fire:"
        }

        # Color based on severity
        color_map = {
            AlertSeverity.LOW: "#36a64f",
            AlertSeverity.MEDIUM: "#ff9900",
            AlertSeverity.HIGH: "#ff6600",
            AlertSeverity.CRITICAL: "#ff0000"
        }

        payload = {
            "text": f"{emoji_map[alert.severity]} *VulnZero Alert*",
            "attachments": [
                {
                    "color": color_map[alert.severity],
                    "title": alert.title,
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity.value.upper(),
                            "short": True
                        },
                        {
                            "title": "Source",
                            "value": alert.source,
                            "short": True
                        },
                        {
                            "title": "Time",
                            "value": alert.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "short": False
                        }
                    ],
                    "footer": "VulnZero Monitoring",
                    "ts": int(alert.created_at.timestamp())
                }
            ]
        }

        try:
            response = requests.post(
                self.slack_webhook,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            self.logger.info(f"Sent Slack alert: {alert.title}")
        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")

    def _send_email(self, alert: Alert):
        """
        Send alert via email.

        Args:
            alert: Alert to send
        """
        if not self.email_enabled:
            self.logger.debug("Email notifications not enabled")
            return

        # For MVP: Log email that would be sent
        # In production: Use SMTP library to send actual email
        self.logger.info(f"[EMAIL ALERT] {alert.title}: {alert.message}")

    def _send_webhook(self, alert: Alert):
        """
        Send alert to custom webhook.

        Args:
            alert: Alert to send
        """
        webhook_url = os.getenv("ALERT_WEBHOOK_URL")
        if not webhook_url:
            return

        payload = {
            "alert_id": alert.id,
            "title": alert.title,
            "message": alert.message,
            "severity": alert.severity.value,
            "status": alert.status.value,
            "source": alert.source,
            "created_at": alert.created_at.isoformat(),
            "metadata": alert.metadata
        }

        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            self.logger.info(f"Sent webhook alert: {alert.title}")
        except Exception as e:
            self.logger.error(f"Failed to send webhook alert: {e}")

    def acknowledge_alert(self, alert_id: int, user_id: Optional[int] = None):
        """
        Mark alert as acknowledged.

        Args:
            alert_id: Alert ID
            user_id: User acknowledging the alert
        """
        # For MVP: Just log
        # In production: Update alert in database
        self.logger.info(f"Alert {alert_id} acknowledged by user {user_id}")

        # Create audit log
        if user_id:
            audit_log = AuditLog(
                user_id=user_id,
                action=AuditAction.SYSTEM_ALERT,
                resource_type="alert",
                resource_id=alert_id,
                details={"action": "acknowledged"},
                ip_address="internal",
                user_agent="AlertManager"
            )
            self.db.add(audit_log)
            self.db.commit()

    def resolve_alert(self, alert_id: int, user_id: Optional[int] = None):
        """
        Mark alert as resolved.

        Args:
            alert_id: Alert ID
            user_id: User resolving the alert
        """
        # For MVP: Just log
        # In production: Update alert in database
        self.logger.info(f"Alert {alert_id} resolved by user {user_id}")

        # Create audit log
        if user_id:
            audit_log = AuditLog(
                user_id=user_id,
                action=AuditAction.SYSTEM_ALERT,
                resource_type="alert",
                resource_id=alert_id,
                details={"action": "resolved"},
                ip_address="internal",
                user_agent="AlertManager"
            )
            self.db.add(audit_log)
            self.db.commit()
