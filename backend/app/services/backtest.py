"""
Backtest engine service for orchestrating backtest execution.
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .data_fetcher import DataFetcher
from .strategy import HybridStrategy
from ..models.backtest import BacktestResult, BacktestRequest
from ..models.strategy import StrategyParams
from ..config import settings

logger = logging.getLogger(__name__)

class BacktestEngine:
    """Orchestrates backtest execution with data fetching and strategy execution."""
    
    def __init__(self):
        """Initialize the backtest engine."""
        self.data_fetcher = DataFetcher()
        self.strategy = HybridStrategy(settings.DEFAULT_STRATEGY_PARAMS)
        
        logger.info("Backtest Engine initialized successfully")
    
    async def run_backtest(self, request: BacktestRequest) -> BacktestResult:
        """
        Run a complete backtest.
        
        Args:
            request: Backtest request parameters
            
        Returns:
            Backtest result
        """
        try:
            start_time = datetime.now()
            logger.info(f"Starting backtest for {request.symbol} {request.interval}")
            
            # Step 1: Fetch historical data
            logger.info("Fetching historical data...")
            candles = await self._fetch_historical_data(request)
            
            if not candles:
                return self._create_error_result(
                    request, 
                    start_time, 
                    "No historical data available"
                )
            
            # Step 2: Validate and prepare strategy parameters
            logger.info("Preparing strategy parameters...")
            strategy_params = self._prepare_strategy_params(request)
            
            # Step 3: Execute backtest
            logger.info("Executing backtest...")
            backtest_result = self.strategy.run_backtest(candles, strategy_params)
            
            # Step 4: Create final result
            result = BacktestResult(
                strategy_params=request.strategy_params,
                candles=candles,
                trades=backtest_result['trades'],
                statistics=backtest_result['statistics'],
                final_capital=backtest_result['final_capital'],
                execution_time=backtest_result['execution_time'],
                data_period=backtest_result['data_period'],
                success=backtest_result['success'],
                error_message=backtest_result.get('error_message')
            )
            
            logger.info(f"Backtest completed successfully: {len(result.trades)} trades")
            return result
            
        except Exception as e:
            logger.error(f"Error in backtest execution: {e}")
            return self._create_error_result(request, start_time, str(e))
    
    async def _fetch_historical_data(self, request: BacktestRequest) -> List:
        """Fetch historical data for the backtest."""
        try:
            # Determine data limit
            limit = request.limit or settings.DEFAULT_CANDLES_LIMIT
            
            # Fetch candles
            candles = await self.data_fetcher.fetch_candles(
                symbol=request.symbol,
                interval=request.interval,
                limit=limit
            )
            
            # Filter by timeframe if specified
            if request.start_time or request.end_time:
                filtered_candles = []
                for candle in candles:
                    if request.start_time and candle.timestamp < request.start_time:
                        continue
                    if request.end_time and candle.timestamp > request.end_time:
                        continue
                    filtered_candles.append(candle)
                candles = filtered_candles
            
            logger.info(f"Fetched {len(candles)} candles for backtest")
            return candles
            
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return []
    
    def _prepare_strategy_params(self, request: BacktestRequest) -> StrategyParams:
        """Prepare and validate strategy parameters."""
        try:
            # Merge request parameters with defaults
            params_dict = settings.DEFAULT_STRATEGY_PARAMS.copy()
            params_dict.update(request.strategy_params)
            params_dict.update({
                'symbol': request.symbol,
                'interval': request.interval
            })
            
            # Create and validate StrategyParams
            strategy_params = StrategyParams(**params_dict)
            
            logger.info(f"Strategy parameters prepared: {strategy_params.model_dump()}")
            return strategy_params
            
        except Exception as e:
            logger.error(f"Error preparing strategy parameters: {e}")
            raise ValueError(f"Invalid strategy parameters: {e}")
    
    def _create_error_result(
        self, 
        request: BacktestRequest, 
        start_time: datetime, 
        error_message: str
    ) -> BacktestResult:
        """Create an error result."""
        return BacktestResult(
            strategy_params=request.strategy_params,
            candles=[],
            trades=[],
            statistics={
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'total_return': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'avg_trade_duration': 0,
                'max_trade_duration': 0,
                'min_trade_duration': 0,
                'consecutive_wins': 0,
                'consecutive_losses': 0,
                'largest_win': 0,
                'largest_loss': 0
            },
            final_capital=request.strategy_params.get('initial_capital', 10000),
            execution_time=(datetime.now() - start_time).total_seconds(),
            data_period={'start': None, 'end': None},
            success=False,
            error_message=error_message
        )
    
    async def get_available_symbols(self) -> List[str]:
        """Get list of available trading symbols."""
        return self.data_fetcher.get_available_symbols()
    
    async def get_available_intervals(self) -> List[str]:
        """Get list of available time intervals."""
        return self.data_fetcher.get_available_intervals()
    
    def validate_request(self, request: BacktestRequest) -> Dict[str, Any]:
        """Validate backtest request parameters."""
        errors = []
        
        # Validate symbol
        if not self.data_fetcher.validate_symbol(request.symbol):
            errors.append(f"Invalid symbol: {request.symbol}")
        
        # Validate interval
        if not self.data_fetcher.validate_interval(request.interval):
            errors.append(f"Invalid interval: {request.interval}")
        
        # Validate strategy parameters
        try:
            self._prepare_strategy_params(request)
        except Exception as e:
            errors.append(f"Invalid strategy parameters: {e}")
        
        # Validate limit
        if request.limit and (request.limit < 1 or request.limit > settings.MAX_CANDLES_LIMIT):
            errors.append(f"Invalid limit: {request.limit}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def get_engine_info(self) -> Dict[str, Any]:
        """Get information about the backtest engine."""
        return {
            'name': 'Backtest Engine',
            'version': '1.0.0',
            'strategy': self.strategy.get_strategy_info(),
            'data_fetcher': {
                'exchange': 'Binance',
                'supported_symbols': len(self.data_fetcher.get_available_symbols()),
                'supported_intervals': len(self.data_fetcher.get_available_intervals())
            },
            'config': {
                'max_candles_limit': settings.MAX_CANDLES_LIMIT,
                'default_candles_limit': settings.DEFAULT_CANDLES_LIMIT
            }
        }
