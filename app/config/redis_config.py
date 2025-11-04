import redis.asyncio as aioredis
from typing import Optional
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)


class RedisConfig:
    """Redis configuration and connection manager."""
    
    def __init__(self):
        """Initialize Redis configuration."""
        self.redis: Optional[aioredis.Redis] = None
        self._initialized = False
    
    async def connect(self):
        """Create Redis connection pool."""
        if self._initialized:
            logger.warning("Redis connection already initialized")
            return
        
        try:
            self.redis = await aioredis.from_url(
                settings.redis_url,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=settings.REDIS_DECODE_RESPONSES,
                encoding="utf-8",
            )
            self._initialized = True
            logger.info("Redis connection created successfully")
        except Exception as e:
            logger.error(f"Failed to create Redis connection: {e}")
            raise
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            self._initialized = False
            logger.info("Redis connection closed")
    
    def get_client(self) -> aioredis.Redis:
        """Get Redis client."""
        if not self.redis:
            raise RuntimeError("Redis not initialized")
        return self.redis
    
    async def health_check(self) -> bool:
        """Check if Redis is healthy."""
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


# Global Redis instance
redis_config = RedisConfig()
