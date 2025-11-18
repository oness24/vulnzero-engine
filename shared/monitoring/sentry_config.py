"""
Sentry error tracking configuration for VulnZero

Provides centralized Sentry SDK initialization and configuration for:
- Backend API (FastAPI)
- Celery workers
- Frontend (React) - via environment variables

Usage:
    from shared.monitoring.sentry_config import init_sentry

    # In your application startup
    init_sentry(environment="production", release="v1.0.0")
"""

import os
from typing import Optional
import structlog

logger = structlog.get_logger()


def init_sentry(
    dsn: Optional[str] = None,
    environment: str = "development",
    release: Optional[str] = None,
    sample_rate: float = 1.0,
    traces_sample_rate: float = 0.1,
    enable_tracing: bool = True
) -> bool:
    """
    Initialize Sentry SDK for error tracking and performance monitoring

    Args:
        dsn: Sentry DSN (Data Source Name). If None, reads from SENTRY_DSN env var
        environment: Environment name (development, staging, production)
        release: Release version (e.g., "vulnzero@1.0.0")
        sample_rate: Error sampling rate (1.0 = 100%)
        traces_sample_rate: Performance tracing sample rate (0.1 = 10%)
        enable_tracing: Whether to enable performance tracing

    Returns:
        bool: True if Sentry was initialized successfully, False otherwise

    Example:
        # In api/main.py startup event
        init_sentry(
            environment="production",
            release="vulnzero@1.2.3",
            traces_sample_rate=0.2  # 20% of transactions
        )
    """
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        # Get DSN from parameter or environment variable
        sentry_dsn = dsn or os.getenv("SENTRY_DSN")

        if not sentry_dsn:
            logger.warning(
                "sentry_not_configured",
                message="SENTRY_DSN not provided, error tracking disabled"
            )
            return False

        # Determine release version
        if not release:
            # Try to get from git or environment
            release = os.getenv("RELEASE_VERSION") or os.getenv("GIT_COMMIT_SHA")

        # Configure integrations
        integrations = [
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            RedisIntegration(),
            CeleryIntegration(),
            LoggingIntegration(
                level=None,  # Capture all log levels
                event_level=None  # Don't send logs as events (only errors)
            ),
        ]

        # Initialize Sentry
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            release=release,
            sample_rate=sample_rate,
            traces_sample_rate=traces_sample_rate if enable_tracing else 0.0,
            integrations=integrations,
            # Send default PII (like user IP, user agent)
            send_default_pii=True,
            # Attach stack locals to errors (helpful for debugging)
            attach_stacktrace=True,
            # Performance monitoring options
            profiles_sample_rate=0.1 if enable_tracing else 0.0,
            # Before send hook for filtering
            before_send=before_send_hook,
        )

        logger.info(
            "sentry_initialized",
            environment=environment,
            release=release,
            traces_sample_rate=traces_sample_rate
        )

        return True

    except ImportError:
        logger.warning(
            "sentry_import_error",
            message="sentry-sdk not installed, error tracking disabled"
        )
        return False

    except Exception as e:
        logger.error(
            "sentry_initialization_failed",
            error=str(e),
            exc_info=True
        )
        return False


def before_send_hook(event, hint):
    """
    Filter and modify events before sending to Sentry

    Use this to:
    - Filter out sensitive data
    - Ignore certain errors
    - Add custom context

    Args:
        event: Sentry event dictionary
        hint: Additional context about the event

    Returns:
        Modified event or None to drop the event
    """
    # Ignore health check endpoint errors
    if event.get("request", {}).get("url", "").endswith("/health"):
        return None

    # Ignore rate limit errors (already logged elsewhere)
    if "RateLimitExceeded" in event.get("exception", {}).get("values", [{}])[0].get("type", ""):
        return None

    # Filter sensitive data from request body
    if "request" in event and "data" in event["request"]:
        data = event["request"]["data"]
        if isinstance(data, dict):
            # Redact sensitive fields
            sensitive_fields = ["password", "token", "api_key", "secret"]
            for field in sensitive_fields:
                if field in data:
                    data[field] = "[REDACTED]"

    return event


def set_user_context(user_id: str, email: Optional[str] = None, username: Optional[str] = None):
    """
    Set user context for Sentry error tracking

    Call this after user authentication to associate errors with specific users

    Args:
        user_id: User ID
        email: User email (optional)
        username: Username (optional)

    Example:
        # After successful login
        set_user_context(
            user_id=str(user.id),
            email=user.email,
            username=user.username
        )
    """
    try:
        import sentry_sdk
        sentry_sdk.set_user({
            "id": user_id,
            "email": email,
            "username": username
        })
    except ImportError:
        pass


def set_context(context_name: str, context_data: dict):
    """
    Add custom context to Sentry events

    Args:
        context_name: Name of the context (e.g., "vulnerability", "deployment")
        context_data: Dictionary of context data

    Example:
        set_context("patch_generation", {
            "vulnerability_id": vuln_id,
            "llm_provider": "openai",
            "model": "gpt-4"
        })
    """
    try:
        import sentry_sdk
        sentry_sdk.set_context(context_name, context_data)
    except ImportError:
        pass


def add_breadcrumb(message: str, category: str = "info", level: str = "info", data: Optional[dict] = None):
    """
    Add breadcrumb for debugging error context

    Breadcrumbs are a trail of events leading up to an error

    Args:
        message: Breadcrumb message
        category: Breadcrumb category (e.g., "auth", "db", "api")
        level: Severity level (debug, info, warning, error)
        data: Additional structured data

    Example:
        add_breadcrumb(
            message="Starting patch generation",
            category="patch",
            data={"vulnerability_id": 123}
        )
    """
    try:
        import sentry_sdk
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {}
        )
    except ImportError:
        pass


def capture_exception(error: Exception, extra: Optional[dict] = None):
    """
    Manually capture an exception to Sentry

    Use when you want to log an error but still handle it gracefully

    Args:
        error: Exception to capture
        extra: Additional context data

    Example:
        try:
            risky_operation()
        except ValueError as e:
            capture_exception(e, extra={"input": user_input})
            return default_value
    """
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            if extra:
                for key, value in extra.items():
                    scope.set_extra(key, value)
            sentry_sdk.capture_exception(error)
    except ImportError:
        pass


def capture_message(message: str, level: str = "info", extra: Optional[dict] = None):
    """
    Capture a message to Sentry (not an exception)

    Useful for logging important events

    Args:
        message: Message to log
        level: Severity level (debug, info, warning, error, fatal)
        extra: Additional context data

    Example:
        capture_message(
            "Patch deployment completed",
            level="info",
            extra={"deployment_id": 123, "status": "success"}
        )
    """
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            if extra:
                for key, value in extra.items():
                    scope.set_extra(key, value)
            sentry_sdk.capture_message(message, level=level)
    except ImportError:
        pass


# Environment-specific configuration presets
SENTRY_CONFIGS = {
    "development": {
        "sample_rate": 1.0,  # Capture all errors
        "traces_sample_rate": 0.0,  # No performance tracing
        "enable_tracing": False,
    },
    "staging": {
        "sample_rate": 1.0,
        "traces_sample_rate": 0.5,  # 50% of transactions
        "enable_tracing": True,
    },
    "production": {
        "sample_rate": 1.0,  # Capture all errors
        "traces_sample_rate": 0.1,  # 10% of transactions (cost control)
        "enable_tracing": True,
    },
}


def init_sentry_for_environment(env: str = "development", **kwargs) -> bool:
    """
    Initialize Sentry with environment-specific presets

    Args:
        env: Environment name (development, staging, production)
        **kwargs: Override any configuration parameters

    Returns:
        bool: True if initialized successfully

    Example:
        # Use production preset
        init_sentry_for_environment("production", release="v1.2.3")
    """
    config = SENTRY_CONFIGS.get(env, SENTRY_CONFIGS["development"])
    config.update(kwargs)
    config["environment"] = env

    return init_sentry(**config)
