"""
Timeout Pattern
===============

Prevent operations from running indefinitely.
"""

import logging
import asyncio
from typing import Callable
from functools import wraps

logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Raised when operation times out"""

    pass


def with_timeout(timeout_seconds: float):
    """
    Decorator to add timeout to async functions.

    Args:
        timeout_seconds: Maximum execution time in seconds

    Usage:
        @with_timeout(30.0)
        async def fetch_large_dataset():
            # Will raise TimeoutError if takes > 30 seconds
            data = await slow_api_call()
            return data
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                result = await asyncio.wait_for(
                    func(*args, **kwargs), timeout=timeout_seconds
                )
                return result
            except asyncio.TimeoutError as e:
                logger.error(
                    f"Function {func.__name__} timed out after {timeout_seconds}s"
                )
                raise TimeoutError(
                    f"Operation timed out after {timeout_seconds} seconds"
                ) from e

        if not asyncio.iscoroutinefunction(func):
            raise TypeError(
                f"@with_timeout can only be applied to async functions, "
                f"got {func.__name__}"
            )

        return async_wrapper

    return decorator
