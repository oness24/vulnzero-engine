"""
Alerting system for deployments
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import structlog

logger = structlog.get_logger()


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert notification channels"""
    LOG = "log"
    EMAIL = "email"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    WEBHOOK = "webhook"


class AlertManager:
    """
    Manages alerts and notifications for deployments
    """

    def __init__(self):
        self.alerts = []
        self.notification_channels = []
        self.alert_rules = []

    def create_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        deployment_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new alert

        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity
            deployment_id: Optional deployment ID
            metadata: Optional additional metadata

        Returns:
            Created alert
        """
        alert = {
            "id": len(self.alerts) + 1,
            "title": title,
            "message": message,
            "severity": severity.value,
            "deployment_id": deployment_id,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "acknowledged": False,
            "resolved": False,
        }

        self.alerts.append(alert)

        logger.info(
            "alert_created",
            alert_id=alert["id"],
            severity=severity.value,
            deployment_id=deployment_id,
        )

        # Send notifications
        self._send_notifications(alert)

        return alert

    def _send_notifications(self, alert: Dict[str, Any]):
        """
        Send alert notifications to configured channels

        Args:
            alert: Alert to send
        """
        severity = AlertSeverity(alert["severity"])

        for channel in self.notification_channels:
            # Check if channel is configured for this severity
            if self._should_notify_channel(channel, severity):
                self._notify_channel(channel, alert)

    def _should_notify_channel(
        self,
        channel: Dict[str, Any],
        severity: AlertSeverity,
    ) -> bool:
        """
        Determine if channel should be notified

        Args:
            channel: Notification channel config
            severity: Alert severity

        Returns:
            True if should notify
        """
        min_severity = channel.get("min_severity", AlertSeverity.WARNING.value)
        severity_levels = {
            "info": 1,
            "warning": 2,
            "error": 3,
            "critical": 4,
        }

        return severity_levels.get(severity.value, 0) >= severity_levels.get(min_severity, 2)

    def _notify_channel(self, channel: Dict[str, Any], alert: Dict[str, Any]):
        """
        Send notification to a channel

        Args:
            channel: Channel configuration
            alert: Alert to send
        """
        channel_type = channel.get("type")

        logger.info(
            "sending_alert_notification",
            channel=channel_type,
            alert_id=alert["id"],
        )

        if channel_type == AlertChannel.LOG.value:
            self._notify_log(alert)
        elif channel_type == AlertChannel.EMAIL.value:
            self._notify_email(channel, alert)
        elif channel_type == AlertChannel.SLACK.value:
            self._notify_slack(channel, alert)
        elif channel_type == AlertChannel.WEBHOOK.value:
            self._notify_webhook(channel, alert)
        else:
            logger.warning("unknown_channel_type", channel_type=channel_type)

    def _notify_log(self, alert: Dict[str, Any]):
        """Log alert"""
        severity = alert["severity"]

        log_message = f"ALERT [{severity.upper()}]: {alert['title']} - {alert['message']}"

        if severity == AlertSeverity.CRITICAL.value:
            logger.critical(log_message)
        elif severity == AlertSeverity.ERROR.value:
            logger.error(log_message)
        elif severity == AlertSeverity.WARNING.value:
            logger.warning(log_message)
        else:
            logger.info(log_message)

    def _notify_email(self, channel: Dict[str, Any], alert: Dict[str, Any]):
        """
        Send email notification

        Args:
            channel: Email channel config
            alert: Alert to send
        """
        # Placeholder - would integrate with email service
        logger.info(
            "email_notification_sent",
            to=channel.get("recipients"),
            alert_id=alert["id"],
        )

    def _notify_slack(self, channel: Dict[str, Any], alert: Dict[str, Any]):
        """
        Send Slack notification

        Args:
            channel: Slack channel config
            alert: Alert to send
        """
        # Placeholder - would integrate with Slack API
        logger.info(
            "slack_notification_sent",
            channel=channel.get("webhook_url"),
            alert_id=alert["id"],
        )

    def _notify_webhook(self, channel: Dict[str, Any], alert: Dict[str, Any]):
        """
        Send webhook notification

        Args:
            channel: Webhook config
            alert: Alert to send
        """
        # Placeholder - would send HTTP POST to webhook
        logger.info(
            "webhook_notification_sent",
            url=channel.get("url"),
            alert_id=alert["id"],
        )

    def acknowledge_alert(self, alert_id: int) -> bool:
        """
        Acknowledge an alert

        Args:
            alert_id: Alert ID to acknowledge

        Returns:
            True if acknowledged
        """
        for alert in self.alerts:
            if alert["id"] == alert_id:
                alert["acknowledged"] = True
                alert["acknowledged_at"] = datetime.utcnow().isoformat()

                logger.info("alert_acknowledged", alert_id=alert_id)
                return True

        return False

    def resolve_alert(self, alert_id: int) -> bool:
        """
        Resolve an alert

        Args:
            alert_id: Alert ID to resolve

        Returns:
            True if resolved
        """
        for alert in self.alerts:
            if alert["id"] == alert_id:
                alert["resolved"] = True
                alert["resolved_at"] = datetime.utcnow().isoformat()

                logger.info("alert_resolved", alert_id=alert_id)
                return True

        return False

    def get_active_alerts(
        self,
        deployment_id: Optional[int] = None,
        min_severity: Optional[AlertSeverity] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get active (unresolved) alerts

        Args:
            deployment_id: Optional filter by deployment
            min_severity: Optional minimum severity filter

        Returns:
            List of active alerts
        """
        active_alerts = [
            alert for alert in self.alerts
            if not alert.get("resolved", False)
        ]

        if deployment_id:
            active_alerts = [
                alert for alert in active_alerts
                if alert.get("deployment_id") == deployment_id
            ]

        if min_severity:
            severity_levels = {
                "info": 1,
                "warning": 2,
                "error": 3,
                "critical": 4,
            }
            min_level = severity_levels.get(min_severity.value, 0)

            active_alerts = [
                alert for alert in active_alerts
                if severity_levels.get(alert["severity"], 0) >= min_level
            ]

        return active_alerts

    def add_notification_channel(
        self,
        channel_type: AlertChannel,
        config: Dict[str, Any],
    ) -> bool:
        """
        Add a notification channel

        Args:
            channel_type: Type of channel
            config: Channel configuration

        Returns:
            True if added
        """
        channel = {
            "type": channel_type.value,
            "config": config,
            "min_severity": config.get("min_severity", AlertSeverity.WARNING.value),
        }

        self.notification_channels.append(channel)

        logger.info("notification_channel_added", type=channel_type.value)
        return True

    def remove_notification_channel(self, channel_type: str) -> bool:
        """
        Remove a notification channel

        Args:
            channel_type: Type of channel to remove

        Returns:
            True if removed
        """
        initial_count = len(self.notification_channels)
        self.notification_channels = [
            channel for channel in self.notification_channels
            if channel["type"] != channel_type
        ]

        removed = len(self.notification_channels) < initial_count

        if removed:
            logger.info("notification_channel_removed", type=channel_type)

        return removed

    def create_deployment_alert(
        self,
        deployment_id: int,
        alert_type: str,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create deployment-specific alert

        Args:
            deployment_id: Deployment ID
            alert_type: Type of alert
            details: Alert details

        Returns:
            Created alert
        """
        alert_configs = {
            "deployment_started": {
                "title": f"Deployment {deployment_id} Started",
                "severity": AlertSeverity.INFO,
            },
            "deployment_completed": {
                "title": f"Deployment {deployment_id} Completed",
                "severity": AlertSeverity.INFO,
            },
            "deployment_failed": {
                "title": f"Deployment {deployment_id} Failed",
                "severity": AlertSeverity.ERROR,
            },
            "health_check_failed": {
                "title": f"Health Check Failed - Deployment {deployment_id}",
                "severity": AlertSeverity.WARNING,
            },
            "rollback_triggered": {
                "title": f"Rollback Triggered - Deployment {deployment_id}",
                "severity": AlertSeverity.CRITICAL,
            },
            "rollback_completed": {
                "title": f"Rollback Completed - Deployment {deployment_id}",
                "severity": AlertSeverity.WARNING,
            },
        }

        config = alert_configs.get(alert_type, {
            "title": f"Deployment {deployment_id} Alert",
            "severity": AlertSeverity.WARNING,
        })

        message = details.get("message", f"{alert_type} for deployment {deployment_id}")

        return self.create_alert(
            title=config["title"],
            message=message,
            severity=config["severity"],
            deployment_id=deployment_id,
            metadata=details,
        )

    def get_alert_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get alert summary for the last N hours

        Args:
            hours: Number of hours to summarize

        Returns:
            Alert summary
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=hours)

        recent_alerts = [
            alert for alert in self.alerts
            if datetime.fromisoformat(alert["created_at"]) > cutoff
        ]

        summary = {
            "total_alerts": len(recent_alerts),
            "by_severity": {
                "info": 0,
                "warning": 0,
                "error": 0,
                "critical": 0,
            },
            "active_alerts": 0,
            "resolved_alerts": 0,
        }

        for alert in recent_alerts:
            severity = alert["severity"]
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1

            if alert.get("resolved"):
                summary["resolved_alerts"] += 1
            else:
                summary["active_alerts"] += 1

        return summary
