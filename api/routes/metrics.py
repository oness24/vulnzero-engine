"""
Prometheus metrics endpoint
"""

from fastapi import APIRouter, Response
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
)
from prometheus_client.multiprocess import MultiProcessCollector
import os

router = APIRouter(tags=["metrics"])

# Create registry
registry = CollectorRegistry()

# Check if running in multiprocess mode (multiple Uvicorn workers)
if "PROMETHEUS_MULTIPROC_DIR" in os.environ:
    # Use multiprocess collector for multiple workers
    MultiProcessCollector(registry)
else:
    # Single process mode - use default registry
    from prometheus_client import REGISTRY
    registry = REGISTRY

# Define metrics
# Counters
http_requests_total = Counter(
    'vulnzero_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

vulnerabilities_detected_total = Counter(
    'vulnzero_vulnerabilities_detected_total',
    'Total vulnerabilities detected',
    ['severity'],
    registry=registry
)

patches_generated_total = Counter(
    'vulnzero_patches_generated_total',
    'Total patches generated',
    ['type'],
    registry=registry
)

deployments_total = Counter(
    'vulnzero_deployments_total',
    'Total deployments',
    ['status', 'environment'],
    registry=registry
)

# Histograms
request_duration_seconds = Histogram(
    'vulnzero_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=registry
)

patch_generation_duration_seconds = Histogram(
    'vulnzero_patch_generation_duration_seconds',
    'Patch generation duration in seconds',
    ['llm_provider'],
    registry=registry
)

deployment_duration_seconds = Histogram(
    'vulnzero_deployment_duration_seconds',
    'Deployment duration in seconds',
    ['environment'],
    registry=registry
)

# Gauges
active_vulnerabilities = Gauge(
    'vulnzero_active_vulnerabilities',
    'Number of active vulnerabilities',
    ['severity'],
    registry=registry
)

pending_deployments = Gauge(
    'vulnzero_pending_deployments',
    'Number of pending deployments',
    registry=registry
)

active_websocket_connections = Gauge(
    'vulnzero_active_websocket_connections',
    'Number of active WebSocket connections',
    registry=registry
)

system_health_score = Gauge(
    'vulnzero_system_health_score',
    'System health score (0-100)',
    registry=registry
)


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint

    Returns metrics in Prometheus text format
    """
    # Generate latest metrics
    metrics_output = generate_latest(registry)

    return Response(
        content=metrics_output,
        media_type=CONTENT_TYPE_LATEST,
    )


# Helper functions to update metrics
def increment_http_requests(method: str, endpoint: str, status: int):
    """Increment HTTP request counter"""
    http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()


def increment_vulnerabilities_detected(severity: str):
    """Increment vulnerabilities detected counter"""
    vulnerabilities_detected_total.labels(severity=severity).inc()


def increment_patches_generated(patch_type: str):
    """Increment patches generated counter"""
    patches_generated_total.labels(type=patch_type).inc()


def increment_deployments(status: str, environment: str):
    """Increment deployments counter"""
    deployments_total.labels(status=status, environment=environment).inc()


def observe_request_duration(method: str, endpoint: str, duration: float):
    """Observe HTTP request duration"""
    request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)


def observe_patch_generation_duration(llm_provider: str, duration: float):
    """Observe patch generation duration"""
    patch_generation_duration_seconds.labels(llm_provider=llm_provider).observe(duration)


def observe_deployment_duration(environment: str, duration: float):
    """Observe deployment duration"""
    deployment_duration_seconds.labels(environment=environment).observe(duration)


def set_active_vulnerabilities(severity: str, count: int):
    """Set active vulnerabilities gauge"""
    active_vulnerabilities.labels(severity=severity).set(count)


def set_pending_deployments(count: int):
    """Set pending deployments gauge"""
    pending_deployments.set(count)


def set_active_websocket_connections(count: int):
    """Set active WebSocket connections gauge"""
    active_websocket_connections.set(count)


def set_system_health_score(score: float):
    """Set system health score (0-100)"""
    system_health_score.set(score)
