"""
Centralized error handling utilities for VulnZero

Provides:
- Custom exception classes
- Error response formatting
- Error logging helpers
- Sentry integration
- Retry decorators
"""

import functools
import time
from typing import Optional, Callable, Any, Dict
from enum import Enum
import structlog

logger = structlog.get_logger()


class ErrorCode(str, Enum):
    """Standard error codes for VulnZero"""

    # Client errors (4xx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Server errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"

    # Business logic errors
    PATCH_GENERATION_FAILED = "PATCH_GENERATION_FAILED"
    DEPLOYMENT_FAILED = "DEPLOYMENT_FAILED"
    ROLLBACK_FAILED = "ROLLBACK_FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"


class VulnZeroException(Exception):
    """Base exception for VulnZero application"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response"""
        return {
            "error": {
                "message": self.message,
                "code": self.error_code.value,
                "details": self.details
            }
        }


class ValidationError(VulnZeroException):
    """Validation error"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details=details
        )


class AuthenticationError(VulnZeroException):
    """Authentication error"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHENTICATION_ERROR,
            status_code=401
        )


class AuthorizationError(VulnZeroException):
    """Authorization error"""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHORIZATION_ERROR,
            status_code=403
        )


class NotFoundError(VulnZeroException):
    """Resource not found error"""

    def __init__(self, resource: str, resource_id: Any):
        super().__init__(
            message=f"{resource} not found: {resource_id}",
            error_code=ErrorCode.NOT_FOUND,
            status_code=404,
            details={"resource": resource, "id": str(resource_id)}
        )


class ConflictError(VulnZeroException):
    """Resource conflict error"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.CONFLICT,
            status_code=409,
            details=details
        )


class DatabaseError(VulnZeroException):
    """Database operation error"""

    def __init__(self, message: str, operation: str):
        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_ERROR,
            status_code=500,
            details={"operation": operation}
        )


class ExternalServiceError(VulnZeroException):
    """External service integration error"""

    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"{service} error: {message}",
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            status_code=502,
            details={"service": service}
        )


def retry_on_exception(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to retry function on exception with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Backoff multiplier for each retry
        exceptions: Tuple of exceptions to catch and retry

    Example:
        @retry_on_exception(max_retries=3, delay=1.0, exceptions=(DatabaseError,))
        async def fetch_data():
            return await db.query(...)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        logger.warning(
                            "function_retry",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            delay=current_delay,
                            error=str(e)
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            "function_max_retries_exceeded",
                            function=func.__name__,
                            max_retries=max_retries,
                            error=str(e),
                            exc_info=True
                        )

            # All retries exhausted
            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        logger.warning(
                            "function_retry",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            delay=current_delay,
                            error=str(e)
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            "function_max_retries_exceeded",
                            function=func.__name__,
                            max_retries=max_retries,
                            error=str(e),
                            exc_info=True
                        )

            raise last_exception

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    send_to_sentry: bool = True
):
    """
    Log error with context and optionally send to Sentry

    Args:
        error: Exception to log
        context: Additional context dictionary
        send_to_sentry: Whether to send error to Sentry

    Example:
        try:
            risky_operation()
        except Exception as e:
            log_error(e, context={"user_id": 123, "operation": "patch_generation"})
            raise
    """
    error_context = context or {}

    # Log to structured logger
    logger.error(
        "error_occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        **error_context,
        exc_info=True
    )

    # Send to Sentry if configured
    if send_to_sentry:
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                for key, value in error_context.items():
                    scope.set_context(key, value)
                sentry_sdk.capture_exception(error)
        except ImportError:
            # Sentry not installed, skip
            pass
        except Exception as sentry_error:
            logger.warning(
                "sentry_error_reporting_failed",
                error=str(sentry_error)
            )


def handle_errors(func: Callable) -> Callable:
    """
    Decorator to catch and log errors in route handlers

    Example:
        @router.get("/vulnerabilities")
        @handle_errors
        async def list_vulnerabilities():
            return await get_vulnerabilities()
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except VulnZeroException:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Log unexpected errors
            log_error(e, context={"function": func.__name__})
            raise VulnZeroException(
                message="An unexpected error occurred",
                error_code=ErrorCode.INTERNAL_ERROR,
                status_code=500,
                details={"function": func.__name__}
            )

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except VulnZeroException:
            raise
        except Exception as e:
            log_error(e, context={"function": func.__name__})
            raise VulnZeroException(
                message="An unexpected error occurred",
                error_code=ErrorCode.INTERNAL_ERROR,
                status_code=500,
                details={"function": func.__name__}
            )

    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper
