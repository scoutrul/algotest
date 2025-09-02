"""
Data fetcher service for retrieving historical market data from Binance.
"""
import ccxt
import pandas as pd
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from ..config import settings
from ..models.backtest import CandleData
from .cache import data_cache

logger = logging.getLogger(__name__)

class DataFetcher:
    """Service for fetching historical market data from Binance."""
    
    def __init__(self):
        """Initialize the data fetcher with Binance exchange."""
        self.exchange = ccxt.binance({
            'apiKey': '',  # Public data doesn't require API key
            'secret': '',
            'sandbox': False,
            'enableRateLimit': True,
            'rateLimit': 1000,  # 1 second between requests
        })
        
        # Cache for frequently requested data
        self._cache: Dict[str, List[CandleData]] = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
    
    async def fetch_candles(
        self, 
        symbol: str, 
        interval: str, 
        limit: Optional[int] = None
    ) -> List[CandleData]:
        """
        Fetch historical OHLCV data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            interval: Time interval (e.g., '15m', '1h')
            limit: Maximum number of candles to fetch
            
        Returns:
            List of CandleData objects
            
        Raises:
            ValueError: If symbol or interval is invalid
            Exception: If data fetching fails
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
                logger.info(f"Returning cached data from Redis for {symbol} {interval}")
                return [CandleData(**candle) for candle in cached_data]
            
            # Check local cache as fallback
            cache_key = f"{symbol}_{interval}_{limit}"
            if cache_key in self._cache:
                logger.info(f"Returning cached data from local cache for {cache_key}")
                return self._cache[cache_key]
            
            # Fetch data from exchange
            logger.info(f"Fetching {limit} candles for {symbol} {interval}")
            
            # Convert interval to ccxt format
            ccxt_interval = self._convert_interval(interval)
            
            # Fetch OHLCV data
            ohlcv = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.exchange.fetch_ohlcv(symbol, ccxt_interval, limit=limit)
            )
            
            # Convert to CandleData objects
            candles = [CandleData.from_ccxt(candle) for candle in ohlcv]
            
            # Cache the result in both Redis and local cache
            await data_cache.set_candles(symbol, interval, limit, [candle.model_dump() for candle in candles])
            self._cache[cache_key] = candles
            
            logger.info(f"Successfully fetched {len(candles)} candles for {symbol}")
            return candles
            
        except ccxt.NetworkError as e:
            logger.error(f"Network error fetching data for {symbol}: {e}")
            raise Exception(f"Network error: {e}")
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching data for {symbol}: {e}")
            raise Exception(f"Exchange error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching data for {symbol}: {e}")
            raise Exception(f"Data fetching failed: {e}")
    
    async def fetch_candles_with_timeframe(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[CandleData]:
        """
        Fetch historical data within a specific timeframe.
        
        Args:
            symbol: Trading pair symbol
            interval: Time interval
            start_time: Start time for data
            end_time: End time for data
            limit: Maximum number of candles
            
        Returns:
            List of CandleData objects
        """
        try:
            # If no start_time provided, calculate based on limit
            if start_time is None and limit is not None:
                interval_minutes = self._get_interval_minutes(interval)
                start_time = datetime.now() - timedelta(minutes=interval_minutes * limit)
            
            # Fetch data
            candles = await self.fetch_candles(symbol, interval, limit)
            
            # Filter by timeframe if specified
            if start_time or end_time:
                filtered_candles = []
                for candle in candles:
                    if start_time and candle.timestamp < start_time:
                        continue
                    if end_time and candle.timestamp > end_time:
                        continue
                    filtered_candles.append(candle)
                return filtered_candles
            
            return candles
            
        except Exception as e:
            logger.error(f"Error fetching data with timeframe: {e}")
            raise
    
    def get_available_symbols(self) -> List[str]:
        """Get list of available trading symbols."""
        return settings.SUPPORTED_SYMBOLS.copy()
    
    def get_available_intervals(self) -> List[str]:
        """Get list of available time intervals."""
        return settings.SUPPORTED_INTERVALS.copy()
    
    def validate_symbol(self, symbol: str) -> bool:
        """Validate if symbol is supported."""
        try:
            self._validate_symbol(symbol)
            return True
        except ValueError:
            return False
    
    def validate_interval(self, interval: str) -> bool:
        """Validate if interval is supported."""
        try:
            self._validate_interval(interval)
            return True
        except ValueError:
            return False
    
    def _validate_symbol(self, symbol: str) -> None:
        """Validate trading symbol."""
        if not symbol:
            raise ValueError("Symbol cannot be empty")
        
        if '/' not in symbol:
            raise ValueError("Symbol must contain '/' (e.g., BTC/USDT)")
        
        if symbol.upper() not in [s.upper() for s in settings.SUPPORTED_SYMBOLS]:
            raise ValueError(f"Unsupported symbol: {symbol}. Supported: {settings.SUPPORTED_SYMBOLS}")
    
    def _validate_interval(self, interval: str) -> None:
        """Validate time interval."""
        if not interval:
            raise ValueError("Interval cannot be empty")
        
        if interval not in settings.SUPPORTED_INTERVALS:
            raise ValueError(f"Unsupported interval: {interval}. Supported: {settings.SUPPORTED_INTERVALS}")
    
    def _convert_interval(self, interval: str) -> str:
        """Convert interval to ccxt format."""
        # ccxt uses different format for some intervals
        interval_map = {
            '1m': '1m',
            '5m': '5m', 
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '2h': '2h',
            '4h': '4h',
            '6h': '6h',
            '8h': '8h',
            '12h': '12h',
            '1d': '1d'
        }
        return interval_map.get(interval, interval)
    
    def _get_interval_minutes(self, interval: str) -> int:
        """Get interval duration in minutes."""
        interval_minutes = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '2h': 120,
            '4h': 240,
            '6h': 360,
            '8h': 480,
            '12h': 720,
            '1d': 1440
        }
        return interval_minutes.get(interval, 60)
    
    def clear_cache(self) -> None:
        """Clear the data cache."""
        self._cache.clear()
        logger.info("Data cache cleared")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information."""
        return {
            "cache_size": len(self._cache),
            "cache_keys": list(self._cache.keys()),
            "cache_ttl": self._cache_ttl
        }
