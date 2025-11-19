"""Resilience patterns for fault tolerance"""

from shared.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerError,
    circuit_breaker,
)
from shared.resilience.retry import (
    retry_with_backoff,
    RetryStrategy,
    MaxRetriesExceeded,
)
from shared.resilience.timeout import (
    with_timeout,
    TimeoutError,
)
from shared.resilience.bulkhead import (
    Bulkhead,
    BulkheadRejectedError,
)

__all__ = [
    # Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerState",
    "CircuitBreakerError",
    "circuit_breaker",
    # Retry
    "retry_with_backoff",
    "RetryStrategy",
    "MaxRetriesExceeded",
    # Timeout
    "with_timeout",
    "TimeoutError",
    # Bulkhead
    "Bulkhead",
    "BulkheadRejectedError",
]
