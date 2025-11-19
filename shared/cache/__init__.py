"""Cache utilities for VulnZero"""

from shared.cache.redis_client import get_redis_client, close_redis_client

__all__ = ["get_redis_client", "close_redis_client"]
