"""
Retry Pattern with Exponential Backoff
=======================================

Automatically retry failed operations with increasing delays.
"""

import logging
import time
import random
from typing import Callable, Optional, Tuple, Any
from functools import wraps
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class RetryStrategy(str, Enum):
    """Retry strategies"""

    EXPONENTIAL = "exponential"  # 2^n * base_delay
    LINEAR = "linear"  # n * base_delay
    CONSTANT = "constant"  # base_delay


class MaxRetriesExceeded(Exception):
    """Raised when maximum retries exceeded"""

    pass


def calculate_delay(
    attempt: int,
    base_delay: float,
    strategy: RetryStrategy,
    max_delay: float,
    jitter: bool = True,
) -> float:
    """
    Calculate retry delay based on strategy.

    Args:
        attempt: Retry attempt number (0-indexed)
        base_delay: Base delay in seconds
        strategy: Retry strategy
        max_delay: Maximum delay in seconds
        jitter: Add random jitter to prevent thundering herd

    Returns:
        Delay in seconds
    """
    if strategy == RetryStrategy.EXPONENTIAL:
        delay = base_delay * (2**attempt)
    elif strategy == RetryStrategy.LINEAR:
        delay = base_delay * (attempt + 1)
    else:  # CONSTANT
        delay = base_delay

    # Cap at max_delay
    delay = min(delay, max_delay)

    # Add jitter (0-25% of delay)
    if jitter:
        jitter_amount = delay * random.uniform(0, 0.25)
        delay += jitter_amount

    return delay


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    exceptions: Tuple[type, ...] = (Exception,),
    on_retry: Optional[Callable] = None,
):
    """
    Decorator to retry function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        strategy: Retry strategy (exponential, linear, constant)
        exceptions: Tuple of exceptions to retry on
        on_retry: Optional callback called on each retry

    Usage:
        @retry_with_backoff(
            max_retries=5,
            base_delay=2.0,
            exceptions=(requests.RequestException, httpx.HTTPError)
        )
        async def fetch_data():
            response = await httpx.get("https://api.example.com")
            return response.json()
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(
                            f"Function {func.__name__} succeeded after {attempt} retries"
                        )
                    return result

                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        delay = calculate_delay(
                            attempt=attempt,
                            base_delay=base_delay,
                            strategy=strategy,
                            max_delay=max_delay,
                        )

                        logger.warning(
                            f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}), "
                            f"retrying in {delay:.2f}s. Error: {e}"
                        )

                        # Call retry callback if provided
                        if on_retry:
                            try:
                                if asyncio.iscoroutinefunction(on_retry):
                                    await on_retry(attempt, delay, e)
                                else:
                                    on_retry(attempt, delay, e)
                            except Exception as callback_error:
                                logger.error(
                                    f"Error in retry callback: {callback_error}"
                                )

                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries + 1} attempts"
                        )

            raise MaxRetriesExceeded(
                f"Max retries ({max_retries}) exceeded for {func.__name__}"
            ) from last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(
                            f"Function {func.__name__} succeeded after {attempt} retries"
                        )
                    return result

                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        delay = calculate_delay(
                            attempt=attempt,
                            base_delay=base_delay,
                            strategy=strategy,
                            max_delay=max_delay,
                        )

                        logger.warning(
                            f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}), "
                            f"retrying in {delay:.2f}s. Error: {e}"
                        )

                        # Call retry callback if provided
                        if on_retry:
                            try:
                                on_retry(attempt, delay, e)
                            except Exception as callback_error:
                                logger.error(
                                    f"Error in retry callback: {callback_error}"
                                )

                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries + 1} attempts"
                        )

            raise MaxRetriesExceeded(
                f"Max retries ({max_retries}) exceeded for {func.__name__}"
            ) from last_exception

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Pre-configured retry decorators for common scenarios
def retry_api_call(func: Callable) -> Callable:
    """
    Retry decorator for external API calls.

    3 retries with exponential backoff (1s, 2s, 4s).
    """
    return retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        strategy=RetryStrategy.EXPONENTIAL,
    )(func)


def retry_database_operation(func: Callable) -> Callable:
    """
    Retry decorator for database operations.

    2 retries with linear backoff (2s, 4s).
    """
    return retry_with_backoff(
        max_retries=2,
        base_delay=2.0,
        strategy=RetryStrategy.LINEAR,
    )(func)


def retry_network_call(func: Callable) -> Callable:
    """
    Retry decorator for network operations.

    5 retries with exponential backoff, max 30s delay.
    """
    return retry_with_backoff(
        max_retries=5,
        base_delay=1.0,
        max_delay=30.0,
        strategy=RetryStrategy.EXPONENTIAL,
    )(func)
