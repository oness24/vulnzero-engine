"""
Metrics Collector

Collects system, application, and deployment metrics for monitoring.
"""

import logging
import psutil
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import func

from shared.models import Deployment, Asset

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Metric type enumeration"""
    SYSTEM_CPU = "system_cpu"
    SYSTEM_MEMORY = "system_memory"
    SYSTEM_DISK = "system_disk"
    SYSTEM_NETWORK = "system_network"
    APP_RESPONSE_TIME = "app_response_time"
    APP_ERROR_RATE = "app_error_rate"
    APP_THROUGHPUT = "app_throughput"
    DEPLOYMENT_STATUS = "deployment_status"
    DEPLOYMENT_SUCCESS_RATE = "deployment_success_rate"
    HEALTH_CHECK = "health_check"


@dataclass
class Metric:
    """
    Represents a single metric data point.
    """
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    labels: Dict[str, str]
    unit: str = ""


class MetricsCollector:
    """
    Collects various metrics from system, application, and deployments.
    """

    def __init__(self, db: Session):
        """
        Initialize metrics collector.

        Args:
            db: Database session
        """
        self.db = db
        self.logger = logging.getLogger(__name__)

    def collect_system_metrics(self, asset_id: Optional[int] = None) -> List[Metric]:
        """
        Collect system metrics (CPU, memory, disk, network).

        Args:
            asset_id: Optional asset ID for labeling

        Returns:
            List of system metrics
        """
        metrics = []
        timestamp = datetime.utcnow()
        labels = {"asset_id": str(asset_id)} if asset_id else {}

        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics.append(Metric(
                name="cpu_usage",
                value=cpu_percent,
                metric_type=MetricType.SYSTEM_CPU,
                timestamp=timestamp,
                labels=labels,
                unit="%"
            ))

            # Memory metrics
            memory = psutil.virtual_memory()
            metrics.append(Metric(
                name="memory_usage",
                value=memory.percent,
                metric_type=MetricType.SYSTEM_MEMORY,
                timestamp=timestamp,
                labels=labels,
                unit="%"
            ))
            metrics.append(Metric(
                name="memory_available",
                value=memory.available / (1024 ** 3),  # GB
                metric_type=MetricType.SYSTEM_MEMORY,
                timestamp=timestamp,
                labels={**labels, "stat": "available"},
                unit="GB"
            ))

            # Disk metrics
            disk = psutil.disk_usage('/')
            metrics.append(Metric(
                name="disk_usage",
                value=disk.percent,
                metric_type=MetricType.SYSTEM_DISK,
                timestamp=timestamp,
                labels=labels,
                unit="%"
            ))
            metrics.append(Metric(
                name="disk_free",
                value=disk.free / (1024 ** 3),  # GB
                metric_type=MetricType.SYSTEM_DISK,
                timestamp=timestamp,
                labels={**labels, "stat": "free"},
                unit="GB"
            ))

            # Network I/O
            net_io = psutil.net_io_counters()
            metrics.append(Metric(
                name="network_bytes_sent",
                value=net_io.bytes_sent,
                metric_type=MetricType.SYSTEM_NETWORK,
                timestamp=timestamp,
                labels={**labels, "direction": "sent"},
                unit="bytes"
            ))
            metrics.append(Metric(
                name="network_bytes_recv",
                value=net_io.bytes_recv,
                metric_type=MetricType.SYSTEM_NETWORK,
                timestamp=timestamp,
                labels={**labels, "direction": "recv"},
                unit="bytes"
            ))

        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}", exc_info=True)

        return metrics

    def collect_deployment_metrics(self, deployment_id: int) -> List[Metric]:
        """
        Collect metrics for a specific deployment.

        Args:
            deployment_id: Deployment ID

        Returns:
            List of deployment metrics
        """
        metrics = []
        timestamp = datetime.utcnow()

        try:
            deployment = self.db.query(Deployment).filter_by(id=deployment_id).first()
            if not deployment:
                self.logger.warning(f"Deployment {deployment_id} not found")
                return metrics

            labels = {
                "deployment_id": str(deployment_id),
                "patch_id": str(deployment.patch_id),
                "strategy": deployment.strategy
            }

            # Deployment status (0=pending, 1=in_progress, 2=completed, 3=failed, 4=rolled_back)
            status_map = {
                "pending": 0,
                "in_progress": 1,
                "completed": 2,
                "failed": 3,
                "rolled_back": 4
            }
            metrics.append(Metric(
                name="deployment_status",
                value=status_map.get(deployment.status.value, -1),
                metric_type=MetricType.DEPLOYMENT_STATUS,
                timestamp=timestamp,
                labels=labels,
                unit=""
            ))

            # Success rate
            if deployment.total_assets > 0:
                success_rate = (deployment.successful_assets / deployment.total_assets) * 100
                metrics.append(Metric(
                    name="deployment_success_rate",
                    value=success_rate,
                    metric_type=MetricType.DEPLOYMENT_SUCCESS_RATE,
                    timestamp=timestamp,
                    labels=labels,
                    unit="%"
                ))

            # Asset counts
            metrics.append(Metric(
                name="deployment_total_assets",
                value=deployment.total_assets,
                metric_type=MetricType.DEPLOYMENT_STATUS,
                timestamp=timestamp,
                labels={**labels, "stat": "total"},
                unit="count"
            ))
            metrics.append(Metric(
                name="deployment_successful_assets",
                value=deployment.successful_assets,
                metric_type=MetricType.DEPLOYMENT_STATUS,
                timestamp=timestamp,
                labels={**labels, "stat": "successful"},
                unit="count"
            ))
            metrics.append(Metric(
                name="deployment_failed_assets",
                value=deployment.failed_assets,
                metric_type=MetricType.DEPLOYMENT_STATUS,
                timestamp=timestamp,
                labels={**labels, "stat": "failed"},
                unit="count"
            ))

        except Exception as e:
            self.logger.error(
                f"Error collecting deployment metrics for {deployment_id}: {e}",
                exc_info=True
            )

        return metrics

    def collect_error_metrics(self, deployment_id: int, window_minutes: int = 5) -> List[Metric]:
        """
        Collect error rate metrics for a deployment.

        Args:
            deployment_id: Deployment ID
            window_minutes: Time window for error rate calculation

        Returns:
            List of error metrics
        """
        metrics = []
        timestamp = datetime.utcnow()

        try:
            deployment = self.db.query(Deployment).filter_by(id=deployment_id).first()
            if not deployment:
                return metrics

            labels = {"deployment_id": str(deployment_id)}

            # Calculate error rate from failed assets
            if deployment.total_assets > 0:
                error_rate = (deployment.failed_assets / deployment.total_assets) * 100
                metrics.append(Metric(
                    name="error_rate",
                    value=error_rate,
                    metric_type=MetricType.APP_ERROR_RATE,
                    timestamp=timestamp,
                    labels=labels,
                    unit="%"
                ))

        except Exception as e:
            self.logger.error(f"Error collecting error metrics: {e}", exc_info=True)

        return metrics

    def collect_baseline_metrics(self, asset_ids: List[int]) -> Dict[str, List[Metric]]:
        """
        Collect baseline metrics before deployment for comparison.

        Args:
            asset_ids: List of asset IDs to collect baseline for

        Returns:
            Dict mapping asset_id to list of baseline metrics
        """
        baseline = {}
        self.logger.info(f"Collecting baseline metrics for {len(asset_ids)} assets")

        for asset_id in asset_ids:
            try:
                # Collect system metrics for baseline
                metrics = self.collect_system_metrics(asset_id=asset_id)
                baseline[str(asset_id)] = metrics
            except Exception as e:
                self.logger.error(
                    f"Error collecting baseline for asset {asset_id}: {e}",
                    exc_info=True
                )

        return baseline

    def get_metric_history(
        self,
        metric_name: str,
        hours: int = 1,
        labels: Optional[Dict[str, str]] = None
    ) -> List[Metric]:
        """
        Get historical metric data.

        Args:
            metric_name: Name of metric to retrieve
            hours: Number of hours of history
            labels: Optional label filters

        Returns:
            List of historical metric data points
        """
        # For MVP: Return empty list
        # In production: Query from TimescaleDB or Prometheus
        self.logger.debug(
            f"Fetching {hours}h history for metric: {metric_name} with labels: {labels}"
        )
        return []

    def calculate_metric_statistics(self, metrics: List[Metric]) -> Dict[str, float]:
        """
        Calculate statistics for a list of metrics.

        Args:
            metrics: List of metrics

        Returns:
            Dict with min, max, mean, stddev
        """
        if not metrics:
            return {"min": 0, "max": 0, "mean": 0, "stddev": 0}

        values = [m.value for m in metrics]

        import statistics

        return {
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "stddev": statistics.stdev(values) if len(values) > 1 else 0
        }
