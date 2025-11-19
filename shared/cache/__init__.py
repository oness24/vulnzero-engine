"""Cache utilities for VulnZero"""

from shared.cache.redis_client import get_redis_client, close_redis_client
from shared.cache.caching import (
    cache,
    CacheManager,
    CacheStrategies,
    cache_manager,
    get_cached,
    set_cached,
    delete_cached,
    invalidate_cached,
    generate_cache_key,
)

__all__ = [
    # Redis client
    "get_redis_client",
    "close_redis_client",
    # Caching
    "cache",
    "CacheManager",
    "CacheStrategies",
    "cache_manager",
    "get_cached",
    "set_cached",
    "delete_cached",
    "invalidate_cached",
    "generate_cache_key",
]
