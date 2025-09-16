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
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175"
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
        "1m", "15m", "1h", "4h", "12h", "1d", "1w", "1M"
    ]
    
    # Data Limits
    MAX_CANDLES_LIMIT: int = 10000
    DEFAULT_CANDLES_LIMIT: int = 1000
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./backtest.db")
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "False").lower() == "true"

    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 🚀 Liquidity Feature Configuration
    LIQUIDITY_FEATURE_ENABLED: bool = os.getenv("LIQUIDITY_FEATURE_ENABLED", "true").lower() == "true"
    LIQUIDITY_EXCHANGE: str = os.getenv("LIQUIDITY_EXCHANGE", "binance")
    LIQUIDITY_SYMBOLS: List[str] = os.getenv("LIQUIDITY_SYMBOLS", "BTC/USDT,ETH/USDT,BNB/USDT").split(",")
    LIQUIDITY_COLLECTION_INTERVAL: int = int(os.getenv("LIQUIDITY_COLLECTION_INTERVAL", "30"))  # seconds
    LIQUIDITY_ORDER_BOOK_LIMIT: int = int(os.getenv("LIQUIDITY_ORDER_BOOK_LIMIT", "20"))  # levels
    LIQUIDITY_HISTORY_RETENTION_DAYS: int = int(os.getenv("LIQUIDITY_HISTORY_RETENTION_DAYS", "30"))
    LIQUIDITY_MIN_VOLUME_THRESHOLD: float = float(os.getenv("LIQUIDITY_MIN_VOLUME_THRESHOLD", "0.01"))
    
    # Liquidity Aggregation Settings
    LIQUIDITY_AGGREGATION_INTERVALS: List[str] = ["5m", "15m", "1h", "4h", "1d"]
    LIQUIDITY_MAX_HISTORY_LIMIT: int = 1000

# Global settings instance
settings = Settings()
