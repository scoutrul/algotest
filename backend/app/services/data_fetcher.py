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
from .database import db_service

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
            'rateLimit': 200,  # Reduced from 1000ms to 200ms for faster requests
            'options': {
                'adjustForTimeDifference': False,  # Skip time adjustment for faster responses
                'recvWindow': 10000,
            }
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
            
            # 1. Try to get data from database first
            db_candles = await db_service.get_candles(symbol, interval, limit)
            if db_candles and len(db_candles) > 0:
                logger.info(f"Returning {len(db_candles)} candles from database for {symbol} {interval}")
                return db_candles

            # 2. Check Redis cache as fallback
            cached_data = await data_cache.get_candles(symbol, interval, limit)
            if cached_data:
                logger.info(f"Returning cached data from Redis for {symbol} {interval}")
                candles = [CandleData(**candle) for candle in cached_data]
                # Save to database for future use
                await db_service.save_candles(symbol, interval, candles)
                return candles

            # 3. Check local cache as last resort
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

            # 5. Save to database for future requests
            saved_count = await db_service.save_candles(symbol, interval, candles)
            if saved_count > 0:
                logger.info(f"Saved {saved_count} candles to database for {symbol} {interval}")

            # 6. Cache the result in Redis and local cache
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
            # Validate inputs
            self._validate_symbol(symbol)
            self._validate_interval(interval)

            # Normalize inputs
            if start_time and start_time.tzinfo:
                start_time = start_time.replace(tzinfo=None)
            if end_time and end_time.tzinfo:
                end_time = end_time.replace(tzinfo=None)

            # Determine limit
            if limit is None:
                limit = settings.DEFAULT_CANDLES_LIMIT
            limit = min(limit, settings.MAX_CANDLES_LIMIT)

            # 1. Try to get data from database first
            db_candles = await db_service.get_candles(
                symbol, interval, limit,
                start_time=start_time, end_time=end_time
            )
            if db_candles and len(db_candles) > 0:
                logger.info(f"Returning {len(db_candles)} timeframe candles from database for {symbol} {interval}")
                return db_candles

            # 2. Fetch from exchange if not in database
            logger.info(f"Fetching timeframe data for {symbol} {interval} from exchange")
            candles = await self._fetch_timeframe_from_exchange(symbol, interval, start_time, end_time, limit)

            # 3. Save to database
            saved_count = await db_service.save_candles(symbol, interval, candles)
            if saved_count > 0:
                logger.info(f"Saved {saved_count} timeframe candles to database for {symbol} {interval}")

            return candles
            
        except Exception as e:
            logger.error(f"Error fetching data with timeframe: {e}")
            raise

    async def _fetch_timeframe_from_exchange(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        limit: int
    ) -> List[CandleData]:
        """Fetch timeframe data directly from exchange."""
        try:
            ccxt_interval = self._convert_interval(interval)

            since = None
            if start_time:
                since = int(start_time.timestamp() * 1000)
            elif end_time:
                # If only end_time provided, calculate since as end_time - limit * interval_duration
                # But go back much further to ensure we get historical data
                interval_seconds = self._get_interval_seconds(interval)
                since_timestamp = end_time.timestamp() - (limit * interval_seconds * 2)  # Go back 2x further
                since = int(since_timestamp * 1000)

            ohlcv = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.exchange.fetch_ohlcv(symbol, ccxt_interval, since=since, limit=limit)
            )

            # Convert to CandleData objects
            candles = [CandleData.from_ccxt(candle) for candle in ohlcv]

            # Filter candles by end_time if provided (safety check)
            if end_time:
                candles = [c for c in candles if c.timestamp < end_time]

            return candles

        except ccxt.NetworkError as e:
            logger.error(f"Network error fetching timeframe data for {symbol}: {e}")
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Exchange error fetching timeframe data for {symbol}: {e}")
            raise Exception(f"Exchange error: {str(e)}")

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

    def _get_interval_seconds(self, interval: str) -> int:
        """Get interval duration in seconds."""
        return self._get_interval_minutes(interval) * 60
    
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
