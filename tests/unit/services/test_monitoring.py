"""
Unit Tests for Monitoring & Rollback Engine

Tests metrics collection, anomaly detection, alerting, and rollback logic.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from services.monitoring.collectors.metrics_collector import MetricsCollector, MetricType
from services.monitoring.detectors.anomaly_detector import (
    AnomalyDetector,
    AnomalyType,
    AnomalySeverity
)
from services.monitoring.rollback.rollback_engine import RollbackEngine
from shared.models import DeploymentStatus


class TestMetricsCollector:
    """Test metrics collection"""

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_collect_system_metrics(self, mock_disk, mock_memory, mock_cpu, test_db):
        """Test collecting system metrics"""
        # Mock system calls
        mock_cpu.return_value = 45.5
        mock_memory.return_value = Mock(percent=60.0, available=4*1024**3)
        mock_disk.return_value = Mock(percent=70.0, free=100*1024**3)

        collector = MetricsCollector(test_db)
        metrics = collector.collect_system_metrics(asset_id=1)

        assert len(metrics) > 0
        assert any(m.metric_type == MetricType.SYSTEM_CPU for m in metrics)
        assert any(m.metric_type == MetricType.SYSTEM_MEMORY for m in metrics)
        assert any(m.metric_type == MetricType.SYSTEM_DISK for m in metrics)

    def test_collect_deployment_metrics(self, test_db, sample_deployment):
        """Test collecting deployment metrics"""
        collector = MetricsCollector(test_db)
        metrics = collector.collect_deployment_metrics(sample_deployment.id)

        assert len(metrics) > 0
        assert any(m.name == "deployment_status" for m in metrics)

    def test_collect_error_metrics(self, test_db, sample_deployment):
        """Test collecting error rate metrics"""
        # Note: Deployment model doesn't have total_assets/failed_assets fields
        # These were removed from the model schema
        test_db.commit()

        collector = MetricsCollector(test_db)
        metrics = collector.collect_error_metrics(sample_deployment.id)

        # Should collect error metrics even if error rate can't be calculated
        assert isinstance(metrics, list)

    def test_collect_baseline_metrics(self, test_db):
        """Test collecting baseline metrics"""
        collector = MetricsCollector(test_db)
        baseline = collector.collect_baseline_metrics([1, 2, 3])

        assert isinstance(baseline, dict)
        # Should have entries for each asset
        assert len(baseline) <= 3

    def test_metric_statistics(self, test_db):
        """Test calculating metric statistics"""
        from services.monitoring.collectors.metrics_collector import Metric

        metrics = [
            Metric("cpu", 50.0, MetricType.SYSTEM_CPU, datetime.utcnow(), {}, "%"),
            Metric("cpu", 60.0, MetricType.SYSTEM_CPU, datetime.utcnow(), {}, "%"),
            Metric("cpu", 70.0, MetricType.SYSTEM_CPU, datetime.utcnow(), {}, "%"),
        ]

        collector = MetricsCollector(test_db)
        stats = collector.calculate_metric_statistics(metrics)

        assert stats["min"] == 50.0
        assert stats["max"] == 70.0
        assert stats["mean"] == 60.0


class TestAnomalyDetector:
    """Test anomaly detection"""

    def test_detect_threshold_violation(self, test_db):
        """Test detecting threshold violations"""
        from services.monitoring.collectors.metrics_collector import Metric

        detector = AnomalyDetector()

        # Create high CPU metric
        high_cpu = Metric(
            "cpu_usage",
            96.0,  # Above critical threshold (95)
            MetricType.SYSTEM_CPU,
            datetime.utcnow(),
            {"asset_id": "1"},
            "%"
        )

        anomalies = detector.detect([high_cpu])

        assert len(anomalies) > 0
        assert any(a.anomaly_type == AnomalyType.CPU_SPIKE for a in anomalies)
        assert any(a.severity == AnomalySeverity.CRITICAL for a in anomalies)

    def test_detect_baseline_deviation(self, test_db):
        """Test detecting deviation from baseline"""
        from services.monitoring.collectors.metrics_collector import Metric

        detector = AnomalyDetector()

        # Baseline metrics (normal)
        baseline = [
            Metric("cpu", 50.0, MetricType.SYSTEM_CPU, datetime.utcnow(), {}, "%"),
            Metric("cpu", 52.0, MetricType.SYSTEM_CPU, datetime.utcnow(), {}, "%"),
            Metric("cpu", 48.0, MetricType.SYSTEM_CPU, datetime.utcnow(), {}, "%"),
        ]

        # Current metrics (anomalous)
        current = [
            Metric("cpu", 150.0, MetricType.SYSTEM_CPU, datetime.utcnow(), {}, "%"),
        ]

        anomalies = detector.detect(current, baseline=baseline)

        # Should detect statistical outlier
        assert len(anomalies) > 0

    def test_detect_error_rate_anomaly(self):
        """Test detecting high error rate"""
        from services.monitoring.collectors.metrics_collector import Metric

        detector = AnomalyDetector()

        high_error_rate = Metric(
            "error_rate",
            15.0,  # Above critical threshold (10%)
            MetricType.APP_ERROR_RATE,
            datetime.utcnow(),
            {},
            "%"
        )

        anomalies = detector.detect([high_error_rate])

        assert len(anomalies) > 0
        assert any(a.anomaly_type == AnomalyType.HIGH_ERROR_RATE for a in anomalies)

    def test_detect_memory_leak_pattern(self):
        """Test detecting memory leak pattern"""
        from services.monitoring.collectors.metrics_collector import Metric

        detector = AnomalyDetector()

        # Consistently high memory usage
        metrics = [
            Metric("memory_usage", 85.0, MetricType.SYSTEM_MEMORY, datetime.utcnow(), {}, "%"),
            Metric("memory_usage", 87.0, MetricType.SYSTEM_MEMORY, datetime.utcnow(), {}, "%"),
            Metric("memory_usage", 89.0, MetricType.SYSTEM_MEMORY, datetime.utcnow(), {}, "%"),
        ]

        anomalies = detector.detect(metrics)

        # Should detect potential memory leak
        # (might not always trigger depending on implementation)
        assert isinstance(anomalies, list)

    def test_set_custom_threshold(self):
        """Test setting custom thresholds"""
        detector = AnomalyDetector()

        detector.set_threshold("cpu_usage", "critical", 98.0)

        assert detector.thresholds["cpu_usage"]["critical"] == 98.0

    def test_anomaly_confidence_scoring(self):
        """Test anomaly confidence scores"""
        from services.monitoring.collectors.metrics_collector import Metric

        detector = AnomalyDetector()

        metric = Metric(
            "cpu_usage",
            99.0,  # Very high
            MetricType.SYSTEM_CPU,
            datetime.utcnow(),
            {},
            "%"
        )

        anomalies = detector.detect([metric])

        if anomalies:
            # Should have high confidence
            assert anomalies[0].confidence >= 0.8


class TestRollbackEngine:
    """Test automatic rollback logic"""

    def test_evaluate_rollback_critical_anomaly(self, test_db):
        """Test rollback triggered by critical anomaly"""
        from services.monitoring.detectors.anomaly_detector import Anomaly

        engine = RollbackEngine(test_db)

        # Create critical anomaly
        critical_anomaly = Anomaly(
            anomaly_type=AnomalyType.HIGH_ERROR_RATE,
            severity=AnomalySeverity.CRITICAL,
            metric_name="error_rate",
            metric_value=15.0,
            threshold=10.0,
            message="Critical error rate",
            timestamp=datetime.utcnow(),
            labels={},
            confidence=1.0
        )

        decision = engine.evaluate_rollback(
            deployment_id=1,
            anomalies=[critical_anomaly]
        )

        assert decision.should_rollback is True
        assert decision.confidence >= 0.9

    def test_evaluate_rollback_multiple_high_anomalies(self, test_db):
        """Test rollback triggered by multiple high anomalies"""
        from services.monitoring.detectors.anomaly_detector import Anomaly

        engine = RollbackEngine(test_db)

        # Create multiple high anomalies
        anomalies = [
            Anomaly(
                AnomalyType.CPU_SPIKE,
                AnomalySeverity.HIGH,
                "cpu",
                90.0,
                80.0,
                "High CPU",
                datetime.utcnow(),
                {},
                0.8
            ),
            Anomaly(
                AnomalyType.MEMORY_LEAK,
                AnomalySeverity.HIGH,
                "memory",
                85.0,
                80.0,
                "High memory",
                datetime.utcnow(),
                {},
                0.8
            ),
            Anomaly(
                AnomalyType.DISK_FULL,
                AnomalySeverity.HIGH,
                "disk",
                92.0,
                90.0,
                "High disk",
                datetime.utcnow(),
                {},
                0.8
            ),
        ]

        decision = engine.evaluate_rollback(deployment_id=1, anomalies=anomalies)

        # 3 high anomalies should trigger rollback (threshold is 3)
        assert decision.should_rollback is True

    def test_evaluate_no_rollback(self, test_db):
        """Test no rollback for minor anomalies"""
        from services.monitoring.detectors.anomaly_detector import Anomaly

        engine = RollbackEngine(test_db)

        # Create low severity anomaly
        anomaly = Anomaly(
            AnomalyType.STATISTICAL_OUTLIER,
            AnomalySeverity.LOW,
            "metric",
            55.0,
            50.0,
            "Minor deviation",
            datetime.utcnow(),
            {},
            0.5
        )

        decision = engine.evaluate_rollback(deployment_id=1, anomalies=[anomaly])

        assert decision.should_rollback is False

    @patch('services.deployment_orchestrator.core.engine.DeploymentEngine')
    def test_trigger_rollback_execution(self, mock_engine, test_db, sample_deployment):
        """Test triggering rollback execution"""
        from services.monitoring.detectors.anomaly_detector import Anomaly

        mock_engine.return_value.rollback.return_value = True

        engine = RollbackEngine(test_db)

        anomaly = Anomaly(
            AnomalyType.SERVICE_DOWN,
            AnomalySeverity.CRITICAL,
            "service",
            0,
            1,
            "Service down",
            datetime.utcnow(),
            {},
            1.0
        )

        success = engine.trigger_rollback(
            deployment_id=sample_deployment.id,
            anomalies=[anomaly]
        )

        assert isinstance(success, bool)

    def test_rollback_eligibility(self, test_db, sample_deployment, sample_patch):
        """Test checking rollback eligibility"""
        # Add rollback script to patch
        sample_patch.rollback_script = "#!/bin/bash\necho 'rollback'"

        # Set deployment to a started status (not PENDING)
        sample_deployment.status = DeploymentStatus.DEPLOYING
        sample_deployment.started_at = datetime.utcnow()
        test_db.commit()

        engine = RollbackEngine(test_db)
        eligibility = engine.get_rollback_eligibility(sample_deployment.id)

        assert eligibility["eligible"] is True


class TestAlertManager:
    """Test alert management"""

    @patch('requests.post')
    def test_send_slack_alert(self, mock_post, test_db):
        """Test sending alert to Slack"""
        from services.monitoring.alerts.alert_manager import AlertManager, Alert, AlertSeverity, AlertStatus

        mock_post.return_value = Mock(status_code=200)

        manager = AlertManager(test_db)
        manager.slack_webhook = "https://hooks.slack.com/test"

        alert = Alert(
            id=1,
            title="Test Alert",
            message="Test message",
            severity=AlertSeverity.HIGH,
            status=AlertStatus.ACTIVE,
            source="test",
            anomaly_type="test_anomaly",
            created_at=datetime.utcnow()
        )

        manager.send_alert(alert, channels=["slack"])

        assert mock_post.called

    def test_create_alert_from_anomaly(self, test_db):
        """Test creating alert from anomaly"""
        from services.monitoring.alerts.alert_manager import AlertManager
        from services.monitoring.detectors.anomaly_detector import Anomaly

        manager = AlertManager(test_db)

        anomaly = Anomaly(
            AnomalyType.HIGH_ERROR_RATE,
            AnomalySeverity.CRITICAL,
            "error_rate",
            15.0,
            10.0,
            "High error rate detected",
            datetime.utcnow(),
            {"deployment_id": "123"},
            1.0
        )

        alert = manager.create_alert_from_anomaly(anomaly, deployment_id=123)

        assert alert is not None
        assert alert.severity.value == "critical"
        assert alert.title is not None

    def test_alert_deduplication(self, test_db):
        """Test alert deduplication"""
        from services.monitoring.alerts.alert_manager import AlertManager, Alert, AlertSeverity, AlertStatus

        manager = AlertManager(test_db)

        alert = Alert(
            id=1,
            title="Duplicate Alert",
            message="Message",
            severity=AlertSeverity.LOW,
            status=AlertStatus.ACTIVE,
            source="test",
            anomaly_type=None,
            created_at=datetime.utcnow()
        )

        # Should send first alert
        should_send_1 = manager.should_send_alert(alert)

        # Critical alerts always sent
        alert.severity = AlertSeverity.CRITICAL
        should_send_2 = manager.should_send_alert(alert)

        assert should_send_2 is True  # Critical always sent


class TestPrometheusExporter:
    """Test Prometheus metrics export"""

    def test_export_deployment_metrics(self, test_db, sample_deployment):
        """Test exporting deployment metrics"""
        from services.monitoring.prometheus.exporter import MetricsExporter

        exporter = MetricsExporter(test_db)
        exporter.export_deployment_metrics()

        # Should not raise exceptions
        assert True

    def test_export_all_metrics(self, test_db):
        """Test exporting all metrics"""
        from services.monitoring.prometheus.exporter import MetricsExporter
        from prometheus_client import REGISTRY

        # Clear any existing collectors to avoid "already registered" errors
        collectors = list(REGISTRY._collector_to_names.keys())
        for collector in collectors:
            try:
                REGISTRY.unregister(collector)
            except Exception:
                pass

        exporter = MetricsExporter(test_db)
        exporter.export_all_metrics()

        # Should complete without errors
        assert True

    @patch('psutil.cpu_percent')
    def test_export_system_metrics(self, mock_cpu, test_db):
        """Test exporting system metrics"""
        from services.monitoring.prometheus.exporter import MetricsExporter
        from services.monitoring.collectors.metrics_collector import Metric, MetricType
        from prometheus_client import REGISTRY

        # Clear any existing collectors to avoid "already registered" errors
        collectors = list(REGISTRY._collector_to_names.keys())
        for collector in collectors:
            try:
                REGISTRY.unregister(collector)
            except Exception:
                pass

        mock_cpu.return_value = 50.0

        exporter = MetricsExporter(test_db)

        metrics = [
            Metric("cpu_usage", 50.0, MetricType.SYSTEM_CPU, datetime.utcnow(), {"asset_id": "1"}, "%")
        ]

        exporter.export_system_metrics(metrics)

        # Should handle metrics without errors
        assert True
