"""
Backtest API endpoints.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from ..services.backtest import BacktestEngine
from ..models.backtest import BacktestRequest, BacktestResult
from ..models.strategy import StrategyParams
from ..config import settings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1", tags=["backtest"])

# Global backtest engine instance
backtest_engine = BacktestEngine()

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "service": "BackTest Trading Bot API"
    }

@router.get("/symbols")
async def get_symbols():
    """Get available trading symbols."""
    try:
        symbols = await backtest_engine.get_available_symbols()
        return {"symbols": symbols}
    except Exception as e:
        logger.error(f"Error getting symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/intervals")
async def get_intervals():
    """Get available time intervals."""
    try:
        intervals = await backtest_engine.get_available_intervals()
        return {"intervals": intervals}
    except Exception as e:
        logger.error(f"Error getting intervals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/backtest", response_model=BacktestResult)
async def run_backtest(
    symbol: str = Query(..., description="Trading pair symbol (e.g., BTC/USDT)"),
    interval: str = Query(..., description="Time interval (e.g., 15m, 1h)"),
    lookback_period: Optional[int] = Query(None, ge=5, le=100, description="Lookback period for volume analysis"),
    volume_threshold: Optional[float] = Query(None, gt=1.0, le=5.0, description="Volume spike threshold"),
    min_price_change: Optional[float] = Query(None, gt=0.0, le=0.1, description="Minimum price change for signals"),
    take_profit: Optional[float] = Query(None, gt=0.0, le=0.5, description="Take profit percentage"),
    stop_loss: Optional[float] = Query(None, gt=0.0, le=0.5, description="Stop loss percentage"),
    max_trades: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of trades"),
    initial_capital: Optional[float] = Query(None, gt=0, description="Initial capital"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Number of candles to fetch")
):
    """
    Run a backtest with the specified parameters.
    
    Args:
        symbol: Trading pair symbol
        interval: Time interval
        lookback_period: Number of candles for volume average
        volume_threshold: Volume spike multiplier
        min_price_change: Minimum price change for signal detection
        take_profit: Take profit percentage
        stop_loss: Stop loss percentage
        max_trades: Maximum number of trades
        initial_capital: Starting capital
        limit: Number of candles to fetch
        
    Returns:
        Backtest result with trades and statistics
    """
    try:
        # Prepare strategy parameters
        strategy_params = {}
        
        if lookback_period is not None:
            strategy_params['lookback_period'] = lookback_period
        if volume_threshold is not None:
            strategy_params['volume_threshold'] = volume_threshold
        if min_price_change is not None:
            strategy_params['min_price_change'] = min_price_change
        if take_profit is not None:
            strategy_params['take_profit'] = take_profit
        if stop_loss is not None:
            strategy_params['stop_loss'] = stop_loss
        if max_trades is not None:
            strategy_params['max_trades'] = max_trades
        if initial_capital is not None:
            strategy_params['initial_capital'] = initial_capital
        
        # Create backtest request
        request = BacktestRequest(
            symbol=symbol,
            interval=interval,
            strategy_params=strategy_params,
            limit=limit
        )
        
        # Validate request
        validation = backtest_engine.validate_request(request)
        if not validation['valid']:
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": "Invalid request parameters",
                    "details": validation['errors']
                }
            )
        
        # Run backtest
        logger.info(f"Running backtest for {symbol} {interval}")
        result = await backtest_engine.run_backtest(request)
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Backtest execution failed",
                    "message": result.error_message
                }
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in backtest endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/backtest", response_model=BacktestResult)
async def run_backtest_post(request: BacktestRequest):
    """
    Run a backtest using POST request with full request body.
    
    Args:
        request: Complete backtest request
        
    Returns:
        Backtest result with trades and statistics
    """
    try:
        # Validate request
        validation = backtest_engine.validate_request(request)
        if not validation['valid']:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid request parameters",
                    "details": validation['errors']
                }
            )
        
        # Run backtest
        logger.info(f"Running backtest for {request.symbol} {request.interval}")
        result = await backtest_engine.run_backtest(request)
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Backtest execution failed",
                    "message": result.error_message
                }
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in backtest POST endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/engine/info")
async def get_engine_info():
    """Get information about the backtest engine."""
    try:
        info = backtest_engine.get_engine_info()
        return info
    except Exception as e:
        logger.error(f"Error getting engine info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/strategy/info")
async def get_strategy_info():
    """Get information about the trading strategy."""
    try:
        info = backtest_engine.strategy.get_strategy_info()
        return info
    except Exception as e:
        logger.error(f"Error getting strategy info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
async def get_config():
    """Get current configuration."""
    try:
        return {
            "default_strategy_params": settings.DEFAULT_STRATEGY_PARAMS,
            "supported_symbols": settings.SUPPORTED_SYMBOLS,
            "supported_intervals": settings.SUPPORTED_INTERVALS,
            "max_candles_limit": settings.MAX_CANDLES_LIMIT,
            "default_candles_limit": settings.DEFAULT_CANDLES_LIMIT
        }
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
