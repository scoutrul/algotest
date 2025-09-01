"""
Tests for DataFetcher service.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch
from app.services.data_fetcher import DataFetcher
from app.config import settings


class TestDataFetcher:
    """Test cases for DataFetcher service."""
    
    @pytest.fixture
    def data_fetcher(self):
        """Create DataFetcher instance for testing."""
        return DataFetcher()
    
    def test_validate_symbol_valid(self, data_fetcher):
        """Test symbol validation with valid symbols."""
        valid_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        
        for symbol in valid_symbols:
            assert data_fetcher.validate_symbol(symbol) is True
    
    def test_validate_symbol_invalid(self, data_fetcher):
        """Test symbol validation with invalid symbols."""
        invalid_symbols = ['BTCUSDT', 'BTC-USD', 'BTC_USDT', '']
        
        for symbol in invalid_symbols:
            assert data_fetcher.validate_symbol(symbol) is False
    
    def test_validate_interval_valid(self, data_fetcher):
        """Test interval validation with valid intervals."""
        valid_intervals = ['1m', '15m', '1h', '1d']
        
        for interval in valid_intervals:
            assert data_fetcher.validate_interval(interval) is True
    
    def test_validate_interval_invalid(self, data_fetcher):
        """Test interval validation with invalid intervals."""
        invalid_intervals = ['1min', '15min', '1hour', '']
        
        for interval in invalid_intervals:
            assert data_fetcher.validate_interval(interval) is False
    
    def test_get_available_symbols(self, data_fetcher):
        """Test getting available symbols."""
        symbols = data_fetcher.get_available_symbols()
        
        assert isinstance(symbols, list)
        assert len(symbols) > 0
        assert 'BTC/USDT' in symbols
    
    def test_get_available_intervals(self, data_fetcher):
        """Test getting available intervals."""
        intervals = data_fetcher.get_available_intervals()
        
        assert isinstance(intervals, list)
        assert len(intervals) > 0
        assert '15m' in intervals
    
    def test_convert_interval(self, data_fetcher):
        """Test interval conversion to ccxt format."""
        test_cases = [
            ('1m', '1m'),
            ('15m', '15m'),
            ('1h', '1h'),
            ('1d', '1d')
        ]
        
        for input_interval, expected in test_cases:
            result = data_fetcher._convert_interval(input_interval)
            assert result == expected
    
    def test_get_interval_minutes(self, data_fetcher):
        """Test getting interval duration in minutes."""
        test_cases = [
            ('1m', 1),
            ('15m', 15),
            ('1h', 60),
            ('1d', 1440)
        ]
        
        for interval, expected_minutes in test_cases:
            result = data_fetcher._get_interval_minutes(interval)
            assert result == expected_minutes
    
    def test_clear_cache(self, data_fetcher):
        """Test cache clearing functionality."""
        # Add some test data to cache
        data_fetcher._cache['test_key'] = ['test_data']
        
        # Clear cache
        data_fetcher.clear_cache()
        
        # Verify cache is empty
        assert len(data_fetcher._cache) == 0
    
    def test_get_cache_info(self, data_fetcher):
        """Test getting cache information."""
        cache_info = data_fetcher.get_cache_info()
        
        assert isinstance(cache_info, dict)
        assert 'cache_size' in cache_info
        assert 'cache_keys' in cache_info
        assert 'cache_ttl' in cache_info
        assert cache_info['cache_size'] == 0  # Initially empty


@pytest.mark.asyncio
class TestDataFetcherAsync:
    """Async test cases for DataFetcher service."""
    
    @pytest.fixture
    def data_fetcher(self):
        """Create DataFetcher instance for testing."""
        return DataFetcher()
    
    @patch('app.services.data_fetcher.ccxt.binance')
    async def test_fetch_candles_success(self, mock_ccxt, data_fetcher):
        """Test successful candle fetching."""
        # Mock ccxt response
        mock_exchange = Mock()
        mock_exchange.fetch_ohlcv.return_value = [
            [1640995200000, 50000, 51000, 49000, 50500, 1000],  # timestamp, open, high, low, close, volume
            [1640995260000, 50500, 51500, 50000, 51000, 1200]
        ]
        mock_ccxt.return_value = mock_exchange
        
        # Test fetching
        candles = await data_fetcher.fetch_candles('BTC/USDT', '15m', 2)
        
        assert len(candles) == 2
        assert candles[0].open == 50000
        assert candles[0].close == 50500
        assert candles[1].volume == 1200
    
    @patch('app.services.data_fetcher.ccxt.binance')
    async def test_fetch_candles_invalid_symbol(self, mock_ccxt, data_fetcher):
        """Test candle fetching with invalid symbol."""
        with pytest.raises(ValueError, match="Unsupported symbol"):
            await data_fetcher.fetch_candles('INVALID/USDT', '15m', 10)
    
    @patch('app.services.data_fetcher.ccxt.binance')
    async def test_fetch_candles_invalid_interval(self, mock_ccxt, data_fetcher):
        """Test candle fetching with invalid interval."""
        with pytest.raises(ValueError, match="Unsupported interval"):
            await data_fetcher.fetch_candles('BTC/USDT', 'invalid', 10)
    
    @patch('app.services.data_fetcher.ccxt.binance')
    async def test_fetch_candles_insufficient_data(self, mock_ccxt, data_fetcher):
        """Test candle fetching with insufficient data."""
        # Mock ccxt response
        mock_exchange = Mock()
        mock_exchange.fetch_ohlcv.return_value = []
        mock_ccxt.return_value = mock_exchange
        
        # Test with lookback period that requires more data
        data_fetcher.lookback_period = 20
        
        with pytest.raises(ValueError, match="Insufficient data"):
            await data_fetcher.fetch_candles('BTC/USDT', '15m', 10)
    
    async def test_fetch_candles_with_timeframe(self, data_fetcher):
        """Test candle fetching with timeframe parameters."""
        # This test would require more complex mocking of the ccxt library
        # For now, we'll test the method exists and handles basic cases
        assert hasattr(data_fetcher, 'fetch_candles_with_timeframe')
        assert callable(data_fetcher.fetch_candles_with_timeframe)
