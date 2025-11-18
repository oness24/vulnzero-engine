"""
Shared utility modules for VulnZero

Provides common utilities used across the application:
- Error handling and custom exceptions
- API response formatting helpers
- Retry decorators
- Validation helpers
"""

from shared.utils.error_handling import (
    ErrorCode,
    VulnZeroException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ConflictError,
    DatabaseError,
    ExternalServiceError,
    retry_on_exception,
    log_error,
    handle_errors,
)

from shared.utils.response_helpers import (
    success_response,
    error_response,
    paginated_response,
    created_response,
    deleted_response,
    no_content_response,
    ListQueryParams,
    calculate_offset,
    parse_sort_params,
    SuccessResponse,
    ErrorResponse,
    PaginatedResponse,
    PaginationMeta,
)

__all__ = [
    # Error handling
    "ErrorCode",
    "VulnZeroException",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ConflictError",
    "DatabaseError",
    "ExternalServiceError",
    "retry_on_exception",
    "log_error",
    "handle_errors",
    # Response helpers
    "success_response",
    "error_response",
    "paginated_response",
    "created_response",
    "deleted_response",
    "no_content_response",
    "ListQueryParams",
    "calculate_offset",
    "parse_sort_params",
    "SuccessResponse",
    "ErrorResponse",
    "PaginatedResponse",
    "PaginationMeta",
]
