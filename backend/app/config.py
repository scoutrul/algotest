"""
Configuration settings for the BackTest Trading Bot backend.
"""
import os
from typing import List, Dict, Any

class Settings:
    """Application settings and configuration."""
    
    # API Configuration
    API_TITLE: str = "BackTest Trading Bot API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "API for cryptocurrency backtesting and strategy analysis"
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]
    
    # Binance Configuration
    BINANCE_API_URL: str = "https://api.binance.com"
    BINANCE_RATE_LIMIT: int = 1200  # requests per minute
    BINANCE_TIMEOUT: int = 30  # seconds
    
    # Strategy Default Parameters
    DEFAULT_STRATEGY_PARAMS: Dict[str, Any] = {
        "lookback_period": 20,
        "volume_threshold": 1.5,
        "min_price_change": 0.005,
        "take_profit": 0.02,
        "stop_loss": 0.01,
        "max_trades": 100,
        "initial_capital": 10000
    }
    
    # Supported Symbols
    SUPPORTED_SYMBOLS: List[str] = [
        "BTC/USDT",
        "ETH/USDT", 
        "BNB/USDT",
        "ADA/USDT",
        "SOL/USDT",
        "XRP/USDT",
        "DOT/USDT",
        "DOGE/USDT"
    ]
    
    # Supported Intervals
    SUPPORTED_INTERVALS: List[str] = [
        "1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d"
    ]
    
    # Data Limits
    MAX_CANDLES_LIMIT: int = 1000
    DEFAULT_CANDLES_LIMIT: int = 500
    
    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Global settings instance
settings = Settings()
