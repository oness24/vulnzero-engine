"""
Redis Client Helper
===================

Provides async Redis client for caching and session management.
"""

import logging
from typing import Optional
import redis.asyncio as aioredis

from shared.config.settings import settings

logger = logging.getLogger(__name__)

# Global Redis client instance
_redis_client: Optional[aioredis.Redis] = None


async def get_redis_client() -> aioredis.Redis:
    """
    Get or create Redis client instance.

    Returns:
        Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        try:
            # Parse Redis URL
            redis_url = settings.redis_url

            # Create Redis client
            _redis_client = await aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10,
            )

            logger.info("Redis client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            raise

    return _redis_client


async def close_redis_client():
    """Close Redis client connection."""
    global _redis_client

    if _redis_client:
        try:
            await _redis_client.close()
            logger.info("Redis client closed")
        except Exception as e:
            logger.error(f"Error closing Redis client: {e}")
        finally:
            _redis_client = None
