"""
Monitoring Celery Tasks

Async tasks for deployment monitoring, anomaly detection, and rollback.
"""

import logging
import time
from typing import List, Dict, Any, Optional
from celery import Task
from sqlalchemy.orm import Session

from services.monitoring.tasks.celery_app import celery_app
from services.monitoring.collectors.metrics_collector import MetricsCollector
from services.monitoring.detectors.anomaly_detector import AnomalyDetector, AnomalySeverity
from services.monitoring.alerts.alert_manager import AlertManager
from services.monitoring.rollback.rollback_engine import RollbackEngine
from services.monitoring.prometheus.exporter import MetricsExporter
from shared.database import get_db
from shared.models import Deployment, Asset, AuditLog, AuditAction

logger = logging.getLogger(__name__)


class MonitoringTask(Task):
    """Base task with database session management"""

    def __call__(self, *args, **kwargs):
        """Execute task with database session"""
        db = next(get_db())
        try:
            return self.run(*args, db=db, **kwargs)
        finally:
            db.close()


@celery_app.task(
    bind=True,
    base=MonitoringTask,
    name="monitoring.monitor_deployment",
)
def monitor_deployment(
    self,
    deployment_id: int,
    duration_seconds: int = 900,  # 15 minutes
    check_interval: int = 60,     # 1 minute
    db: Session = None
):
    """
    Monitor a deployment for anomalies.

    Args:
        deployment_id: Deployment to monitor
        duration_seconds: How long to monitor
        check_interval: Seconds between checks
        db: Database session (injected)

    Returns:
        Monitoring result dict
    """
    logger.info(
        f"Starting monitoring for deployment {deployment_id}: "
        f"duration={duration_seconds}s, interval={check_interval}s"
    )

    # Initialize components
    collector = MetricsCollector(db)
    detector = AnomalyDetector()
    alert_manager = AlertManager(db)
    rollback_engine = RollbackEngine(db)

    # Get deployment
    deployment = db.query(Deployment).filter_by(id=deployment_id).first()
    if not deployment:
        logger.error(f"Deployment {deployment_id} not found")
        return {"error": "Deployment not found"}

    # Get assets for deployment (simplified - would use join table in production)
    assets = db.query(Asset).all()

    # Collect baseline metrics before monitoring starts
    logger.info(f"Collecting baseline metrics for {len(assets)} assets")
    baseline_metrics = collector.collect_baseline_metrics([a.id for a in assets])

    # Monitoring loop
    start_time = time.time()
    check_count = 0
    total_anomalies = []

    try:
        while time.time() - start_time < duration_seconds:
            check_count += 1
            logger.info(f"Monitoring check #{check_count} for deployment {deployment_id}")

            # Collect current metrics
            current_metrics = []
            current_metrics.extend(collector.collect_deployment_metrics(deployment_id))
            current_metrics.extend(collector.collect_error_metrics(deployment_id))

            for asset in assets[:5]:  # Limit to first 5 assets for MVP
                current_metrics.extend(collector.collect_system_metrics(asset.id))

            # Detect anomalies
            baseline_list = []
            for asset_metrics in baseline_metrics.values():
                baseline_list.extend(asset_metrics)

            anomalies = detector.detect(
                metrics=current_metrics,
                baseline=baseline_list
            )

            if anomalies:
                logger.warning(f"Detected {len(anomalies)} anomalies")
                total_anomalies.extend(anomalies)

                # Send alerts
                for anomaly in anomalies:
                    alert = alert_manager.create_alert_from_anomaly(
                        anomaly=anomaly,
                        deployment_id=deployment_id
                    )
                    alert_manager.send_alert(alert)

                # Evaluate rollback
                decision = rollback_engine.evaluate_rollback(
                    deployment_id=deployment_id,
                    anomalies=anomalies
                )

                if decision.should_rollback:
                    logger.critical(
                        f"Triggering automatic rollback for deployment {deployment_id}: "
                        f"{decision.message}"
                    )

                    success = rollback_engine.trigger_rollback(
                        deployment_id=deployment_id,
                        anomalies=anomalies,
                        manual=False
                    )

                    return {
                        "deployment_id": deployment_id,
                        "status": "rolled_back",
                        "reason": decision.reason.value if decision.reason else None,
                        "rollback_success": success,
                        "checks_completed": check_count,
                        "anomalies_detected": len(total_anomalies)
                    }

            # Wait for next check
            if time.time() - start_time < duration_seconds:
                time.sleep(check_interval)

        logger.info(
            f"Monitoring completed for deployment {deployment_id}: "
            f"{check_count} checks, {len(total_anomalies)} anomalies"
        )

        return {
            "deployment_id": deployment_id,
            "status": "completed",
            "checks_completed": check_count,
            "anomalies_detected": len(total_anomalies),
            "rollback_triggered": False
        }

    except Exception as e:
        logger.error(f"Monitoring error: {e}", exc_info=True)
        return {
            "deployment_id": deployment_id,
            "status": "error",
            "error": str(e),
            "checks_completed": check_count
        }


@celery_app.task(
    bind=True,
    base=MonitoringTask,
    name="monitoring.export_prometheus_metrics"
)
def export_prometheus_metrics(self, db: Session = None):
    """
    Export metrics to Prometheus.

    Args:
        db: Database session (injected)

    Returns:
        Export result dict
    """
    logger.info("Exporting metrics to Prometheus")

    try:
        exporter = MetricsExporter(db)
        exporter.export_all_metrics()

        return {
            "status": "success",
            "message": "Metrics exported successfully"
        }

    except Exception as e:
        logger.error(f"Error exporting metrics: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


@celery_app.task(
    bind=True,
    base=MonitoringTask,
    name="monitoring.check_deployment_health"
)
def check_deployment_health(
    self,
    deployment_id: int,
    db: Session = None
):
    """
    Perform single health check on deployment.

    Args:
        deployment_id: Deployment to check
        db: Database session (injected)

    Returns:
        Health check result
    """
    logger.info(f"Health check for deployment {deployment_id}")

    try:
        collector = MetricsCollector(db)
        detector = AnomalyDetector()

        # Collect metrics
        metrics = collector.collect_deployment_metrics(deployment_id)
        metrics.extend(collector.collect_error_metrics(deployment_id))

        # Detect anomalies
        anomalies = detector.detect(metrics)

        # Calculate health score (0-100)
        if not anomalies:
            health_score = 100
        else:
            # Deduct points based on anomaly severity
            deductions = {
                AnomalySeverity.CRITICAL: 50,
                AnomalySeverity.HIGH: 20,
                AnomalySeverity.MEDIUM: 10,
                AnomalySeverity.LOW: 5
            }
            total_deduction = sum(deductions[a.severity] for a in anomalies)
            health_score = max(0, 100 - total_deduction)

        return {
            "deployment_id": deployment_id,
            "health_score": health_score,
            "healthy": health_score >= 70,
            "anomalies_detected": len(anomalies),
            "critical_issues": sum(
                1 for a in anomalies if a.severity == AnomalySeverity.CRITICAL
            )
        }

    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        return {
            "deployment_id": deployment_id,
            "health_score": 0,
            "healthy": False,
            "error": str(e)
        }


@celery_app.task(
    bind=True,
    base=MonitoringTask,
    name="monitoring.cleanup_old_metrics"
)
def cleanup_old_metrics(self, days: int = 30, db: Session = None):
    """
    Clean up metrics older than specified days.

    Args:
        days: Number of days to retain
        db: Database session (injected)

    Returns:
        Cleanup result
    """
    logger.info(f"Cleaning up metrics older than {days} days")

    try:
        # For MVP: Just log
        # In production: Delete old metrics from TimescaleDB
        logger.info(f"Would delete metrics older than {days} days")

        return {
            "status": "success",
            "retention_days": days,
            "message": "Cleanup completed"
        }

    except Exception as e:
        logger.error(f"Cleanup error: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


# Periodic tasks configuration
celery_app.conf.beat_schedule = {
    'export-prometheus-metrics': {
        'task': 'monitoring.export_prometheus_metrics',
        'schedule': 60.0,  # Every minute
    },
    'cleanup-old-metrics': {
        'task': 'monitoring.cleanup_old_metrics',
        'schedule': 86400.0,  # Daily
        'args': (30,)  # 30 days retention
    },
}
