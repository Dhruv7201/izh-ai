"""Redis cache helper for caching operations."""
import json
import logging
from typing import Any, Optional, Union
from functools import wraps
import hashlib

from app.config.redis_config import redis_config
from app.config.settings import settings

logger = logging.getLogger(__name__)


class CacheHelper:
    """Helper class for Redis caching operations."""
    
    def __init__(self):
        """Initialize cache helper."""
        self.redis = redis_config
        self.default_ttl = settings.CACHE_TTL
        self.enabled = settings.CACHE_ENABLED
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if not self.enabled:
            return None
        
        try:
            client = self.redis.get_client()
            value = await client.get(key)
            if value:
                logger.debug(f"Cache hit: {key}")
                return json.loads(value) if value else None
            logger.debug(f"Cache miss: {key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default from settings)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            client = self.redis.get_client()
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value)
            await client.setex(key, ttl, serialized)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            client = self.redis.get_client()
            await client.delete(key)
            logger.debug(f"Cache delete: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Key pattern (e.g., "user:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0
        
        try:
            client = self.redis.get_client()
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                deleted = await client.delete(*keys)
                logger.debug(f"Cache delete pattern {pattern}: {deleted} keys")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if exists, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            client = self.redis.get_client()
            exists = await client.exists(key)
            return bool(exists)
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a counter in cache.
        
        Args:
            key: Cache key
            amount: Amount to increment
            
        Returns:
            New value or None
        """
        if not self.enabled:
            return None
        
        try:
            client = self.redis.get_client()
            value = await client.incrby(key, amount)
            return value
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return None
    
    async def set_with_lock(
        self, 
        key: str, 
        value: Any, 
        lock_timeout: int = 10,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set a value with distributed lock.
        
        Args:
            key: Cache key
            value: Value to cache
            lock_timeout: Lock timeout in seconds
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        lock_key = f"lock:{key}"
        client = self.redis.get_client()
        
        try:
            # Acquire lock
            lock_acquired = await client.set(
                lock_key, 
                "1", 
                nx=True, 
                ex=lock_timeout
            )
            
            if not lock_acquired:
                logger.warning(f"Could not acquire lock for key {key}")
                return False
            
            # Set value
            result = await self.set(key, value, ttl)
            
            # Release lock
            await client.delete(lock_key)
            
            return result
        except Exception as e:
            logger.error(f"Cache set with lock error for key {key}: {e}")
            # Try to release lock
            try:
                await client.delete(lock_key)
            except:
                pass
            return False
    
    def cache_key(self, *args, **kwargs) -> str:
        """
        Generate a cache key from arguments.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Generated cache key
        """
        key_data = f"{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()


def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        
    Usage:
        @cached(ttl=300, key_prefix="user")
        async def get_user(user_id: int):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = CacheHelper()
            
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{cache.cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            await cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


# Global cache helper instance
cache_helper = CacheHelper()
