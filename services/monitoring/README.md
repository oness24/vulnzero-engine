# VulnZero Monitoring & Rollback Engine

Real-time monitoring, anomaly detection, and automatic rollback system for VulnZero deployments.

## Overview

The Monitoring & Rollback Engine provides comprehensive monitoring of deployed patches with automatic anomaly detection and rollback capabilities.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│     Metrics     │────▶│     Anomaly      │────▶│     Alert       │
│   Collectors    │     │    Detectors     │     │    Manager      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                 │                         │
                                 ▼                         ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │    Rollback     │     │   Notifications │
                        │     Engine      │     │   (Slack, Email)│
                        └─────────────────┘     └─────────────────┘
```

## Components

### 1. Metrics Collectors (`collectors/`)
- **MetricsCollector**: Collects system and application metrics
- **SystemMetrics**: CPU, memory, disk, network metrics
- **ApplicationMetrics**: Response times, error rates, throughput
- **DeploymentMetrics**: Deployment-specific tracking

### 2. Anomaly Detectors (`detectors/`)
- **AnomalyDetector**: ML-based anomaly detection
- **StatisticalDetector**: Statistical outlier detection (Z-score, IQR)
- **ThresholdDetector**: Simple threshold-based detection
- **BaselineComparison**: Compare against pre-deployment baseline

### 3. Alert Manager (`alerts/`)
- **AlertManager**: Alert generation and routing
- **NotificationChannels**: Slack, email, webhook integrations
- **AlertRules**: Configurable alert rules and severity levels

### 4. Rollback Engine (`rollback/`)
- **RollbackEngine**: Automatic rollback orchestration
- **RollbackDecisionMaker**: Decides when to trigger rollback
- **RollbackExecutor**: Executes rollback operations

### 5. Prometheus Integration (`prometheus/`)
- **MetricsExporter**: Exports metrics to Prometheus
- **PrometheusClient**: Prometheus client integration

### 6. Celery Tasks (`tasks/`)
- **monitoring_tasks**: Async monitoring operations
- **alert_tasks**: Async alert processing
- **rollback_tasks**: Async rollback execution

## Features

### ✅ Real-Time Monitoring
- System metrics (CPU, memory, disk, network)
- Application metrics (latency, errors, throughput)
- Deployment health metrics

### ✅ Anomaly Detection
- **Statistical Methods**: Z-score, IQR outlier detection
- **ML-Based**: Isolation Forest for complex patterns
- **Threshold-Based**: Configurable static thresholds
- **Baseline Comparison**: Compare against pre-deployment state

### ✅ Automatic Rollback
- Triggered on critical anomalies
- Pre-deployment snapshot comparison
- Configurable rollback thresholds
- Manual override capability

### ✅ Alerting
- Multi-channel notifications (Slack, Email, Webhook)
- Severity-based routing
- Alert deduplication
- Escalation policies

### ✅ Prometheus Integration
- Standard metric formats
- Custom VulnZero metrics
- Grafana dashboard compatibility

## Usage

### Basic Monitoring

```python
from services.monitoring import MetricsCollector, AnomalyDetector, RollbackEngine
from sqlalchemy.orm import Session

# Initialize components
collector = MetricsCollector(db)
detector = AnomalyDetector()
rollback_engine = RollbackEngine(db)

# Start monitoring a deployment
deployment_id = 123
metrics = collector.collect_deployment_metrics(deployment_id)

# Check for anomalies
anomalies = detector.detect(metrics)

# Automatic rollback if critical anomalies detected
if any(a.severity == "critical" for a in anomalies):
    rollback_engine.trigger_rollback(deployment_id, anomalies)
```

### Async Monitoring (Celery)

```python
from services.monitoring.tasks.monitoring_tasks import monitor_deployment

# Start monitoring task
task = monitor_deployment.delay(
    deployment_id=123,
    duration_seconds=900,  # 15 minutes
    check_interval=60      # Check every minute
)
```

### Custom Alert Rules

```python
from services.monitoring import AlertManager, AlertSeverity

alert_manager = AlertManager(db)

# Create custom alert rule
alert_manager.create_rule(
    name="High Error Rate",
    metric="error_rate",
    threshold=5.0,  # 5% error rate
    severity=AlertSeverity.CRITICAL,
    channels=["slack", "email"]
)
```

## Anomaly Types

| Type | Description | Severity |
|------|-------------|----------|
| `HIGH_ERROR_RATE` | Error rate exceeds threshold | Critical |
| `HIGH_LATENCY` | Response time degradation | High |
| `MEMORY_LEAK` | Memory usage trending up | High |
| `CPU_SPIKE` | CPU usage spike | Medium |
| `SERVICE_DOWN` | Service unavailable | Critical |
| `DISK_FULL` | Disk space exhausted | High |

## Configuration

### Environment Variables

```bash
# Monitoring Settings
MONITORING_ENABLED=true
MONITORING_INTERVAL=60  # seconds
ANOMALY_THRESHOLD=0.95  # confidence threshold

# Rollback Settings
AUTO_ROLLBACK_ENABLED=true
ROLLBACK_THRESHOLD_CRITICAL=1  # Number of critical anomalies
ROLLBACK_THRESHOLD_HIGH=3      # Number of high anomalies

# Prometheus
PROMETHEUS_PORT=9090
PROMETHEUS_SCRAPE_INTERVAL=15s

# Alerts
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
ALERT_EMAIL_FROM=alerts@vulnzero.com
ALERT_EMAIL_TO=ops-team@company.com
```

## Rollback Decision Logic

```python
# Automatic rollback is triggered when:
1. Critical anomalies >= 1 OR
2. High anomalies >= 3 OR
3. Error rate > 10% OR
4. Service downtime > 60 seconds
```

## Metrics Collected

### System Metrics
- CPU usage (%)
- Memory usage (MB, %)
- Disk usage (GB, %)
- Network I/O (bytes/s)

### Application Metrics
- Request count
- Error count
- Response time (p50, p95, p99)
- Throughput (req/s)

### Deployment Metrics
- Deployment status
- Success rate
- Rollback count
- Health check results

## Integration with Deployment Orchestrator

The monitoring engine automatically integrates with the Deployment Orchestrator to:

1. **Start monitoring** when deployment begins
2. **Collect baseline** before deployment
3. **Monitor continuously** during deployment
4. **Trigger rollback** on anomalies
5. **Stop monitoring** after deployment completes

## Dashboard Metrics

Grafana dashboards are provided for:
- Real-time deployment monitoring
- Anomaly detection visualization
- Rollback history
- Alert timeline

Import dashboards from `infrastructure/grafana/dashboards/`.

## Testing

```bash
# Run unit tests
pytest tests/unit/monitoring/

# Run integration tests
pytest tests/integration/monitoring/

# Test anomaly detection
pytest tests/unit/monitoring/test_anomaly_detector.py

# Test rollback engine
pytest tests/unit/monitoring/test_rollback_engine.py
```

## Development

### Adding New Metrics

```python
# In collectors/metrics_collector.py
def collect_custom_metric(self, asset_id: int) -> float:
    # Your collection logic
    return metric_value
```

### Adding New Anomaly Detectors

```python
# In detectors/anomaly_detector.py
class CustomDetector(BaseDetector):
    def detect(self, metrics: List[Metric]) -> List[Anomaly]:
        # Your detection logic
        pass
```

### Adding New Alert Channels

```python
# In alerts/channels/
class CustomChannel(NotificationChannel):
    def send(self, alert: Alert):
        # Your notification logic
        pass
```

## Production Considerations

- **Scaling**: Use dedicated Celery workers for monitoring tasks
- **Storage**: Metrics stored in TimescaleDB for time-series optimization
- **Retention**: Default 30-day retention for metrics
- **High Availability**: Run multiple monitoring workers
- **Performance**: Batch metric collection to reduce overhead

## Troubleshooting

### Monitoring Not Starting
- Check `MONITORING_ENABLED` environment variable
- Verify Celery workers are running
- Check database connectivity

### Rollback Not Triggering
- Verify `AUTO_ROLLBACK_ENABLED=true`
- Check anomaly detection thresholds
- Review rollback decision logs

### Alerts Not Sending
- Verify notification channel credentials
- Check alert rule configuration
- Review alert manager logs

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/docs/)
- [Anomaly Detection Algorithms](https://scikit-learn.org/stable/modules/outlier_detection.html)
