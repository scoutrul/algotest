"""
Main strategy service implementing the Hybrid Adaptive Strategy.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .strategy.volume_analyzer import VolumeAnalyzer
from .strategy.price_analyzer import PriceAnalyzer
from .strategy.risk_manager import RiskManager
from .strategy.signal_combiner import SignalCombiner
from ..models.backtest import CandleData, Trade, TradeDirection, ExitReason
from ..models.strategy import StrategyParams

logger = logging.getLogger(__name__)

class HybridStrategy:
    """Hybrid Adaptive Strategy combining volume, price, and risk management."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the hybrid strategy.
        
        Args:
            config: Strategy configuration parameters
        """
        self.config = config
        
        # Initialize strategy components
        self.volume_analyzer = VolumeAnalyzer(config)
        self.price_analyzer = PriceAnalyzer(config)
        self.risk_manager = RiskManager(config)
        self.signal_combiner = SignalCombiner(config)
        
        logger.info("Hybrid Strategy initialized successfully")
    
    def detect_signals(self, candles: List[CandleData], params: StrategyParams) -> List[Dict[str, Any]]:
        """
        Detect trading signals using the hybrid strategy.
        
        Args:
            candles: Historical candle data
            params: Strategy parameters
            
        Returns:
            List of detected trading signals
        """
        try:
            if len(candles) < params.lookback_period + 1:
                logger.warning(f"Insufficient data for signal detection: {len(candles)} candles")
                return []
            
            # Convert params to dict for compatibility
            params_dict = params.dict()
            
            # Step 1: Volume analysis
            logger.info("Starting volume analysis...")
            volume_signals = self.volume_analyzer.analyze(candles, params_dict)
            logger.info(f"Volume analysis completed: {len(volume_signals)} signals")
            
            # Step 2: Price analysis
            logger.info("Starting price analysis...")
            price_signals = self.price_analyzer.analyze(candles, params_dict)
            logger.info(f"Price analysis completed: {len(price_signals)} signals")
            
            # Step 3: Combine signals
            logger.info("Combining signals...")
            combined_signals = self.signal_combiner.combine_signals(
                volume_signals, price_signals, candles
            )
            logger.info(f"Signal combination completed: {len(combined_signals)} signals")
            
            # Step 4: Apply risk management
            logger.info("Applying risk management...")
            final_signals = self.risk_manager.filter_signals(combined_signals, candles)
            logger.info(f"Risk management completed: {len(final_signals)} final signals")
            
            return final_signals
            
        except Exception as e:
            logger.error(f"Error in signal detection: {e}")
            return []
    
    def run_backtest(self, candles: List[CandleData], params: StrategyParams) -> Dict[str, Any]:
        """
        Run a complete backtest using the hybrid strategy.
        
        Args:
            candles: Historical candle data
            params: Strategy parameters
            
        Returns:
            Backtest results dictionary
        """
        try:
            start_time = datetime.now()
            logger.info(f"Starting backtest with {len(candles)} candles")
            
            # Detect signals
            signals = self.detect_signals(candles, params)
            
            if not signals:
                logger.warning("No signals detected for backtest")
                return self._create_empty_backtest_result(candles, params, start_time)
            
            # Execute backtest
            trades = self._execute_backtest(candles, signals, params)
            
            # Calculate statistics
            statistics = self._calculate_statistics(trades, params.initial_capital)
            
            # Create result
            result = {
                'candles': candles,
                'trades': trades,
                'statistics': statistics,
                'final_capital': params.initial_capital + sum(t.pnl for t in trades if t.pnl),
                'execution_time': (datetime.now() - start_time).total_seconds(),
                'data_period': {
                    'start': candles[0].timestamp if candles else None,
                    'end': candles[-1].timestamp if candles else None
                },
                'success': True,
                'parameters': params.dict()
            }
            
            logger.info(f"Backtest completed successfully: {len(trades)} trades, {statistics['total_pnl']:.2f} PnL")
            return result
            
        except Exception as e:
            logger.error(f"Error in backtest execution: {e}")
            return self._create_error_backtest_result(candles, params, start_time, str(e))
    
    def _execute_backtest(
        self, 
        candles: List[CandleData], 
        signals: List[Dict[str, Any]], 
        params: StrategyParams
    ) -> List[Trade]:
        """Execute the backtest simulation."""
        trades = []
        active_trades = []
        available_capital = params.initial_capital
        
        # Create signal lookup for faster access
        signal_lookup = {signal['timestamp']: signal for signal in signals}
        
        for i, candle in enumerate(candles):
            # Check exit conditions for active trades
            for trade in active_trades[:]:  # Copy to avoid modification during iteration
                exit_info = self.risk_manager.check_exit_conditions(trade, candle)
                
                if exit_info and exit_info['should_exit']:
                    # Close trade
                    trade.exit_time = candle.timestamp
                    trade.exit_price = exit_info['exit_price']
                    trade.pnl = exit_info['pnl']
                    trade.exit_reason = ExitReason(exit_info['exit_reason'])
                    
                    # Calculate duration
                    if trade.entry_time and trade.exit_time:
                        duration = trade.exit_time - trade.entry_time
                        trade.duration_minutes = int(duration.total_seconds() / 60)
                    
                    trades.append(trade)
                    active_trades.remove(trade)
                    available_capital += trade.pnl
                    
                    logger.debug(f"Trade closed: {trade.direction} PnL: {trade.pnl:.2f}")
            
            # Check for new entry signals (if no active trades and within limits)
            if (len(active_trades) == 0 and 
                len(trades) < params.max_trades and 
                candle.timestamp in signal_lookup):
                
                signal = signal_lookup[candle.timestamp]
                
                # Create new trade
                trade = self.risk_manager.create_trade(signal, candle, available_capital)
                
                if trade:
                    active_trades.append(trade)
                    available_capital -= trade.size
                    logger.debug(f"Trade opened: {trade.direction} Size: {trade.size:.2f}")
        
        # Close any remaining active trades
        if candles:
            final_candle = candles[-1]
            for trade in active_trades:
                trade.exit_time = final_candle.timestamp
                trade.exit_price = final_candle.close
                trade.pnl = self.risk_manager._calculate_pnl(trade, final_candle.close)
                trade.exit_reason = ExitReason.MANUAL
                
                if trade.entry_time and trade.exit_time:
                    duration = trade.exit_time - trade.entry_time
                    trade.duration_minutes = int(duration.total_seconds() / 60)
                
                trades.append(trade)
        
        return trades
    
    def _calculate_statistics(self, trades: List[Trade], initial_capital: float) -> Dict[str, Any]:
        """Calculate backtest performance statistics."""
        if not trades:
            return {
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
            }
        
        # Basic trade statistics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl and t.pnl < 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        # PnL statistics
        total_pnl = sum(t.pnl for t in trades if t.pnl)
        total_return = total_pnl / initial_capital if initial_capital > 0 else 0
        
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        # Drawdown calculation
        cumulative_pnl = np.cumsum([t.pnl for t in trades if t.pnl])
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = running_max - cumulative_pnl
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
        
        # Sharpe ratio (simplified)
        returns = [t.pnl / initial_capital for t in trades if t.pnl]
        if len(returns) > 1:
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = mean_return / std_return if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Duration statistics
        durations = [t.duration_minutes for t in trades if t.duration_minutes]
        avg_duration = np.mean(durations) if durations else 0
        max_duration = np.max(durations) if durations else 0
        min_duration = np.min(durations) if durations else 0
        
        # Consecutive wins/losses
        consecutive_wins, consecutive_losses = self._calculate_consecutive_trades(trades)
        
        # Largest win/loss
        pnls = [t.pnl for t in trades if t.pnl]
        largest_win = np.max(pnls) if pnls else 0
        largest_loss = np.min(pnls) if pnls else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': win_count,
            'losing_trades': loss_count,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'avg_trade_duration': avg_duration,
            'max_trade_duration': max_duration,
            'min_trade_duration': min_duration,
            'consecutive_wins': consecutive_wins,
            'consecutive_losses': consecutive_losses,
            'largest_win': largest_win,
            'largest_loss': largest_loss
        }
    
    def _calculate_consecutive_trades(self, trades: List[Trade]) -> tuple:
        """Calculate maximum consecutive wins and losses."""
        if not trades:
            return 0, 0
        
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in trades:
            if trade.pnl and trade.pnl > 0:
                current_wins += 1
                current_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, current_wins)
            elif trade.pnl and trade.pnl < 0:
                current_losses += 1
                current_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, current_losses)
        
        return max_consecutive_wins, max_consecutive_losses
    
    def _create_empty_backtest_result(
        self, 
        candles: List[CandleData], 
        params: StrategyParams, 
        start_time: datetime
    ) -> Dict[str, Any]:
        """Create empty backtest result when no signals are detected."""
        return {
            'candles': candles,
            'trades': [],
            'statistics': self._calculate_statistics([], params.initial_capital),
            'final_capital': params.initial_capital,
            'execution_time': (datetime.now() - start_time).total_seconds(),
            'data_period': {
                'start': candles[0].timestamp if candles else None,
                'end': candles[-1].timestamp if candles else None
            },
            'success': True,
            'parameters': params.dict(),
            'error_message': 'No signals detected'
        }
    
    def _create_error_backtest_result(
        self, 
        candles: List[CandleData], 
        params: StrategyParams, 
        start_time: datetime, 
        error_message: str
    ) -> Dict[str, Any]:
        """Create error backtest result when execution fails."""
        return {
            'candles': candles,
            'trades': [],
            'statistics': self._calculate_statistics([], params.initial_capital),
            'final_capital': params.initial_capital,
            'execution_time': (datetime.now() - start_time).total_seconds(),
            'data_period': {
                'start': candles[0].timestamp if candles else None,
                'end': candles[-1].timestamp if candles else None
            },
            'success': False,
            'parameters': params.dict(),
            'error_message': error_message
        }
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get information about the strategy."""
        return {
            'name': 'Hybrid Adaptive Strategy',
            'description': 'Combines volume analysis, price analysis, and risk management',
            'components': [
                'VolumeAnalyzer',
                'PriceAnalyzer', 
                'RiskManager',
                'SignalCombiner'
            ],
            'config': self.config
        }
