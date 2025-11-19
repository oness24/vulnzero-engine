"""
Bulkhead Pattern
================

Limit concurrent operations to prevent resource exhaustion.
"""

import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)


class BulkheadRejectedError(Exception):
    """Raised when bulkhead rejects request due to capacity"""

    pass


class Bulkhead:
    """
    Bulkhead implementation using semaphore.

    Limits number of concurrent operations to prevent resource exhaustion.

    Usage:
        bulkhead = Bulkhead(max_concurrent=10, name="api-calls")

        async with bulkhead:
            # Only 10 operations can run concurrently
            response = await httpx.get(url)
    """

    def __init__(
        self,
        max_concurrent: int,
        max_wait_time: Optional[float] = None,
        name: str = "default",
    ):
        """
        Initialize bulkhead.

        Args:
            max_concurrent: Maximum concurrent operations
            max_wait_time: Maximum time to wait for slot (None = wait forever)
            name: Bulkhead name for logging
        """
        self.max_concurrent = max_concurrent
        self.max_wait_time = max_wait_time
        self.name = name
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._current_count = 0

        logger.info(
            f"Bulkhead '{name}' initialized "
            f"(max_concurrent={max_concurrent}, max_wait={max_wait_time}s)"
        )

    async def __aenter__(self):
        """Async context manager entry"""
        try:
            if self.max_wait_time:
                # Try to acquire with timeout
                acquired = await asyncio.wait_for(
                    self.semaphore.acquire(), timeout=self.max_wait_time
                )
                if not acquired:
                    raise BulkheadRejectedError(
                        f"Bulkhead '{self.name}' rejected request "
                        f"(max concurrent: {self.max_concurrent})"
                    )
            else:
                # Wait indefinitely
                await self.semaphore.acquire()

            self._current_count += 1
            return self

        except asyncio.TimeoutError:
            raise BulkheadRejectedError(
                f"Bulkhead '{self.name}' rejected request after {self.max_wait_time}s wait "
                f"(max concurrent: {self.max_concurrent})"
            )

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self._current_count -= 1
        self.semaphore.release()
        return False

    @property
    def current_count(self) -> int:
        """Get current number of operations in progress"""
        return self._current_count

    @property
    def available_slots(self) -> int:
        """Get number of available slots"""
        return self.max_concurrent - self._current_count


# Global bulkhead registry
_bulkheads: dict[str, Bulkhead] = {}


def get_bulkhead(
    name: str, max_concurrent: int = 10, max_wait_time: Optional[float] = None
) -> Bulkhead:
    """
    Get or create bulkhead by name.

    Args:
        name: Bulkhead name
        max_concurrent: Maximum concurrent operations
        max_wait_time: Maximum wait time in seconds

    Returns:
        Bulkhead instance
    """
    if name not in _bulkheads:
        _bulkheads[name] = Bulkhead(
            max_concurrent=max_concurrent, max_wait_time=max_wait_time, name=name
        )

    return _bulkheads[name]
