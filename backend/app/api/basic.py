"""
Basic API endpoints for configuration and data access.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
import random

from ..config import settings
from ..services.database import get_db
from ..models.database import Candle
from ..models.backtest import CandleData

router = APIRouter(prefix="/api/v1", tags=["basic"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.API_VERSION,
        "features": {
            "backtesting": True,
            "market_data": True,
            "liquidity_analysis": settings.LIQUIDITY_FEATURE_ENABLED
        }
    }


@router.get("/config")
async def get_config():
    """Get application configuration."""
    return {
        "api_title": settings.API_TITLE,
        "api_version": settings.API_VERSION,
        "default_strategy_params": settings.DEFAULT_STRATEGY_PARAMS,
        "supported_symbols": settings.SUPPORTED_SYMBOLS,
        "supported_intervals": settings.SUPPORTED_INTERVALS,
        "max_candles_limit": settings.MAX_CANDLES_LIMIT,
        "default_candles_limit": settings.DEFAULT_CANDLES_LIMIT,
        "liquidity_feature_enabled": settings.LIQUIDITY_FEATURE_ENABLED
    }


@router.get("/symbols")
async def get_symbols():
    """Get supported trading symbols."""
    return {
        "symbols": settings.SUPPORTED_SYMBOLS,
        "count": len(settings.SUPPORTED_SYMBOLS)
    }


@router.get("/intervals")
async def get_intervals():
    """Get supported time intervals."""
    return {
        "intervals": settings.SUPPORTED_INTERVALS,
        "count": len(settings.SUPPORTED_INTERVALS)
    }


@router.get("/candles")
async def get_candles(
    symbol: str = Query(..., description="Trading symbol (e.g., BTC/USDT)"),
    interval: str = Query(..., description="Time interval (e.g., 15m)"),
    limit: int = Query(500, ge=1, le=5000, description="Maximum number of candles"),
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    db: Session = Depends(get_db)
):
    """Get historical candle data."""
    try:
        # Parse time filters
        start_dt = None
        end_dt = None
        
        if start_time:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        if end_time:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        # Query database
        query = db.query(Candle).filter(
            Candle.symbol == symbol,
            Candle.interval == interval
        )
        
        if start_dt:
            query = query.filter(Candle.timestamp >= start_dt.replace(tzinfo=None))
        if end_dt:
            query = query.filter(Candle.timestamp <= end_dt.replace(tzinfo=None))
        
        # Order by timestamp descending and limit
        candles = query.order_by(Candle.timestamp.desc()).limit(limit).all()
        
        # If no candles found, generate sample data
        if not candles:
            return generate_sample_candles(symbol, interval, limit)
        
        # Convert to response format (reverse to get chronological order)
        candle_data = []
        for candle in reversed(candles):
            candle_data.append({
                "timestamp": candle.timestamp.isoformat(),
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume
            })
        
        return candle_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid time format: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get candles: {e}")


@router.get("/data/status")
async def get_data_status(db: Session = Depends(get_db)):
    """Get data synchronization status."""
    try:
        from ..models.database import MarketDataStatus
        
        # Get status for all symbol/interval combinations
        statuses = db.query(MarketDataStatus).all()
        
        status_data = []
        for status in statuses:
            status_data.append({
                "symbol": status.symbol,
                "interval": status.interval,
                "last_updated": status.last_updated.isoformat() if status.last_updated else None,
                "oldest_timestamp": status.oldest_timestamp.isoformat() if status.oldest_timestamp else None,
                "newest_timestamp": status.newest_timestamp.isoformat() if status.newest_timestamp else None,
                "total_candles": status.total_candles
            })
        
        return {
            "statuses": status_data,
            "count": len(status_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get data status: {e}")


def generate_sample_candles(symbol: str, interval: str, limit: int) -> List[dict]:
    """Generate sample candle data for testing."""
    # Base prices for different symbols
    base_prices = {
        "BTC/USDT": 43000,
        "ETH/USDT": 2500,
        "BNB/USDT": 300,
        "ADA/USDT": 0.5,
        "SOL/USDT": 100,
        "XRP/USDT": 0.6,
        "DOT/USDT": 7,
        "DOGE/USDT": 0.08
    }
    
    base_price = base_prices.get(symbol, 100)
    
    # Time interval in minutes
    interval_minutes = {
        "1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60,
        "2h": 120, "4h": 240, "6h": 360, "12h": 720, "1d": 1440
    }
    
    minutes = interval_minutes.get(interval, 15)
    
    # Generate candles
    candles = []
    current_time = datetime.now() - timedelta(minutes=minutes * limit)
    current_price = base_price
    
    for i in range(limit):
        # Generate OHLCV data with some randomness
        open_price = current_price
        
        # Random price movement (±2%)
        price_change = random.uniform(-0.02, 0.02)
        close_price = open_price * (1 + price_change)
        
        # High and low based on open/close
        high_price = max(open_price, close_price) * random.uniform(1.0, 1.01)
        low_price = min(open_price, close_price) * random.uniform(0.99, 1.0)
        
        # Volume
        volume = random.uniform(10, 1000)
        
        candles.append({
            "timestamp": current_time.isoformat(),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": round(volume, 3)
        })
        
        current_price = close_price
        current_time += timedelta(minutes=minutes)
    
    return candles
