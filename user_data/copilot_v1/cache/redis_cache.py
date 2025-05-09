"""
Redis Cache for Trading-Copilot
Layer 7 in the architecture
"""

import logging
import json
import asyncio
from typing import Dict, List, Any, Optional, Union
import os
import redis.asyncio as redis
from datetime import timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisCache:
    """
    Redis cache for storing and retrieving data
    """
    
    def __init__(
        self, 
        host: str = "localhost", 
        port: int = 6379, 
        db: int = 0, 
        password: Optional[str] = None,
        prefix: str = "trading_copilot:"
    ):
        """
        Initialize the Redis cache connection
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.prefix = prefix
        self._redis = None
        self._connection_lock = asyncio.Lock()
    
    async def _get_redis(self) -> redis.Redis:
        """
        Get or create Redis connection
        """
        async with self._connection_lock:
            if self._redis is None:
                try:
                    self._redis = redis.Redis(
                        host=self.host,
                        port=self.port,
                        db=self.db,
                        password=self.password,
                        decode_responses=True,
                        socket_timeout=5,
                        socket_connect_timeout=5
                    )
                    # Test connection
                    await self._redis.ping()
                except Exception as e:
                    logger.error(f"Error connecting to Redis: {str(e)}", exc_info=True)
                    # Use a dummy in-memory cache if Redis is not available
                    self._redis = None
                    raise
            
            return self._redis
    
    def _get_key(self, key: str) -> str:
        """
        Get the full Redis key with prefix
        """
        return f"{self.prefix}{key}"
    
    async def get(self, key: str) -> Optional[str]:
        """
        Get a value from the cache
        """
        try:
            redis_client = await self._get_redis()
            result = await redis_client.get(self._get_key(key))
            return result
        except Exception as e:
            logger.warning(f"Error getting value from Redis cache: {str(e)}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: str, 
        expire: Optional[int] = None
    ) -> bool:
        """
        Set a value in the cache with optional expiration (in seconds)
        """
        try:
            redis_client = await self._get_redis()
            result = await redis_client.set(self._get_key(key), value, ex=expire)
            return result
        except Exception as e:
            logger.warning(f"Error setting value in Redis cache: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete a value from the cache
        """
        try:
            redis_client = await self._get_redis()
            result = await redis_client.delete(self._get_key(key))
            return result > 0
        except Exception as e:
            logger.warning(f"Error deleting value from Redis cache: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache
        """
        try:
            redis_client = await self._get_redis()
            result = await redis_client.exists(self._get_key(key))
            return result > 0
        except Exception as e:
            logger.warning(f"Error checking key existence in Redis cache: {str(e)}")
            return False
    
    async def keys(self, pattern: str) -> List[str]:
        """
        Get keys matching a pattern
        """
        try:
            redis_client = await self._get_redis()
            result = await redis_client.keys(self._get_key(pattern))
            return [key[len(self.prefix):] for key in result]  # Remove prefix
        except Exception as e:
            logger.warning(f"Error getting keys from Redis cache: {str(e)}")
            return []
    
    async def flush(self) -> bool:
        """
        Flush all keys with the prefix
        """
        try:
            redis_client = await self._get_redis()
            keys = await redis_client.keys(f"{self.prefix}*")
            if keys:
                result = await redis_client.delete(*keys)
                return result > 0
            return True
        except Exception as e:
            logger.warning(f"Error flushing Redis cache: {str(e)}")
            return False
    
    async def store_json(
        self, 
        key: str, 
        data: Union[Dict, List], 
        expire: Optional[int] = None
    ) -> bool:
        """
        Store JSON data in the cache
        """
        try:
            json_data = json.dumps(data)
            return await self.set(key, json_data, expire)
        except Exception as e:
            logger.warning(f"Error storing JSON in Redis cache: {str(e)}")
            return False
    
    async def get_json(self, key: str) -> Optional[Union[Dict, List]]:
        """
        Get JSON data from the cache
        """
        try:
            data = await self.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Error getting JSON from Redis cache: {str(e)}")
            return None
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a value in the cache
        """
        try:
            redis_client = await self._get_redis()
            result = await redis_client.incrby(self._get_key(key), amount)
            return result
        except Exception as e:
            logger.warning(f"Error incrementing value in Redis cache: {str(e)}")
            return None
    
    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set an expiration on a key
        """
        try:
            redis_client = await self._get_redis()
            result = await redis_client.expire(self._get_key(key), seconds)
            return result
        except Exception as e:
            logger.warning(f"Error setting expiration in Redis cache: {str(e)}")
            return False
    
    async def close(self) -> None:
        """
        Close the Redis connection
        """
        async with self._connection_lock:
            if self._redis:
                await self._redis.close()
                self._redis = None

# Memory-based cache fallback when Redis is not available
class MemoryCache:
    """
    Simple in-memory cache implementation as fallback
    """
    
    def __init__(self):
        self._cache = {}
        self._expiry = {}
    
    async def get(self, key: str) -> Optional[str]:
        """
        Get a value from the cache
        """
        self._check_expiry(key)
        return self._cache.get(key)
    
    async def set(
        self, 
        key: str, 
        value: str, 
        expire: Optional[int] = None
    ) -> bool:
        """
        Set a value in the cache with optional expiration (in seconds)
        """
        self._cache[key] = value
        if expire:
            self._expiry[key] = asyncio.get_event_loop().time() + expire
        return True
    
    async def delete(self, key: str) -> bool:
        """
        Delete a value from the cache
        """
        if key in self._cache:
            del self._cache[key]
            if key in self._expiry:
                del self._expiry[key]
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache
        """
        self._check_expiry(key)
        return key in self._cache
    
    async def keys(self, pattern: str) -> List[str]:
        """
        Get keys matching a pattern (simple implementation)
        """
        self._check_all_expiry()
        pattern = pattern.replace("*", "")
        return [k for k in self._cache.keys() if pattern in k]
    
    async def flush(self) -> bool:
        """
        Flush all keys
        """
        self._cache.clear()
        self._expiry.clear()
        return True
    
    async def store_json(
        self, 
        key: str, 
        data: Union[Dict, List], 
        expire: Optional[int] = None
    ) -> bool:
        """
        Store JSON data in the cache
        """
        json_data = json.dumps(data)
        await self.set(key, json_data, expire)
        return True
    
    async def get_json(self, key: str) -> Optional[Union[Dict, List]]:
        """
        Get JSON data from the cache
        """
        data = await self.get(key)
        if data:
            return json.loads(data)
        return None
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a value in the cache
        """
        self._check_expiry(key)
        if key in self._cache:
            try:
                self._cache[key] = str(int(self._cache[key]) + amount)
                return int(self._cache[key])
            except ValueError:
                return None
        else:
            self._cache[key] = str(amount)
            return amount
    
    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set an expiration on a key
        """
        if key in self._cache:
            self._expiry[key] = asyncio.get_event_loop().time() + seconds
            return True
        return False
    
    async def close(self) -> None:
        """
        Close the cache (no-op for memory cache)
        """
        pass
    
    def _check_expiry(self, key: str) -> None:
        """
        Check and remove expired key
        """
        if key in self._expiry:
            if asyncio.get_event_loop().time() > self._expiry[key]:
                del self._cache[key]
                del self._expiry[key]
    
    def _check_all_expiry(self) -> None:
        """
        Check all keys for expiry
        """
        now = asyncio.get_event_loop().time()
        expired_keys = [k for k, v in self._expiry.items() if now > v]
        for key in expired_keys:
            if key in self._cache:
                del self._cache[key]
            del self._expiry[key]

# Factory function to get appropriate cache based on environment
def get_cache() -> Union[RedisCache, MemoryCache]:
    """
    Get the appropriate cache implementation based on environment
    """
    redis_host = os.getenv("REDIS_HOST", "")
    
    if redis_host:
        try:
            return RedisCache(
                host=redis_host,
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_DB", "0")),
                password=os.getenv("REDIS_PASSWORD", ""),
                prefix=os.getenv("REDIS_PREFIX", "trading_copilot:")
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Redis cache: {str(e)}. Falling back to memory cache.")
    
    logger.info("Using in-memory cache")
    return MemoryCache()
