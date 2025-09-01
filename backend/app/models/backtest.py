"""
Backtest result models and data structures.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class TradeDirection(str, Enum):
    """Trade direction enum."""
    LONG = "long"
    SHORT = "short"

class ExitReason(str, Enum):
    """Trade exit reason enum."""
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    MANUAL = "manual"
    TIMEOUT = "timeout"

class CandleData(BaseModel):
    """OHLCV candle data model."""
    
    timestamp: datetime = Field(..., description="Candle timestamp")
    open: float = Field(..., gt=0, description="Opening price")
    high: float = Field(..., gt=0, description="Highest price")
    low: float = Field(..., gt=0, description="Lowest price")
    close: float = Field(..., gt=0, description="Closing price")
    volume: float = Field(..., ge=0, description="Trading volume")
    
    @classmethod
    def from_ccxt(cls, data: List) -> 'CandleData':
        """Create CandleData from ccxt format [timestamp, open, high, low, close, volume]."""
        return cls(
            timestamp=datetime.fromtimestamp(data[0] / 1000),
            open=float(data[1]),
            high=float(data[2]),
            low=float(data[3]),
            close=float(data[4]),
            volume=float(data[5])
        )

class Trade(BaseModel):
    """Individual trade model."""
    
    id: str = Field(..., description="Unique trade identifier")
    entry_time: datetime = Field(..., description="Trade entry timestamp")
    exit_time: Optional[datetime] = Field(None, description="Trade exit timestamp")
    direction: TradeDirection = Field(..., description="Trade direction")
    entry_price: float = Field(..., gt=0, description="Entry price")
    exit_price: Optional[float] = Field(None, gt=0, description="Exit price")
    size: float = Field(..., gt=0, description="Trade size")
    pnl: Optional[float] = Field(None, description="Profit/Loss")
    exit_reason: Optional[ExitReason] = Field(None, description="Exit reason")
    
    # Risk management levels
    take_profit: float = Field(..., gt=0, description="Take profit price")
    stop_loss: float = Field(..., gt=0, description="Stop loss price")
    
    # Additional metrics
    duration_minutes: Optional[int] = Field(None, description="Trade duration in minutes")
    max_favorable: Optional[float] = Field(None, description="Maximum favorable excursion")
    max_adverse: Optional[float] = Field(None, description="Maximum adverse excursion")

class BacktestStatistics(BaseModel):
    """Backtest performance statistics."""
    
    # Trade statistics
    total_trades: int = Field(..., ge=0, description="Total number of trades")
    winning_trades: int = Field(..., ge=0, description="Number of winning trades")
    losing_trades: int = Field(..., ge=0, description="Number of losing trades")
    win_rate: float = Field(..., ge=0, le=1, description="Win rate percentage")
    
    # PnL statistics
    total_pnl: float = Field(..., description="Total profit/loss")
    total_return: float = Field(..., description="Total return percentage")
    avg_win: float = Field(..., description="Average winning trade")
    avg_loss: float = Field(..., description="Average losing trade")
    profit_factor: float = Field(..., description="Profit factor (gross profit / gross loss)")
    
    # Risk metrics
    max_drawdown: float = Field(..., ge=0, description="Maximum drawdown percentage")
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    sortino_ratio: Optional[float] = Field(None, description="Sortino ratio")
    
    # Time metrics
    avg_trade_duration: float = Field(..., description="Average trade duration in minutes")
    max_trade_duration: float = Field(..., description="Maximum trade duration in minutes")
    min_trade_duration: float = Field(..., description="Minimum trade duration in minutes")
    
    # Additional metrics
    consecutive_wins: int = Field(..., ge=0, description="Maximum consecutive wins")
    consecutive_losses: int = Field(..., ge=0, description="Maximum consecutive losses")
    largest_win: float = Field(..., description="Largest winning trade")
    largest_loss: float = Field(..., description="Largest losing trade")

class BacktestResult(BaseModel):
    """Complete backtest result model."""
    
    # Input parameters
    strategy_params: Dict[str, Any] = Field(..., description="Strategy parameters used")
    
    # Data
    candles: List[CandleData] = Field(..., description="Historical candle data")
    trades: List[Trade] = Field(..., description="Generated trades")
    
    # Results
    statistics: BacktestStatistics = Field(..., description="Performance statistics")
    final_capital: float = Field(..., gt=0, description="Final capital after backtest")
    
    # Metadata
    execution_time: float = Field(..., description="Backtest execution time in seconds")
    data_period: Dict[str, datetime] = Field(..., description="Data period (start, end)")
    success: bool = Field(default=True, description="Whether backtest was successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")

class BacktestRequest(BaseModel):
    """Backtest request model."""
    
    symbol: str = Field(..., description="Trading pair symbol")
    interval: str = Field(..., description="Time interval")
    strategy_params: Dict[str, Any] = Field(..., description="Strategy parameters")
    
    # Optional parameters
    limit: Optional[int] = Field(None, ge=1, le=1000, description="Number of candles to fetch")
    start_time: Optional[datetime] = Field(None, description="Start time for data")
    end_time: Optional[datetime] = Field(None, description="End time for data")
