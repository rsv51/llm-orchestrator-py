"""
Redis cache management for configuration and health status caching.
"""
from typing import Optional, Any
import json
from redis import asyncio as aioredis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class RedisCache:
    """Redis cache manager with connection pooling."""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.enabled = settings.redis_enabled
        
    async def connect(self) -> None:
        """Establish Redis connection."""
        if not self.enabled:
            logger.info("Redis cache is disabled")
            return
            
        try:
            self.redis = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10
            )
            # Test connection
            await self.redis.ping()
            logger.info("Redis cache connected successfully", url=settings.redis_url)
        except RedisError as e:
            logger.error("Failed to connect to Redis", error=str(e))
            self.enabled = False
            self.redis = None
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            logger.info("Redis cache disconnected")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not self.enabled or not self.redis:
            return None
            
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except RedisError as e:
            logger.warning("Redis get failed", key=key, error=str(e))
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default from settings)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.redis:
            return False
            
        try:
            ttl = ttl or settings.redis_cache_ttl
            await self.redis.setex(
                key,
                ttl,
                json.dumps(value)
            )
            return True
        except RedisError as e:
            logger.warning("Redis set failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.redis:
            return False
            
        try:
            await self.redis.delete(key)
            return True
        except RedisError as e:
            logger.warning("Redis delete failed", key=key, error=str(e))
            return False
    
    async def clear(self, pattern: str = "*") -> bool:
        """
        Clear cache keys matching pattern.
        
        Args:
            pattern: Key pattern (default: all keys)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.redis:
            return False
            
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
            logger.info("Cache cleared", pattern=pattern, count=len(keys))
            return True
        except RedisError as e:
            logger.warning("Redis clear failed", pattern=pattern, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if exists, False otherwise
        """
        if not self.enabled or not self.redis:
            return False
            
        try:
            return await self.redis.exists(key) > 0
        except RedisError as e:
            logger.warning("Redis exists check failed", key=key, error=str(e))
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment value of key by amount.
        
        Args:
            key: Cache key
            amount: Amount to increment by (default: 1)
            
        Returns:
            New value after increment, or None if failed
        """
        if not self.enabled or not self.redis:
            return None
            
        try:
            return await self.redis.incrby(key, amount)
        except RedisError as e:
            logger.warning("Redis increment failed", key=key, error=str(e))
            return None


# Global cache instance
cache = RedisCache()


# Cache key generators
def provider_cache_key(model_name: str) -> str:
    """Generate cache key for provider configuration."""
    return f"provider:model:{model_name}"


def health_cache_key(provider_id: int) -> str:
    """Generate cache key for provider health status."""
    return f"health:provider:{provider_id}"


def model_list_cache_key() -> str:
    """Generate cache key for model list."""
    return "models:list"