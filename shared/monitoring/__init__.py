"""Monitoring and metrics module for VulnZero"""

from shared.monitoring.metrics import (
    # HTTP metrics
    http_requests_total,
    http_request_duration_seconds,
    http_requests_in_progress,
    http_request_size_bytes,
    http_response_size_bytes,
    http_errors_total,

    # Database metrics
    db_queries_total,
    db_query_duration_seconds,
    db_slow_queries_total,
    db_pool_size,
    db_pool_checked_out,

    # Cache metrics
    cache_hits_total,
    cache_misses_total,
    cache_operation_duration_seconds,

    # Business metrics
    vulnerabilities_detected_total,
    vulnerabilities_active,
    patches_generated_total,
    patches_deployed_total,
    deployments_total,

    # Celery metrics
    celery_tasks_total,
    celery_task_duration_seconds,
    celery_tasks_active,

    # LLM metrics
    llm_api_calls_total,
    llm_api_duration_seconds,
    llm_tokens_used_total,

    # Decorators and helpers
    track_time,
    track_in_progress,
    MetricsContext,

    # Update functions
    update_application_info,
    update_db_pool_metrics,
    update_cache_metrics,
    update_celery_metrics,
)

__all__ = [
    # HTTP metrics
    "http_requests_total",
    "http_request_duration_seconds",
    "http_requests_in_progress",
    "http_request_size_bytes",
    "http_response_size_bytes",
    "http_errors_total",

    # Database metrics
    "db_queries_total",
    "db_query_duration_seconds",
    "db_slow_queries_total",
    "db_pool_size",
    "db_pool_checked_out",

    # Cache metrics
    "cache_hits_total",
    "cache_misses_total",
    "cache_operation_duration_seconds",

    # Business metrics
    "vulnerabilities_detected_total",
    "vulnerabilities_active",
    "patches_generated_total",
    "patches_deployed_total",
    "deployments_total",

    # Celery metrics
    "celery_tasks_total",
    "celery_task_duration_seconds",
    "celery_tasks_active",

    # LLM metrics
    "llm_api_calls_total",
    "llm_api_duration_seconds",
    "llm_tokens_used_total",

    # Decorators and helpers
    "track_time",
    "track_in_progress",
    "MetricsContext",

    # Update functions
    "update_application_info",
    "update_db_pool_metrics",
    "update_cache_metrics",
    "update_celery_metrics",
]
