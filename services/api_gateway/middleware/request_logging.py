"""
Request Logging Middleware

Structured logging with correlation IDs for request tracing across services.
Logs all requests with timing, status codes, and custom context.
"""

import time
import uuid
import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

logger = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request logging with correlation IDs.

    Features:
    - Unique request ID for tracing
    - Request/response timing
    - Structured logging (JSON format)
    - Error tracking
    - Custom context propagation
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process request and log with correlation ID"""

        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Store in request state for use in routes
        request.state.request_id = request_id

        # Extract client info
        client_host = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # Extract user info if authenticated
        user_id = "anonymous"
        user_email = None

        # Try to get user from auth header (JWT)
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                # This would decode JWT in real implementation
                # For now, just note that auth is present
                user_id = "authenticated"
            except:
                pass

        # Create structured log context
        log_context = structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=client_host,
            user_agent=user_agent,
            user_id=user_id,
        )

        # Log request start
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            request_id=request_id,
            client_ip=client_host,
        )

        # Record start time
        start_time = time.time()

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log successful response
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                request_id=request_id,
                client_ip=client_host,
            )

            # Add headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            return response

        except Exception as e:
            # Calculate duration even on error
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 2),
                request_id=request_id,
                client_ip=client_host,
                exc_info=True,
            )

            # Re-raise to be handled by exception handlers
            raise

        finally:
            # Clear context vars
            structlog.contextvars.clear_contextvars()


class DatabaseQueryLogger:
    """
    Context manager for logging slow database queries.

    Usage:
        with DatabaseQueryLogger("fetch_vulnerabilities", threshold_ms=100):
            results = db.query(Vulnerability).all()
    """

    def __init__(self, query_name: str, threshold_ms: float = 100):
        self.query_name = query_name
        self.threshold_ms = threshold_ms
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000

        if duration_ms > self.threshold_ms:
            logger.warning(
                "slow_database_query",
                query_name=self.query_name,
                duration_ms=round(duration_ms, 2),
                threshold_ms=self.threshold_ms,
            )
        else:
            logger.debug(
                "database_query",
                query_name=self.query_name,
                duration_ms=round(duration_ms, 2),
            )


class CeleryTaskLogger:
    """
    Decorator for logging Celery task execution.

    Usage:
        @celery_app.task
        @CeleryTaskLogger.log_task
        def my_task(param1, param2):
            pass
    """

    @staticmethod
    def log_task(func):
        """Decorator to log Celery task execution"""

        def wrapper(*args, **kwargs):
            task_id = kwargs.get("task_id", "unknown")
            task_name = func.__name__

            logger.info(
                "celery_task_started",
                task_name=task_name,
                task_id=task_id,
                args_count=len(args),
                kwargs_keys=list(kwargs.keys()),
            )

            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                duration_s = time.time() - start_time

                logger.info(
                    "celery_task_completed",
                    task_name=task_name,
                    task_id=task_id,
                    duration_s=round(duration_s, 2),
                    success=True,
                )

                return result

            except Exception as e:
                duration_s = time.time() - start_time

                logger.error(
                    "celery_task_failed",
                    task_name=task_name,
                    task_id=task_id,
                    error=str(e),
                    error_type=type(e).__name__,
                    duration_s=round(duration_s, 2),
                    exc_info=True,
                )

                raise

        return wrapper


def configure_structured_logging():
    """
    Configure structlog for structured JSON logging.

    Call this at application startup.
    """

    structlog.configure(
        processors=[
            # Add log level
            structlog.stdlib.add_log_level,
            # Add timestamp
            structlog.processors.TimeStamper(fmt="iso"),
            # Format stack info
            structlog.processors.StackInfoRenderer(),
            # Format exceptions
            structlog.processors.format_exc_info,
            # Add context variables
            structlog.contextvars.merge_contextvars,
            # Render as JSON
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


class CorrelationIDFilter(logging.Filter):
    """
    Logging filter to add correlation ID to log records.

    Useful for standard logging when structlog isn't used.
    """

    def filter(self, record):
        # Try to get request ID from context
        try:
            from starlette.requests import Request
            # This would need to be passed through context
            # For now, add placeholder
            record.request_id = getattr(record, "request_id", "none")
        except:
            record.request_id = "none"

        return True


def get_logger_with_context(name: str, **context):
    """
    Get a logger with pre-bound context.

    Usage:
        logger = get_logger_with_context(__name__, service="api-gateway")
        logger.info("service_started", version="1.0.0")
    """

    log = structlog.get_logger(name)

    if context:
        log = log.bind(**context)

    return log
