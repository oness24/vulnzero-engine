"""
Monitoring and observability modules for VulnZero

Provides:
- Sentry error tracking
- Performance monitoring
- Custom metrics
"""

from shared.monitoring.sentry_config import (
    init_sentry,
    init_sentry_for_environment,
    set_user_context,
    set_context,
    add_breadcrumb,
    capture_exception,
    capture_message,
    SENTRY_CONFIGS,
)

__all__ = [
    "init_sentry",
    "init_sentry_for_environment",
    "set_user_context",
    "set_context",
    "add_breadcrumb",
    "capture_exception",
    "capture_message",
    "SENTRY_CONFIGS",
]
