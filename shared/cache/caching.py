"""
Redis Caching System
====================

Comprehensive caching strategies for performance optimization.

Features:
- Function result caching with decorators
- Automatic key generation
- TTL (Time-To-Live) management
- Cache invalidation patterns
- Metrics integration
"""

import json
import hashlib
import logging
import functools
from typing import Any, Callable, Optional, Union, List
from datetime import timedelta
import asyncio

from shared.cache.redis_client import get_redis_client
from shared.monitoring import (
    cache_hits_total,
    cache_misses_total,
    cache_operation_duration_seconds,
)

logger = logging.getLogger(__name__)


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate deterministic cache key from function arguments.

    Args:
        prefix: Namespace prefix (e.g., "vuln", "patch", "asset")
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Cache key string like "vuln:abc123def456"
    """
    # Create a string representation of all arguments
    key_data = {
        "args": args,
        "kwargs": kwargs,
    }

    # Serialize to JSON (sorted for determinism)
    key_str = json.dumps(key_data, sort_keys=True, default=str)

    # Hash for reasonable key length
    key_hash = hashlib.md5(key_str.encode()).hexdigest()

    return f"{prefix}:{key_hash}"


def cache(
    ttl: Union[int, timedelta] = 300,
    prefix: str = "default",
    key_builder: Optional[Callable] = None,
):
    """
    Decorator to cache function results in Redis.

    Args:
        ttl: Time-to-live in seconds (or timedelta object)
        prefix: Cache key prefix/namespace
        key_builder: Custom function to build cache key (optional)

    Usage:
        @cache(ttl=600, prefix="vuln")
        def get_vulnerability(vuln_id: int):
            return db.query(Vulnerability).get(vuln_id)

        @cache(ttl=timedelta(hours=1), prefix="stats")
        async def get_statistics():
            return calculate_stats()
    """

    if isinstance(ttl, timedelta):
        ttl_seconds = int(ttl.total_seconds())
    else:
        ttl_seconds = ttl

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = generate_cache_key(prefix, *args, **kwargs)

            try:
                # Try to get from cache
                redis_client = await get_redis_client()

                import time
                start_time = time.time()

                cached_value = await redis_client.get(cache_key)

                duration = time.time() - start_time
                cache_operation_duration_seconds.labels(operation="get").observe(duration)

                if cached_value is not None:
                    # Cache hit
                    cache_hits_total.inc()
                    logger.debug(f"Cache HIT: {cache_key}")
                    return json.loads(cached_value)

                # Cache miss
                cache_misses_total.inc()
                logger.debug(f"Cache MISS: {cache_key}")

                # Execute function
                result = await func(*args, **kwargs)

                # Store in cache
                start_time = time.time()
                await redis_client.setex(
                    cache_key,
                    ttl_seconds,
                    json.dumps(result, default=str)
                )
                duration = time.time() - start_time
                cache_operation_duration_seconds.labels(operation="set").observe(duration)

                return result

            except Exception as e:
                logger.warning(f"Cache error for {cache_key}: {e}. Executing function without cache.")
                # Fall back to executing function without cache
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, run async wrapper in event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running (e.g., in FastAPI), use run_until_complete won't work
                # Fall back to no caching in this case
                logger.warning(f"Cannot cache synchronous function {func.__name__} in running event loop")
                return func(*args, **kwargs)
            else:
                return loop.run_until_complete(async_wrapper(*args, **kwargs))

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class CacheManager:
    """
    Manages cache operations with high-level API.

    Usage:
        cache_mgr = CacheManager()
        await cache_mgr.set("user:123", user_data, ttl=3600)
        user_data = await cache_mgr.get("user:123")
    """

    def __init__(self):
        self.redis_client = None

    async def _get_client(self):
        """Get Redis client, initializing if needed"""
        if self.redis_client is None:
            self.redis_client = await get_redis_client()
        return self.redis_client

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache.

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        try:
            client = await self._get_client()

            import time
            start_time = time.time()

            value = await client.get(key)

            duration = time.time() - start_time
            cache_operation_duration_seconds.labels(operation="get").observe(duration)

            if value is None:
                cache_misses_total.inc()
                return default

            cache_hits_total.inc()
            return json.loads(value)

        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            return default

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Union[int, timedelta, None] = None
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time-to-live in seconds (or timedelta)

        Returns:
            True if successful
        """
        try:
            client = await self._get_client()

            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())

            import time
            start_time = time.time()

            serialized = json.dumps(value, default=str)

            if ttl:
                await client.setex(key, ttl, serialized)
            else:
                await client.set(key, serialized)

            duration = time.time() - start_time
            cache_operation_duration_seconds.labels(operation="set").observe(duration)

            return True

        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            return False

    async def delete(self, *keys: str) -> int:
        """
        Delete one or more keys from cache.

        Args:
            *keys: Keys to delete

        Returns:
            Number of keys deleted
        """
        try:
            client = await self._get_client()

            import time
            start_time = time.time()

            count = await client.delete(*keys)

            duration = time.time() - start_time
            cache_operation_duration_seconds.labels(operation="delete").observe(duration)

            return count

        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            client = await self._get_client()
            return await client.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error for {key}: {e}")
            return False

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment a counter.

        Useful for rate limiting, statistics, etc.
        """
        try:
            client = await self._get_client()
            return await client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error for {key}: {e}")
            return 0

    async def expire(self, key: str, ttl: Union[int, timedelta]) -> bool:
        """Set expiration on existing key"""
        try:
            client = await self._get_client()

            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())

            return await client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Cache expire error for {key}: {e}")
            return False

    async def get_ttl(self, key: str) -> int:
        """
        Get remaining TTL in seconds.

        Returns:
            -2 if key doesn't exist
            -1 if key exists but has no expiration
            >0 remaining seconds
        """
        try:
            client = await self._get_client()
            return await client.ttl(key)
        except Exception as e:
            logger.error(f"Cache TTL error for {key}: {e}")
            return -2

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern.

        Args:
            pattern: Redis pattern (e.g., "vuln:*", "user:123:*")

        Returns:
            Number of keys deleted

        Warning: Use sparingly in production as SCAN can be slow.
        """
        try:
            client = await self._get_client()

            # Use SCAN to avoid blocking
            keys_to_delete = []
            async for key in client.scan_iter(match=pattern):
                keys_to_delete.append(key)

            if keys_to_delete:
                return await client.delete(*keys_to_delete)

            return 0

        except Exception as e:
            logger.error(f"Cache invalidate pattern error for {pattern}: {e}")
            return 0


# Global cache manager instance
cache_manager = CacheManager()


class CacheStrategies:
    """Common caching patterns and strategies"""

    @staticmethod
    def cache_aside_pattern(
        cache_key: str,
        fetch_function: Callable,
        ttl: int = 300
    ):
        """
        Cache-Aside (Lazy Loading) pattern.

        1. Try to get from cache
        2. If miss, fetch from source
        3. Store in cache
        4. Return value

        This is implemented by the @cache decorator.
        Use CacheManager for manual control.
        """
        pass

    @staticmethod
    async def write_through(
        cache_key: str,
        value: Any,
        persist_function: Callable,
        ttl: int = 300
    ) -> bool:
        """
        Write-Through pattern.

        1. Write to database
        2. Write to cache
        3. Return success

        Ensures cache is always up-to-date.
        """
        try:
            # Write to persistent storage first
            await persist_function(value)

            # Then update cache
            await cache_manager.set(cache_key, value, ttl=ttl)

            return True
        except Exception as e:
            logger.error(f"Write-through error: {e}")
            return False

    @staticmethod
    async def invalidate_on_write(
        cache_keys: List[str],
        write_function: Callable,
        *args,
        **kwargs
    ):
        """
        Invalidate cached data when writing.

        1. Perform write operation
        2. Invalidate related cache keys

        Simpler than write-through but may have brief inconsistency.
        """
        try:
            # Perform write
            result = await write_function(*args, **kwargs)

            # Invalidate cache
            await cache_manager.delete(*cache_keys)

            return result
        except Exception as e:
            logger.error(f"Invalidate-on-write error: {e}")
            raise

    @staticmethod
    def cache_key_for_vulnerability(vuln_id: int) -> str:
        """Generate cache key for vulnerability"""
        return f"vuln:{vuln_id}"

    @staticmethod
    def cache_key_for_asset(asset_id: str) -> str:
        """Generate cache key for asset"""
        return f"asset:{asset_id}"

    @staticmethod
    def cache_key_for_patch(patch_id: int) -> str:
        """Generate cache key for patch"""
        return f"patch:{patch_id}"

    @staticmethod
    def cache_key_for_stats(stat_type: str, timeframe: str = "24h") -> str:
        """Generate cache key for statistics"""
        return f"stats:{stat_type}:{timeframe}"

    @staticmethod
    def cache_key_for_cve_details(cve_id: str) -> str:
        """Generate cache key for CVE details from NVD"""
        return f"cve:{cve_id}"


# Convenience functions
async def get_cached(key: str, default: Any = None) -> Any:
    """Quick function to get from cache"""
    return await cache_manager.get(key, default)


async def set_cached(key: str, value: Any, ttl: Union[int, timedelta, None] = None) -> bool:
    """Quick function to set in cache"""
    return await cache_manager.set(key, value, ttl)


async def delete_cached(*keys: str) -> int:
    """Quick function to delete from cache"""
    return await cache_manager.delete(*keys)


async def invalidate_cached(pattern: str) -> int:
    """Quick function to invalidate by pattern"""
    return await cache_manager.invalidate_pattern(pattern)
