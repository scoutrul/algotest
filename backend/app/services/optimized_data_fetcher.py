"""
Optimized Data Fetcher with Connection Pooling and Advanced Caching

This module provides an optimized version of the data fetcher with:
- Connection pooling for ccxt
- Advanced caching strategies
- Response compression
- Memory optimization
"""

import ccxt
import pandas as pd
import asyncio
import aiohttp
import gzip
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor
import weakref

from ..config import settings
from ..models.backtest import CandleData
from .cache import data_cache

logger = logging.getLogger(__name__)


class OptimizedDataFetcher:
    """Optimized data fetcher with connection pooling and advanced caching."""
    
    def __init__(self, max_connections: int = 10):
        """Initialize optimized data fetcher."""
        self.max_connections = max_connections
        self._session = None
        self._executor = ThreadPoolExecutor(max_workers=max_connections)
        
        # Initialize ccxt with connection pooling
        self.exchange = ccxt.binance({
            'apiKey': '',  # Public data doesn't require API key
            'secret': '',
            'sandbox': False,
            'enableRateLimit': True,
            'rateLimit': 100,  # Reduced rate limit for better performance
            'timeout': 30000,  # 30 second timeout
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True,
            }
        })
        
        # Local cache with weak references for memory efficiency
        self._cache: Dict[str, weakref.WeakValueDictionary] = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
        
        logger.info(f"Optimized DataFetcher initialized with {max_connections} connections")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._initialize_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()
    
    async def _initialize_session(self):
        """Initialize aiohttp session for connection pooling."""
        if self._session is None:
            connector = aiohttp.TCPConnector(
                limit=self.max_connections,
                limit_per_host=self.max_connections,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'Accept-Encoding': 'gzip, deflate',
                    'User-Agent': 'BackTest-Trading-Bot/1.0'
                }
            )
    
    async def _close_session(self):
        """Close aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
    
    def _validate_symbol(self, symbol: str):
        """Validate trading symbol."""
        if not symbol or '/' not in symbol:
            raise ValueError(f"Invalid symbol format: {symbol}")
    
    def _validate_interval(self, interval: str):
        """Validate time interval."""
        valid_intervals = ['1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d']
        if interval not in valid_intervals:
            raise ValueError(f"Invalid interval: {interval}. Must be one of: {valid_intervals}")
    
    def _convert_interval(self, interval: str) -> str:
        """Convert interval to ccxt format."""
        return interval
    
    def _get_interval_minutes(self, interval: str) -> int:
        """Get interval in minutes."""
        interval_map = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '4h': 240, '6h': 360,
            '8h': 480, '12h': 720, '1d': 1440
        }
        return interval_map.get(interval, 15)
    
    def _compress_data(self, data: List[Dict]) -> bytes:
        """Compress data using gzip."""
        json_data = json.dumps(data, default=str)
        return gzip.compress(json_data.encode('utf-8'))
    
    def _decompress_data(self, compressed_data: bytes) -> List[Dict]:
        """Decompress data using gzip."""
        json_data = gzip.decompress(compressed_data).decode('utf-8')
        return json.loads(json_data)
    
    async def fetch_candles(
        self, 
        symbol: str, 
        interval: str, 
        limit: Optional[int] = None
    ) -> List[CandleData]:
        """
        Fetch historical OHLCV data with optimization.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            interval: Time interval (e.g., '15m', '1h')
            limit: Maximum number of candles to fetch
            
        Returns:
            List of CandleData objects
        """
        try:
            # Validate inputs
            self._validate_symbol(symbol)
            self._validate_interval(interval)
            
            # Set default limit
            if limit is None:
                limit = settings.DEFAULT_CANDLES_LIMIT
            limit = min(limit, settings.MAX_CANDLES_LIMIT)
            
            # Check Redis cache first
            cached_data = await data_cache.get_candles(symbol, interval, limit)
            if cached_data:
                logger.info(f"Cache hit: Returning cached data for {symbol} {interval}")
                return [CandleData(**candle) for candle in cached_data]
            
            # Check local cache as fallback
            cache_key = f"{symbol}_{interval}_{limit}"
            if cache_key in self._cache:
                cached_candles = self._cache[cache_key]
                if cached_candles:
                    logger.info(f"Local cache hit: Returning cached data for {cache_key}")
                    return list(cached_candles.values())
            
            # Fetch data from exchange with connection pooling
            logger.info(f"Fetching {limit} candles for {symbol} {interval}")
            
            # Use thread pool for ccxt operations
            loop = asyncio.get_event_loop()
            ohlcv = await loop.run_in_executor(
                self._executor,
                self._fetch_ohlcv_sync,
                symbol,
                interval,
                limit
            )
            
            # Convert to CandleData objects efficiently
            candles = []
            for candle_data in ohlcv:
                try:
                    candle = CandleData.from_ccxt(candle_data)
                    candles.append(candle)
                except Exception as e:
                    logger.warning(f"Failed to convert candle data: {e}")
                    continue
            
            # Cache the result in both Redis and local cache
            await data_cache.set_candles(
                symbol, interval, limit, 
                [candle.dict() for candle in candles]
            )
            
            # Store in local cache with weak references
            self._cache[cache_key] = weakref.WeakValueDictionary({
                id(candle): candle for candle in candles
            })
            
            logger.info(f"Successfully fetched {len(candles)} candles for {symbol}")
            return candles
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            raise Exception(f"Data fetching failed: {e}")
    
    def _fetch_ohlcv_sync(self, symbol: str, interval: str, limit: int) -> List[List]:
        """Synchronous OHLCV fetching for thread pool."""
        try:
            ccxt_interval = self._convert_interval(interval)
            return self.exchange.fetch_ohlcv(symbol, ccxt_interval, limit=limit)
        except Exception as e:
            logger.error(f"Sync fetch error for {symbol}: {e}")
            raise
    
    async def fetch_multiple_symbols(
        self, 
        symbols: List[str], 
        interval: str, 
        limit: Optional[int] = None
    ) -> Dict[str, List[CandleData]]:
        """
        Fetch data for multiple symbols concurrently.
        
        Args:
            symbols: List of trading pair symbols
            interval: Time interval
            limit: Maximum number of candles per symbol
            
        Returns:
            Dictionary mapping symbols to their candle data
        """
        tasks = []
        for symbol in symbols:
            task = self.fetch_candles(symbol, interval, limit)
            tasks.append((symbol, task))
        
        results = {}
        completed_tasks = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        for (symbol, _), result in zip(tasks, completed_tasks):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch data for {symbol}: {result}")
                results[symbol] = []
            else:
                results[symbol] = result
        
        return results
    
    async def prefetch_popular_data(self):
        """Prefetch data for popular trading pairs."""
        popular_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT']
        popular_intervals = ['15m', '1h', '4h']
        
        logger.info("Starting prefetch of popular trading data")
        
        tasks = []
        for symbol in popular_symbols:
            for interval in popular_intervals:
                task = self.fetch_candles(symbol, interval, 1000)
                tasks.append(task)
        
        # Execute prefetch tasks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("Completed prefetch of popular trading data")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        local_cache_size = sum(len(cache) for cache in self._cache.values())
        
        return {
            'local_cache_entries': local_cache_size,
            'cache_keys': list(self._cache.keys()),
            'max_connections': self.max_connections,
            'executor_threads': self._executor._max_workers
        }
    
    async def clear_cache(self):
        """Clear all caches."""
        self._cache.clear()
        await data_cache.clear_data_cache()
        logger.info("All caches cleared")
    
    def __del__(self):
        """Cleanup on destruction."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
