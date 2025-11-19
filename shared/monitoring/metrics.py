"""
Prometheus Metrics Module
==========================

Centralized Prometheus metrics for comprehensive application monitoring.

Metrics Categories:
- HTTP API metrics (requests, latency, errors)
- Database metrics (queries, connections, pool)
- Cache metrics (hits, misses, latency)
- Business metrics (vulnerabilities, patches, deployments)
- Celery task metrics (tasks, duration, failures)
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    Info,
)
import time
from functools import wraps
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# HTTP API Metrics
# ============================================================================

# Request counter by method, endpoint, and status code
http_requests_total = Counter(
    "vulnzero_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"]
)

# Request duration histogram
http_request_duration_seconds = Histogram(
    "vulnzero_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

# Active requests gauge
http_requests_in_progress = Gauge(
    "vulnzero_http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"]
)

# Request size summary
http_request_size_bytes = Summary(
    "vulnzero_http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint"]
)

# Response size summary
http_response_size_bytes = Summary(
    "vulnzero_http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"]
)

# Error counter by type
http_errors_total = Counter(
    "vulnzero_http_errors_total",
    "Total HTTP errors",
    ["method", "endpoint", "error_type"]
)

# ============================================================================
# Database Metrics
# ============================================================================

# Query counter
db_queries_total = Counter(
    "vulnzero_db_queries_total",
    "Total database queries",
    ["operation", "table"]
)

# Query duration
db_query_duration_seconds = Histogram(
    "vulnzero_db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

# Slow queries counter (> 1 second)
db_slow_queries_total = Counter(
    "vulnzero_db_slow_queries_total",
    "Total slow database queries (>1s)",
    ["operation", "table"]
)

# Connection pool metrics
db_pool_size = Gauge(
    "vulnzero_db_pool_size",
    "Current database connection pool size"
)

db_pool_checked_out = Gauge(
    "vulnzero_db_pool_connections_checked_out",
    "Number of connections currently checked out from pool"
)

db_pool_overflow = Gauge(
    "vulnzero_db_pool_overflow",
    "Number of connections in overflow"
)

# Database errors
db_errors_total = Counter(
    "vulnzero_db_errors_total",
    "Total database errors",
    ["error_type"]
)

# ============================================================================
# Cache Metrics (Redis)
# ============================================================================

# Cache operations counter
cache_operations_total = Counter(
    "vulnzero_cache_operations_total",
    "Total cache operations",
    ["operation", "status"]  # operation: get/set/delete, status: hit/miss/error
)

# Cache hit ratio (calculated from hits and misses)
cache_hits_total = Counter(
    "vulnzero_cache_hits_total",
    "Total cache hits"
)

cache_misses_total = Counter(
    "vulnzero_cache_misses_total",
    "Total cache misses"
)

# Cache operation duration
cache_operation_duration_seconds = Histogram(
    "vulnzero_cache_operation_duration_seconds",
    "Cache operation duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5)
)

# Cache size gauge
cache_keys_total = Gauge(
    "vulnzero_cache_keys_total",
    "Total number of keys in cache"
)

cache_memory_bytes = Gauge(
    "vulnzero_cache_memory_bytes",
    "Cache memory usage in bytes"
)

# ============================================================================
# Business Metrics
# ============================================================================

# Vulnerability metrics
vulnerabilities_detected_total = Counter(
    "vulnzero_vulnerabilities_detected_total",
    "Total vulnerabilities detected",
    ["severity", "source"]  # severity: critical/high/medium/low, source: nvd/wazuh/qualys
)

vulnerabilities_active = Gauge(
    "vulnzero_vulnerabilities_active",
    "Number of active vulnerabilities",
    ["severity"]
)

vulnerabilities_remediated_total = Counter(
    "vulnzero_vulnerabilities_remediated_total",
    "Total vulnerabilities remediated",
    ["severity", "method"]  # method: auto/manual
)

# Time to remediation
vulnerability_remediation_duration_seconds = Histogram(
    "vulnzero_vulnerability_remediation_duration_seconds",
    "Time from detection to remediation in seconds",
    ["severity"],
    buckets=(60, 300, 900, 1800, 3600, 7200, 14400, 28800, 86400, 172800, 604800)  # 1min to 1week
)

# Patch metrics
patches_generated_total = Counter(
    "vulnzero_patches_generated_total",
    "Total patches generated",
    ["llm_provider", "status"]  # llm_provider: openai/anthropic, status: success/failure
)

patches_tested_total = Counter(
    "vulnzero_patches_tested_total",
    "Total patches tested in digital twin",
    ["result"]  # result: pass/fail
)

patches_deployed_total = Counter(
    "vulnzero_patches_deployed_total",
    "Total patches deployed",
    ["strategy"]  # strategy: blue_green/canary/rolling
)

patch_generation_duration_seconds = Histogram(
    "vulnzero_patch_generation_duration_seconds",
    "Patch generation duration in seconds",
    ["llm_provider"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600)
)

# Deployment metrics
deployments_total = Counter(
    "vulnzero_deployments_total",
    "Total deployments",
    ["strategy", "status"]  # strategy: blue_green/canary, status: success/failure/rollback
)

deployment_duration_seconds = Histogram(
    "vulnzero_deployment_duration_seconds",
    "Deployment duration in seconds",
    ["strategy"],
    buckets=(10, 30, 60, 120, 300, 600, 900, 1800, 3600)
)

rollbacks_total = Counter(
    "vulnzero_rollbacks_total",
    "Total deployment rollbacks",
    ["reason"]  # reason: health_check/error_rate/manual
)

# Asset metrics
assets_monitored = Gauge(
    "vulnzero_assets_monitored",
    "Number of assets being monitored",
    ["type"]  # type: server/container/application
)

# ============================================================================
# Celery Task Metrics
# ============================================================================

# Task counter
celery_tasks_total = Counter(
    "vulnzero_celery_tasks_total",
    "Total Celery tasks",
    ["task_name", "status"]  # status: started/success/failure/retry
)

# Task duration
celery_task_duration_seconds = Histogram(
    "vulnzero_celery_task_duration_seconds",
    "Celery task duration in seconds",
    ["task_name"],
    buckets=(0.1, 0.5, 1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600)
)

# Active tasks
celery_tasks_active = Gauge(
    "vulnzero_celery_tasks_active",
    "Number of active Celery tasks",
    ["task_name"]
)

# Task queue length
celery_queue_length = Gauge(
    "vulnzero_celery_queue_length",
    "Number of tasks in Celery queue",
    ["queue_name"]
)

# Worker metrics
celery_workers_active = Gauge(
    "vulnzero_celery_workers_active",
    "Number of active Celery workers"
)

# Task retries
celery_task_retries_total = Counter(
    "vulnzero_celery_task_retries_total",
    "Total Celery task retries",
    ["task_name", "exception"]
)

# ============================================================================
# System Metrics
# ============================================================================

# Application info
application_info = Info(
    "vulnzero_application",
    "VulnZero application information"
)

# Uptime
application_uptime_seconds = Gauge(
    "vulnzero_application_uptime_seconds",
    "Application uptime in seconds"
)

# Python info
python_info = Info(
    "vulnzero_python",
    "Python runtime information"
)

# ============================================================================
# LLM API Metrics
# ============================================================================

# LLM API calls
llm_api_calls_total = Counter(
    "vulnzero_llm_api_calls_total",
    "Total LLM API calls",
    ["provider", "model", "status"]  # provider: openai/anthropic
)

llm_api_duration_seconds = Histogram(
    "vulnzero_llm_api_duration_seconds",
    "LLM API call duration in seconds",
    ["provider", "model"],
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60, 120)
)

llm_tokens_used_total = Counter(
    "vulnzero_llm_tokens_used_total",
    "Total LLM tokens used",
    ["provider", "model", "type"]  # type: prompt/completion
)

llm_api_errors_total = Counter(
    "vulnzero_llm_api_errors_total",
    "Total LLM API errors",
    ["provider", "error_type"]
)

# ============================================================================
# Event Bus Metrics
# ============================================================================

# Events published
events_published_total = Counter(
    "vulnzero_events_published_total",
    "Total events published to event bus",
    ["event_type", "source_service"]
)

# Events consumed
events_consumed_total = Counter(
    "vulnzero_events_consumed_total",
    "Total events consumed from event bus",
    ["event_type", "handler", "status"]  # status: success/error
)

# Event processing duration
event_processing_duration_seconds = Histogram(
    "vulnzero_event_processing_duration_seconds",
    "Event processing duration in seconds",
    ["event_type"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

# Event processing errors
event_processing_errors_total = Counter(
    "vulnzero_event_processing_errors_total",
    "Total event processing errors",
    ["event_type", "handler", "error_type"]
)

# Event queue depth (if available)
event_queue_depth = Gauge(
    "vulnzero_event_queue_depth",
    "Number of messages in event queue",
    ["queue_name"]
)

# ============================================================================
# Metric Decorators and Helpers
# ============================================================================

def track_time(metric: Histogram, labels: dict = None):
    """
    Decorator to track execution time of a function.

    Usage:
        @track_time(db_query_duration_seconds, {"operation": "select", "table": "vulnerabilities"})
        def get_vulnerabilities():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def track_in_progress(gauge: Gauge, labels: dict = None):
    """
    Decorator to track in-progress operations.

    Increments gauge on entry, decrements on exit.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if labels:
                gauge.labels(**labels).inc()
            else:
                gauge.inc()
            try:
                return func(*args, **kwargs)
            finally:
                if labels:
                    gauge.labels(**labels).dec()
                else:
                    gauge.dec()

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if labels:
                gauge.labels(**labels).inc()
            else:
                gauge.inc()
            try:
                return await func(*args, **kwargs)
            finally:
                if labels:
                    gauge.labels(**labels).dec()
                else:
                    gauge.dec()

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class MetricsContext:
    """
    Context manager for tracking metrics.

    Usage:
        with MetricsContext(db_query_duration_seconds, {"operation": "select"}):
            result = db.execute(query)
    """

    def __init__(self, metric: Histogram, labels: dict = None):
        self.metric = metric
        self.labels = labels or {}
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if self.labels:
            self.metric.labels(**self.labels).observe(duration)
        else:
            self.metric.observe(duration)
        return False


# ============================================================================
# Metric Collection Functions
# ============================================================================

def update_application_info():
    """Update application info metric"""
    from shared.config.settings import settings
    import sys

    application_info.info({
        "version": "0.1.0",
        "environment": settings.environment,
        "python_version": sys.version.split()[0],
    })


def update_db_pool_metrics():
    """Update database connection pool metrics"""
    try:
        from shared.config.database import engine

        pool = engine.pool
        db_pool_size.set(pool.size())
        db_pool_checked_out.set(pool.checkedout())
        db_pool_overflow.set(pool.overflow())

    except Exception as e:
        logger.warning(f"Failed to update DB pool metrics: {e}")


def update_cache_metrics():
    """Update cache metrics from Redis"""
    try:
        from shared.cache import get_redis_client
        import asyncio

        async def _update():
            client = await get_redis_client()
            info = await client.info('memory')
            stats = await client.info('stats')

            # Update metrics
            cache_memory_bytes.set(info.get('used_memory', 0))

            # Key count
            db_size = await client.dbsize()
            cache_keys_total.set(db_size)

        # Run async function
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_update())

    except Exception as e:
        logger.warning(f"Failed to update cache metrics: {e}")


def update_celery_metrics():
    """Update Celery worker and queue metrics"""
    try:
        from shared.celery_app import celery_app

        # Inspect workers
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()

        if active_workers:
            celery_workers_active.set(len(active_workers))

            # Count active tasks
            total_active = sum(len(tasks) for tasks in active_workers.values())
            celery_tasks_active.set(total_active)

    except Exception as e:
        logger.warning(f"Failed to update Celery metrics: {e}")
