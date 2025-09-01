"""
Strategy parameter models and validation.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum

class StrategyType(str, Enum):
    """Available strategy types."""
    HYBRID_ADAPTIVE = "hybrid_adaptive"
    VOLUME_PRICE = "volume_price"
    MOMENTUM = "momentum"

class StrategyParams(BaseModel):
    """Strategy parameters model."""
    
    # Symbol and timeframe
    symbol: str = Field(..., description="Trading pair symbol (e.g., BTC/USDT)")
    interval: str = Field(..., description="Time interval (e.g., 15m, 1h)")
    
    # Strategy parameters
    lookback_period: int = Field(
        default=20, 
        ge=5, 
        le=100, 
        description="Number of candles for volume average calculation"
    )
    volume_threshold: float = Field(
        default=1.5, 
        gt=1.0, 
        le=5.0, 
        description="Volume spike multiplier threshold"
    )
    min_price_change: float = Field(
        default=0.005, 
        gt=0.0, 
        le=0.1, 
        description="Minimum price change for signal detection"
    )
    
    # Risk management
    take_profit: float = Field(
        default=0.02, 
        gt=0.0, 
        le=0.5, 
        description="Take profit percentage"
    )
    stop_loss: float = Field(
        default=0.01, 
        gt=0.0, 
        le=0.5, 
        description="Stop loss percentage"
    )
    
    # Backtest parameters
    max_trades: int = Field(
        default=100, 
        ge=1, 
        le=1000, 
        description="Maximum number of trades per backtest"
    )
    initial_capital: float = Field(
        default=10000, 
        gt=0, 
        description="Initial capital for backtesting"
    )
    
    # Advanced parameters
    strategy_type: StrategyType = Field(
        default=StrategyType.HYBRID_ADAPTIVE,
        description="Strategy type to use"
    )
    
    @validator('symbol')
    def validate_symbol(cls, v):
        """Validate trading symbol format."""
        if '/' not in v:
            raise ValueError('Symbol must contain "/" (e.g., BTC/USDT)')
        return v.upper()
    
    @validator('interval')
    def validate_interval(cls, v):
        """Validate time interval format."""
        valid_intervals = ['1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d']
        if v not in valid_intervals:
            raise ValueError(f'Interval must be one of: {valid_intervals}')
        return v
    
    @validator('stop_loss')
    def validate_stop_loss_vs_take_profit(cls, v, values):
        """Ensure stop loss is smaller than take profit."""
        if 'take_profit' in values and v >= values['take_profit']:
            raise ValueError('Stop loss must be smaller than take profit')
        return v

class StrategyConfig(BaseModel):
    """Strategy configuration model."""
    
    name: str = Field(..., description="Strategy name")
    description: str = Field(..., description="Strategy description")
    params: StrategyParams = Field(..., description="Strategy parameters")
    enabled: bool = Field(default=True, description="Whether strategy is enabled")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
