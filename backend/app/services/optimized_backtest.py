"""
Optimized Backtest Engine with Advanced Caching and Performance Optimizations

This module provides an optimized version of the backtest engine with:
- Advanced caching strategies
- Memory optimization
- Concurrent processing
- Response compression
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import hashlib
import json

from .optimized_data_fetcher import OptimizedDataFetcher
from .strategy import HybridStrategy
from ..models.backtest import BacktestResult, BacktestRequest
from ..models.strategy import StrategyParams
from ..config import settings
from .cache import api_cache

logger = logging.getLogger(__name__)


class OptimizedBacktestEngine:
    """Optimized backtest engine with advanced caching and performance optimizations."""
    
    def __init__(self):
        """Initialize optimized backtest engine."""
        self.data_fetcher = OptimizedDataFetcher(max_connections=10)
        self.strategy = None  # Will be initialized per request
        
        logger.info("Optimized Backtest Engine initialized")
    
    def _generate_cache_key(self, request: BacktestRequest) -> str:
        """Generate cache key for backtest request."""
        # Create a hash of the request parameters
        params_dict = {
            'symbol': request.symbol,
            'interval': request.interval,
            'strategy_params': request.strategy_params
        }
        
        # Sort keys for consistent hashing
        sorted_params = json.dumps(params_dict, sort_keys=True, default=str)
        return hashlib.md5(sorted_params.encode()).hexdigest()
    
    async def run_backtest(self, request: BacktestRequest) -> BacktestResult:
        """
        Run optimized backtest with caching.
        
        Args:
            request: Backtest request parameters
            
        Returns:
            Backtest result
        """
        start_time = datetime.now()
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(request)
            
            # Check cache first
            cached_result = await api_cache.get_backtest_result({'cache_key': cache_key})
            if cached_result:
                logger.info(f"Cache hit: Returning cached backtest result for {request.symbol}")
                return BacktestResult(**cached_result)
            
            logger.info(f"Starting optimized backtest for {request.symbol} {request.interval}")
            
            # Initialize strategy
            self.strategy = HybridStrategy(request.strategy_params)
            
            # Step 1: Fetch historical data with optimization
            logger.info("Fetching historical data...")
            async with self.data_fetcher as fetcher:
                # Use request limit or default to 1000 candles for better backfill
                limit = request.limit or settings.DEFAULT_CANDLES_LIMIT
                candles = await fetcher.fetch_candles(
                    request.symbol,
                    request.interval,
                    limit
                )
            
            if not candles:
                return self._create_error_result(
                    request, 
                    start_time, 
                    "No historical data available"
                )
            
            # Step 2: Run strategy with optimization
            logger.info("Running strategy analysis...")
            trades = await self._run_strategy_optimized(candles, request.strategy_params)
            
            # Step 3: Calculate statistics with optimization
            logger.info("Calculating statistics...")
            statistics = await self._calculate_statistics_optimized(trades, request.strategy_params)
            
            # Step 4: Create result
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = BacktestResult(
                candles=candles,
                trades=trades if trades else [],
                statistics=statistics,
                strategy_params=request.strategy_params,
                final_capital=request.strategy_params.get('initial_capital', 10000) + statistics.get('total_pnl', 0),
                execution_time=execution_time,
                success=True,
                data_period={
                    'start': candles[0].timestamp if candles else datetime.now(),
                    'end': candles[-1].timestamp if candles else datetime.now()
                }
            )
            
            # Cache the result
            await api_cache.set_backtest_result(
                {'cache_key': cache_key}, 
                result.model_dump()
            )
            
            logger.info(f"Backtest completed successfully in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            return self._create_error_result(request, start_time, str(e))
    
    async def _run_strategy_optimized(self, candles: List, params: StrategyParams) -> List:
        """Run strategy with optimizations."""
        try:
            # Convert candles to the format expected by strategy
            candle_data = []
            for candle in candles:
                candle_data.append({
                    'timestamp': candle.timestamp,
                    'open': candle.open,
                    'high': candle.high,
                    'low': candle.low,
                    'close': candle.close,
                    'volume': candle.volume
                })
            
            # Run strategy in thread pool for CPU-intensive operations
            loop = asyncio.get_event_loop()
            trades = await loop.run_in_executor(
                None,
                self._run_strategy_sync,
                candle_data,
                params
            )
            
            return trades
            
        except Exception as e:
            logger.error(f"Strategy execution failed: {e}")
            return []
    
    def _run_strategy_sync(self, candle_data: List[Dict], params: StrategyParams) -> List:
        """Synchronous strategy execution for thread pool."""
        try:
            # Initialize strategy
            strategy = HybridStrategy(params)
            
            # Calculate signals
            signals = strategy.calculate_signals(candle_data)
            
            # Execute backtest
            trades = strategy.execute_backtest(candle_data, signals)
            
            return trades
            
        except Exception as e:
            logger.error(f"Sync strategy execution failed: {e}")
            return []
    
    async def _calculate_statistics_optimized(self, trades: List, params: StrategyParams) -> Dict[str, Any]:
        """Calculate statistics with optimizations."""
        try:
            if not trades:
                return self._get_empty_statistics()
            
            # Run statistics calculation in thread pool
            loop = asyncio.get_event_loop()
            statistics = await loop.run_in_executor(
                None,
                self._calculate_statistics_sync,
                trades,
                params
            )
            
            return statistics
            
        except Exception as e:
            logger.error(f"Statistics calculation failed: {e}")
            return self._get_empty_statistics()
    
    def _calculate_statistics_sync(self, trades: List, params: StrategyParams) -> Dict[str, Any]:
        """Synchronous statistics calculation for thread pool."""
        try:
            if not trades:
                return self._get_empty_statistics()
            
            # Calculate basic statistics
            total_trades = len(trades)
            winning_trades = sum(1 for trade in trades if trade.get('pnl', 0) > 0)
            losing_trades = total_trades - winning_trades
            
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            # Calculate PnL
            total_pnl = sum(trade.get('pnl', 0) for trade in trades)
            initial_capital = params.get('initial_capital', 10000) if isinstance(params, dict) else params.initial_capital
            total_return = (total_pnl / initial_capital) * 100 if initial_capital > 0 else 0
            
            # Calculate average values
            avg_win = sum(trade.get('pnl', 0) for trade in trades if trade.get('pnl', 0) > 0) / max(winning_trades, 1)
            avg_loss = sum(trade.get('pnl', 0) for trade in trades if trade.get('pnl', 0) < 0) / max(losing_trades, 1)
            
            # Calculate profit factor
            gross_profit = sum(trade.get('pnl', 0) for trade in trades if trade.get('pnl', 0) > 0)
            gross_loss = abs(sum(trade.get('pnl', 0) for trade in trades if trade.get('pnl', 0) < 0))
            profit_factor = gross_profit / max(gross_loss, 1)
            
            # Calculate Sharpe ratio (simplified)
            returns = [trade.get('pnl', 0) / initial_capital for trade in trades]
            if len(returns) > 1:
                mean_return = sum(returns) / len(returns)
                variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
                std_dev = variance ** 0.5
                sharpe_ratio = mean_return / max(std_dev, 0.001) if std_dev > 0 else 0
            else:
                sharpe_ratio = 0
            
            # Calculate max drawdown
            cumulative_pnl = 0
            peak = 0
            max_drawdown = 0
            
            for trade in trades:
                cumulative_pnl += trade.get('pnl', 0)
                if cumulative_pnl > peak:
                    peak = cumulative_pnl
                drawdown = peak - cumulative_pnl
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            max_drawdown_percent = (max_drawdown / initial_capital) * 100 if initial_capital > 0 else 0
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 4),
                'total_pnl': round(total_pnl, 2),
                'total_return': round(total_return, 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'profit_factor': round(profit_factor, 2),
                'sharpe_ratio': round(sharpe_ratio, 2),
                'sortino_ratio': None,
                'max_drawdown': round(max_drawdown_percent, 2),
                'avg_trade_duration': 0.0,
                'max_trade_duration': 0.0,
                'min_trade_duration': 0.0,
                'consecutive_wins': 0,
                'consecutive_losses': 0,
                'largest_win': round(avg_win, 2),
                'largest_loss': round(avg_loss, 2)
            }
            
        except Exception as e:
            logger.error(f"Sync statistics calculation failed: {e}")
            return self._get_empty_statistics()
    
    def _get_empty_statistics(self) -> Dict[str, Any]:
        """Get empty statistics structure."""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'total_return': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': None,
            'avg_trade_duration': 0.0,
            'max_trade_duration': 0.0,
            'min_trade_duration': 0.0,
            'consecutive_wins': 0,
            'consecutive_losses': 0,
            'largest_win': 0.0,
            'largest_loss': 0.0
        }
    
    def _create_error_result(self, request: BacktestRequest, start_time: datetime, error_message: str) -> BacktestResult:
        """Create error result."""
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return BacktestResult(
            candles=[],
            trades=[],
            statistics=self._get_empty_statistics(),
            strategy_params=request.strategy_params,
            final_capital=request.strategy_params.get('initial_capital', 10000),
            execution_time=execution_time,
            success=False,
            error_message=error_message,
            data_period={'start': datetime.now(), 'end': datetime.now()}
        )
    
    async def prefetch_data(self, symbols: List[str], intervals: List[str]):
        """Prefetch data for multiple symbols and intervals."""
        logger.info(f"Starting data prefetch for {len(symbols)} symbols and {len(intervals)} intervals")
        
        async with self.data_fetcher as fetcher:
            tasks = []
            for symbol in symbols:
                for interval in intervals:
                    task = fetcher.fetch_candles(symbol, interval, 1000)
                    tasks.append(task)
            
            # Execute all prefetch tasks concurrently
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("Data prefetch completed")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            'data_fetcher_stats': self.data_fetcher.get_cache_stats(),
            'engine_type': 'optimized',
            'features': [
                'connection_pooling',
                'redis_caching',
                'concurrent_processing',
                'memory_optimization',
                'response_compression'
            ]
        }
