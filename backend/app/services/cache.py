"""
Caching service for BackTest Trading Bot.

Provides Redis-based caching for API responses and data fetching.
"""

import json
import asyncio
import hashlib
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import logging

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from ..config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service."""
    
    def __init__(self):
        """Initialize cache service."""
        self.redis_client = None
        self.enabled = False
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis connection."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, caching disabled")
            return
        
        try:
            self.redis_client = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0),
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            self.enabled = True
            logger.info("Redis cache service initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis: {e}, caching disabled")
            self.enabled = False
    
    async def _test_connection(self) -> bool:
        """Test Redis connection."""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            await self.redis_client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis connection test failed: {e}")
            self.enabled = False
            return False
    
    def _generate_key(self, prefix: str, *args) -> str:
        """Generate cache key from arguments."""
        key_data = f"{prefix}:{':'.join(str(arg) for arg in args)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not await self._test_connection():
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL."""
        if not await self._test_connection():
            return False
        
        try:
            serialized = json.dumps(value, default=str)
            await self.redis_client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not await self._test_connection():
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        if not await self._test_connection():
            return 0
        
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear pattern error: {e}")
            return 0
    
    async def get_or_set(self, key: str, factory_func, ttl: int = 300, *args, **kwargs) -> Any:
        """Get from cache or set using factory function."""
        # Try to get from cache first
        cached_value = await self.get(key)
        if cached_value is not None:
            logger.debug(f"Cache hit for key: {key}")
            return cached_value
        
        # Generate value using factory function
        logger.debug(f"Cache miss for key: {key}, generating value")
        try:
            if asyncio.iscoroutinefunction(factory_func):
                value = await factory_func(*args, **kwargs)
            else:
                value = factory_func(*args, **kwargs)
            
            # Store in cache
            await self.set(key, value, ttl)
            return value
        except Exception as e:
            logger.error(f"Factory function error for key {key}: {e}")
            raise


class DataCache:
    """Specialized cache for market data."""
    
    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
        self.data_ttl = 300  # 5 minutes for market data
        self.symbols_ttl = 3600  # 1 hour for symbols list
        self.intervals_ttl = 3600  # 1 hour for intervals list
    
    async def get_candles(self, symbol: str, interval: str, limit: int) -> Optional[List[Dict]]:
        """Get cached candles data."""
        key = self.cache._generate_key("candles", symbol, interval, limit)
        return await self.cache.get(key)
    
    async def set_candles(self, symbol: str, interval: str, limit: int, data: List[Dict]) -> bool:
        """Cache candles data."""
        key = self.cache._generate_key("candles", symbol, interval, limit)
        return await self.cache.set(key, data, self.data_ttl)
    
    async def get_symbols(self) -> Optional[List[str]]:
        """Get cached symbols list."""
        return await self.cache.get("symbols")
    
    async def set_symbols(self, symbols: List[str]) -> bool:
        """Cache symbols list."""
        return await self.cache.set("symbols", symbols, self.symbols_ttl)
    
    async def get_intervals(self) -> Optional[List[str]]:
        """Get cached intervals list."""
        return await self.cache.get("intervals")
    
    async def set_intervals(self, intervals: List[str]) -> bool:
        """Cache intervals list."""
        return await self.cache.set("intervals", intervals, self.intervals_ttl)
    
    async def clear_data_cache(self) -> int:
        """Clear all data cache."""
        return await self.cache.clear_pattern("candles:*")


class APICache:
    """Specialized cache for API responses."""
    
    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
        self.api_ttl = 60  # 1 minute for API responses
        self.backtest_ttl = 300  # 5 minutes for backtest results
    
    async def get_backtest_result(self, params: Dict[str, Any]) -> Optional[Dict]:
        """Get cached backtest result."""
        key = self.cache._generate_key("backtest", *sorted(params.items()))
        return await self.cache.get(key)
    
    async def set_backtest_result(self, params: Dict[str, Any], result: Dict) -> bool:
        """Cache backtest result."""
        key = self.cache._generate_key("backtest", *sorted(params.items()))
        return await self.cache.set(key, result, self.backtest_ttl)
    
    async def get_strategy_info(self) -> Optional[Dict]:
        """Get cached strategy info."""
        return await self.cache.get("strategy_info")
    
    async def set_strategy_info(self, info: Dict) -> bool:
        """Cache strategy info."""
        return await self.cache.set("strategy_info", info, 3600)  # 1 hour
    
    async def clear_api_cache(self) -> int:
        """Clear all API cache."""
        return await self.cache.clear_pattern("backtest:*")


# Global cache instances
cache_service = CacheService()
data_cache = DataCache(cache_service)
api_cache = APICache(cache_service)


async def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    if not cache_service.enabled:
        return {"enabled": False, "message": "Cache disabled"}
    
    try:
        info = await cache_service.redis_client.info()
        return {
            "enabled": True,
            "connected": True,
            "memory_used": info.get("used_memory_human", "unknown"),
            "keys_count": info.get("db0", {}).get("keys", 0),
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "hit_rate": round(
                info.get("keyspace_hits", 0) / 
                max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1) * 100, 2
            )
        }
    except Exception as e:
        return {
            "enabled": True,
            "connected": False,
            "error": str(e)
        }
