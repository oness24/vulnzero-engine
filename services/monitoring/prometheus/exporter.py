"""
Prometheus Metrics Exporter

Exports VulnZero metrics to Prometheus format.
"""

import logging
from typing import Dict, List
from prometheus_client import Counter, Gauge, Histogram, Info
from sqlalchemy.orm import Session
from sqlalchemy import func

from shared.models import Deployment, Patch, Vulnerability, Asset
from services.monitoring.collectors.metrics_collector import Metric, MetricType

logger = logging.getLogger(__name__)


class MetricsExporter:
    """
    Exports VulnZero metrics to Prometheus.
    """

    def __init__(self, db: Session):
        """
        Initialize metrics exporter.

        Args:
            db: Database session
        """
        self.db = db
        self.logger = logging.getLogger(__name__)

        # Define Prometheus metrics
        self._init_metrics()

    def _init_metrics(self):
        """Initialize Prometheus metric objects"""

        # Deployment metrics
        self.deployments_total = Counter(
            'vulnzero_deployments_total',
            'Total number of deployments',
            ['strategy', 'status']
        )

        self.deployment_duration = Histogram(
            'vulnzero_deployment_duration_seconds',
            'Deployment duration in seconds',
            ['strategy']
        )

        self.deployment_success_rate = Gauge(
            'vulnzero_deployment_success_rate',
            'Deployment success rate percentage',
            ['deployment_id']
        )

        # Patch metrics
        self.patches_total = Gauge(
            'vulnzero_patches_total',
            'Total number of patches',
            ['status', 'type']
        )

        self.patch_confidence = Histogram(
            'vulnzero_patch_confidence_score',
            'Patch confidence scores'
        )

        # Vulnerability metrics
        self.vulnerabilities_total = Gauge(
            'vulnzero_vulnerabilities_total',
            'Total number of vulnerabilities',
            ['severity', 'status']
        )

        self.vulnerabilities_priority = Histogram(
            'vulnzero_vulnerability_priority_score',
            'Vulnerability priority scores'
        )

        # Asset metrics
        self.assets_total = Gauge(
            'vulnzero_assets_total',
            'Total number of managed assets',
            ['type']
        )

        # System metrics
        self.system_cpu_usage = Gauge(
            'vulnzero_system_cpu_usage_percent',
            'System CPU usage percentage',
            ['asset_id']
        )

        self.system_memory_usage = Gauge(
            'vulnzero_system_memory_usage_percent',
            'System memory usage percentage',
            ['asset_id']
        )

        self.system_disk_usage = Gauge(
            'vulnzero_system_disk_usage_percent',
            'System disk usage percentage',
            ['asset_id']
        )

        # Anomaly metrics
        self.anomalies_detected = Counter(
            'vulnzero_anomalies_detected_total',
            'Total number of anomalies detected',
            ['type', 'severity']
        )

        self.rollbacks_triggered = Counter(
            'vulnzero_rollbacks_triggered_total',
            'Total number of rollbacks triggered',
            ['reason', 'manual']
        )

        # Application info
        self.app_info = Info(
            'vulnzero_application',
            'VulnZero application information'
        )
        self.app_info.info({
            'version': '0.1.0',
            'component': 'monitoring'
        })

    def export_deployment_metrics(self):
        """Export deployment metrics to Prometheus"""
        try:
            # Count deployments by strategy and status
            from shared.models import DeploymentStatus
            for strategy in ['all-at-once', 'rolling', 'canary']:
                for status in DeploymentStatus:
                    count = (
                        self.db.query(Deployment)
                        .filter_by(strategy=strategy, status=status)
                        .count()
                    )
                    # Note: This is a counter, so we can't set it directly
                    # In production, would track increments properly

            # Update current deployment success rates
            active_deployments = (
                self.db.query(Deployment)
                .filter(Deployment.status.in_(['in_progress', 'completed']))
                .all()
            )

            for deployment in active_deployments:
                if deployment.total_assets > 0:
                    success_rate = (deployment.successful_assets / deployment.total_assets) * 100
                    self.deployment_success_rate.labels(
                        deployment_id=str(deployment.id)
                    ).set(success_rate)

        except Exception as e:
            self.logger.error(f"Error exporting deployment metrics: {e}", exc_info=True)

    def export_patch_metrics(self):
        """Export patch metrics to Prometheus"""
        try:
            from shared.models import PatchStatus, PatchType

            # Count patches by status and type
            for status in PatchStatus:
                for patch_type in PatchType:
                    count = (
                        self.db.query(Patch)
                        .filter_by(status=status, patch_type=patch_type)
                        .count()
                    )
                    self.patches_total.labels(
                        status=status.value,
                        type=patch_type.value
                    ).set(count)

            # Patch confidence scores
            patches = self.db.query(Patch).filter(Patch.confidence_score.isnot(None)).all()
            for patch in patches:
                self.patch_confidence.observe(patch.confidence_score / 100)  # 0-1 scale

        except Exception as e:
            self.logger.error(f"Error exporting patch metrics: {e}", exc_info=True)

    def export_vulnerability_metrics(self):
        """Export vulnerability metrics to Prometheus"""
        try:
            from shared.models import VulnerabilityStatus

            # Count by severity and status
            for severity in ['low', 'medium', 'high', 'critical']:
                for status in VulnerabilityStatus:
                    count = (
                        self.db.query(Vulnerability)
                        .filter_by(severity=severity, status=status)
                        .count()
                    )
                    self.vulnerabilities_total.labels(
                        severity=severity,
                        status=status.value
                    ).set(count)

            # Priority scores
            vulns = self.db.query(Vulnerability).filter(
                Vulnerability.priority_score.isnot(None)
            ).all()
            for vuln in vulns:
                self.vulnerabilities_priority.observe(vuln.priority_score / 100)

        except Exception as e:
            self.logger.error(f"Error exporting vulnerability metrics: {e}", exc_info=True)

    def export_asset_metrics(self):
        """Export asset metrics to Prometheus"""
        try:
            # Count by asset type
            asset_types = self.db.query(Asset.asset_type, func.count(Asset.id)).group_by(
                Asset.asset_type
            ).all()

            for asset_type, count in asset_types:
                self.assets_total.labels(type=asset_type or "unknown").set(count)

        except Exception as e:
            self.logger.error(f"Error exporting asset metrics: {e}", exc_info=True)

    def export_system_metrics(self, metrics: List[Metric]):
        """
        Export system metrics to Prometheus.

        Args:
            metrics: List of collected metrics
        """
        for metric in metrics:
            labels = metric.labels

            if metric.metric_type == MetricType.SYSTEM_CPU:
                asset_id = labels.get("asset_id", "unknown")
                self.system_cpu_usage.labels(asset_id=asset_id).set(metric.value)

            elif metric.metric_type == MetricType.SYSTEM_MEMORY:
                if "stat" not in labels:  # Main memory usage metric
                    asset_id = labels.get("asset_id", "unknown")
                    self.system_memory_usage.labels(asset_id=asset_id).set(metric.value)

            elif metric.metric_type == MetricType.SYSTEM_DISK:
                if "stat" not in labels:  # Main disk usage metric
                    asset_id = labels.get("asset_id", "unknown")
                    self.system_disk_usage.labels(asset_id=asset_id).set(metric.value)

    def export_all_metrics(self):
        """Export all VulnZero metrics to Prometheus"""
        self.logger.info("Exporting all metrics to Prometheus")

        self.export_deployment_metrics()
        self.export_patch_metrics()
        self.export_vulnerability_metrics()
        self.export_asset_metrics()

        self.logger.info("Metrics export complete")
