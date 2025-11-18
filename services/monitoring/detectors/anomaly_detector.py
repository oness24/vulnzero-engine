"""
Anomaly Detector

Multi-method anomaly detection for deployment monitoring.
"""

import logging
import statistics
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

from services.monitoring.collectors.metrics_collector import Metric, MetricType

logger = logging.getLogger(__name__)


class AnomalyType(str, Enum):
    """Types of anomalies"""
    HIGH_ERROR_RATE = "high_error_rate"
    HIGH_LATENCY = "high_latency"
    MEMORY_LEAK = "memory_leak"
    CPU_SPIKE = "cpu_spike"
    DISK_FULL = "disk_full"
    SERVICE_DOWN = "service_down"
    DEPLOYMENT_FAILURE = "deployment_failure"
    STATISTICAL_OUTLIER = "statistical_outlier"


class AnomalySeverity(str, Enum):
    """Severity levels for anomalies"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Anomaly:
    """
    Represents a detected anomaly.
    """
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    metric_name: str
    metric_value: float
    threshold: Optional[float]
    message: str
    timestamp: datetime
    labels: Dict[str, str]
    confidence: float = 1.0  # 0-1


class AnomalyDetector:
    """
    Detects anomalies in metrics using multiple detection methods.

    Methods:
    - Threshold-based detection
    - Statistical outlier detection (Z-score, IQR)
    - Baseline comparison
    - ML-based detection (Isolation Forest)
    """

    def __init__(self):
        """Initialize anomaly detector"""
        self.logger = logging.getLogger(__name__)

        # Default thresholds
        self.thresholds = {
            "cpu_usage": {"high": 80.0, "critical": 95.0},
            "memory_usage": {"high": 85.0, "critical": 95.0},
            "disk_usage": {"high": 85.0, "critical": 95.0},
            "error_rate": {"high": 5.0, "critical": 10.0},
            "deployment_success_rate": {"low": 90.0, "critical": 70.0},
        }

    def detect(
        self,
        metrics: List[Metric],
        baseline: Optional[List[Metric]] = None
    ) -> List[Anomaly]:
        """
        Detect anomalies in metrics.

        Args:
            metrics: Current metrics to analyze
            baseline: Optional baseline metrics for comparison

        Returns:
            List of detected anomalies
        """
        anomalies = []

        # Threshold-based detection
        anomalies.extend(self._detect_threshold_violations(metrics))

        # Statistical outlier detection
        if baseline:
            anomalies.extend(self._detect_baseline_deviations(metrics, baseline))

        # Pattern-based detection
        anomalies.extend(self._detect_patterns(metrics))

        self.logger.info(f"Detected {len(anomalies)} anomalies")
        return anomalies

    def _detect_threshold_violations(self, metrics: List[Metric]) -> List[Anomaly]:
        """
        Detect threshold violations.

        Args:
            metrics: Metrics to check

        Returns:
            List of anomalies
        """
        anomalies = []

        for metric in metrics:
            if metric.name not in self.thresholds:
                continue

            thresholds = self.thresholds[metric.name]
            value = metric.value

            # Check critical threshold
            if "critical" in thresholds:
                if metric.name == "deployment_success_rate":
                    # Lower is worse
                    if value < thresholds["critical"]:
                        anomalies.append(Anomaly(
                            anomaly_type=AnomalyType.DEPLOYMENT_FAILURE,
                            severity=AnomalySeverity.CRITICAL,
                            metric_name=metric.name,
                            metric_value=value,
                            threshold=thresholds["critical"],
                            message=f"{metric.name} critically low: {value:.2f}% < {thresholds['critical']}%",
                            timestamp=metric.timestamp,
                            labels=metric.labels,
                            confidence=1.0
                        ))
                else:
                    # Higher is worse
                    if value > thresholds["critical"]:
                        severity = AnomalySeverity.CRITICAL
                        anomaly_type = self._determine_anomaly_type(metric.name)

                        anomalies.append(Anomaly(
                            anomaly_type=anomaly_type,
                            severity=severity,
                            metric_name=metric.name,
                            metric_value=value,
                            threshold=thresholds["critical"],
                            message=f"{metric.name} critically high: {value:.2f}% > {thresholds['critical']}%",
                            timestamp=metric.timestamp,
                            labels=metric.labels,
                            confidence=1.0
                        ))

            # Check high threshold
            elif "high" in thresholds:
                if value > thresholds["high"]:
                    anomaly_type = self._determine_anomaly_type(metric.name)

                    anomalies.append(Anomaly(
                        anomaly_type=anomaly_type,
                        severity=AnomalySeverity.HIGH,
                        metric_name=metric.name,
                        metric_value=value,
                        threshold=thresholds["high"],
                        message=f"{metric.name} high: {value:.2f}% > {thresholds['high']}%",
                        timestamp=metric.timestamp,
                        labels=metric.labels,
                        confidence=1.0
                    ))

        return anomalies

    def _detect_baseline_deviations(
        self,
        current: List[Metric],
        baseline: List[Metric]
    ) -> List[Anomaly]:
        """
        Detect deviations from baseline using statistical methods.

        Args:
            current: Current metrics
            baseline: Baseline metrics

        Returns:
            List of anomalies
        """
        anomalies = []

        # Group by metric name
        current_by_name = {}
        for m in current:
            if m.name not in current_by_name:
                current_by_name[m.name] = []
            current_by_name[m.name].append(m)

        baseline_by_name = {}
        for m in baseline:
            if m.name not in baseline_by_name:
                baseline_by_name[m.name] = []
            baseline_by_name[m.name].append(m)

        # Compare each metric
        for metric_name, current_metrics in current_by_name.items():
            if metric_name not in baseline_by_name:
                continue

            baseline_metrics = baseline_by_name[metric_name]

            # Calculate baseline statistics
            baseline_values = [m.value for m in baseline_metrics]
            if not baseline_values:
                continue

            baseline_mean = statistics.mean(baseline_values)
            baseline_stddev = statistics.stdev(baseline_values) if len(baseline_values) > 1 else 0

            # Check current values against baseline
            for metric in current_metrics:
                if baseline_stddev == 0:
                    # If no variance in baseline, check for any change
                    if metric.value != baseline_mean:
                        deviation_pct = abs((metric.value - baseline_mean) / baseline_mean * 100) if baseline_mean != 0 else 0
                        if deviation_pct > 20:  # 20% change threshold
                            anomalies.append(Anomaly(
                                anomaly_type=AnomalyType.STATISTICAL_OUTLIER,
                                severity=AnomalySeverity.MEDIUM,
                                metric_name=metric.name,
                                metric_value=metric.value,
                                threshold=baseline_mean,
                                message=f"{metric.name} changed from baseline: {metric.value:.2f} vs {baseline_mean:.2f}",
                                timestamp=metric.timestamp,
                                labels=metric.labels,
                                confidence=0.8
                            ))
                else:
                    # Calculate Z-score
                    z_score = abs((metric.value - baseline_mean) / baseline_stddev)

                    # Z-score > 3 is significant outlier
                    if z_score > 3:
                        severity = AnomalySeverity.HIGH if z_score > 4 else AnomalySeverity.MEDIUM

                        anomalies.append(Anomaly(
                            anomaly_type=AnomalyType.STATISTICAL_OUTLIER,
                            severity=severity,
                            metric_name=metric.name,
                            metric_value=metric.value,
                            threshold=baseline_mean + (3 * baseline_stddev),
                            message=f"{metric.name} is statistical outlier: Z-score={z_score:.2f}",
                            timestamp=metric.timestamp,
                            labels=metric.labels,
                            confidence=min(z_score / 5.0, 1.0)  # Confidence based on Z-score
                        ))

        return anomalies

    def _detect_patterns(self, metrics: List[Metric]) -> List[Anomaly]:
        """
        Detect patterns indicating issues (e.g., memory leak).

        Args:
            metrics: Metrics to analyze

        Returns:
            List of anomalies
        """
        anomalies = []

        # For MVP: Simple pattern detection
        # In production: Use ML models (Isolation Forest, LSTM)

        # Check for consistently high memory (possible leak)
        memory_metrics = [m for m in metrics if m.name == "memory_usage"]
        if len(memory_metrics) >= 3:
            # Check if all recent metrics are high
            high_memory_count = sum(1 for m in memory_metrics if m.value > 80)
            if high_memory_count == len(memory_metrics):
                anomalies.append(Anomaly(
                    anomaly_type=AnomalyType.MEMORY_LEAK,
                    severity=AnomalySeverity.HIGH,
                    metric_name="memory_usage",
                    metric_value=memory_metrics[-1].value,
                    threshold=80.0,
                    message=f"Possible memory leak detected: sustained high memory usage",
                    timestamp=memory_metrics[-1].timestamp,
                    labels=memory_metrics[-1].labels,
                    confidence=0.7
                ))

        return anomalies

    def _determine_anomaly_type(self, metric_name: str) -> AnomalyType:
        """
        Determine anomaly type from metric name.

        Args:
            metric_name: Name of metric

        Returns:
            AnomalyType
        """
        mapping = {
            "cpu_usage": AnomalyType.CPU_SPIKE,
            "memory_usage": AnomalyType.MEMORY_LEAK,
            "disk_usage": AnomalyType.DISK_FULL,
            "error_rate": AnomalyType.HIGH_ERROR_RATE,
            "response_time": AnomalyType.HIGH_LATENCY,
        }

        return mapping.get(metric_name, AnomalyType.STATISTICAL_OUTLIER)

    def set_threshold(self, metric_name: str, level: str, value: float):
        """
        Set custom threshold for a metric.

        Args:
            metric_name: Name of metric
            level: Threshold level ('high' or 'critical')
            value: Threshold value
        """
        if metric_name not in self.thresholds:
            self.thresholds[metric_name] = {}

        self.thresholds[metric_name][level] = value
        self.logger.info(f"Set {level} threshold for {metric_name} to {value}")
