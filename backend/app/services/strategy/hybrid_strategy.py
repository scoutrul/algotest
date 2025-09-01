"""
Main strategy service implementing the Hybrid Adaptive Strategy.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .volume_analyzer import VolumeAnalyzer
from .price_analyzer import PriceAnalyzer
from .risk_manager import RiskManager
from .signal_combiner import SignalCombiner
from ...models.backtest import CandleData, Trade, TradeDirection, ExitReason
from ...models.strategy import StrategyParams

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
            params_dict = params.model_dump()
            
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
            logger.info(f"Detected {len(signals)} signals")
            
            # Execute trades based on signals
            trades = self._execute_trades(signals, candles, params)
            logger.info(f"Executed {len(trades)} trades")
            
            # Calculate statistics
            statistics = self._calculate_statistics(trades, params.initial_capital)
            logger.info("Statistics calculated")
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'signals': signals,
                'trades': trades,
                'statistics': statistics,
                'execution_time': execution_time,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error in backtest execution: {e}")
            return {
                'signals': [],
                'trades': [],
                'statistics': {},
                'execution_time': 0,
                'success': False,
                'error': str(e)
            }
    
    def _execute_trades(self, signals: List[Dict[str, Any]], candles: List[CandleData], params: StrategyParams) -> List[Trade]:
        """
        Execute trades based on detected signals.
        
        Args:
            signals: List of trading signals
            candles: Historical candle data
            params: Strategy parameters
            
        Returns:
            List of executed trades
        """
        trades = []
        current_position = None
        
        for i, signal in enumerate(signals):
            if i >= len(candles) - 1:
                break
                
            candle = candles[i]
            next_candle = candles[i + 1]
            
            # Entry signal
            if signal['action'] == 'entry' and current_position is None:
                current_position = Trade(
                    id=len(trades) + 1,
                    entry_time=candle.timestamp,
                    entry_price=candle.close,
                    direction=signal['direction'],
                    volume=params.position_size,
                    status='open'
                )
                trades.append(current_position)
                logger.info(f"Opened {signal['direction']} position at {candle.close}")
            
            # Exit signal or TP/SL
            elif current_position is not None:
                exit_price = next_candle.close
                exit_time = next_candle.timestamp
                exit_reason = 'take_profit'
                
                # Check stop loss
                if current_position.direction == TradeDirection.LONG:
                    if exit_price <= current_position.entry_price * (1 - params.stop_loss):
                        exit_reason = 'stop_loss'
                else:
                    if exit_price >= current_position.entry_price * (1 + params.stop_loss):
                        exit_reason = 'stop_loss'
                
                # Check take profit
                if current_position.direction == TradeDirection.LONG:
                    if exit_price >= current_position.entry_price * (1 + params.take_profit):
                        exit_reason = 'take_profit'
                else:
                    if exit_price <= current_position.entry_price * (1 - params.take_profit):
                        exit_reason = 'take_profit'
                
                # Close position
                current_position.exit_time = exit_time
                current_position.exit_price = exit_price
                current_position.exit_reason = ExitReason(exit_reason)
                current_position.status = 'closed'
                
                # Calculate PnL
                if current_position.direction == TradeDirection.LONG:
                    current_position.pnl = (exit_price - current_position.entry_price) * current_position.volume
                else:
                    current_position.pnl = (current_position.entry_price - exit_price) * current_position.volume
                
                logger.info(f"Closed position: {exit_reason} at {exit_price}, PnL: {current_position.pnl}")
                current_position = None
        
        # Close any remaining open position
        if current_position is not None:
            last_candle = candles[-1]
            current_position.exit_time = last_candle.timestamp
            current_position.exit_price = last_candle.close
            current_position.exit_reason = ExitReason('end_of_data')
            current_position.status = 'closed'
            
            # Calculate PnL
            if current_position.direction == TradeDirection.LONG:
                current_position.pnl = (last_candle.close - current_position.entry_price) * current_position.volume
            else:
                current_position.pnl = (current_position.entry_price - last_candle.close) * current_position.volume
        
        return trades
    
    def _calculate_statistics(self, trades: List[Trade], initial_capital: float) -> Dict[str, Any]:
        """
        Calculate backtest statistics.
        
        Args:
            trades: List of executed trades
            initial_capital: Initial capital amount
            
        Returns:
            Dictionary with statistics
        """
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'total_return': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0
            }
        
        # Basic counts
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.pnl > 0])
        losing_trades = len([t for t in trades if t.pnl < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        # PnL calculations
        total_pnl = sum(t.pnl for t in trades)
        total_return = total_pnl / initial_capital if initial_capital > 0 else 0.0
        
        # Calculate max drawdown
        cumulative_pnl = 0
        peak = 0
        max_drawdown = 0
        
        for trade in trades:
            cumulative_pnl += trade.pnl
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            drawdown = peak - cumulative_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Calculate Sharpe ratio (simplified)
        if len(trades) > 1:
            returns = [t.pnl / initial_capital for t in trades]
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = avg_return / std_return if std_return > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'avg_win': np.mean([t.pnl for t in trades if t.pnl > 0]) if winning_trades > 0 else 0.0,
            'avg_loss': np.mean([t.pnl for t in trades if t.pnl < 0]) if losing_trades > 0 else 0.0,
            'profit_factor': abs(sum(t.pnl for t in trades if t.pnl > 0) / sum(t.pnl for t in trades if t.pnl < 0)) if losing_trades > 0 else float('inf'),
            'avg_trade_duration': np.mean([(t.exit_time - t.entry_time).total_seconds() / 60 for t in trades if t.exit_time]) if any(t.exit_time for t in trades) else 0.0
        }
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get strategy information.
        
        Returns:
            Dictionary with strategy details
        """
        return {
            'name': 'Hybrid Adaptive Strategy',
            'description': 'Combines volume analysis, price analysis, and risk management',
            'components': {
                'volume_analyzer': self.volume_analyzer.get_info(),
                'price_analyzer': self.price_analyzer.get_info(),
                'risk_manager': self.risk_manager.get_info(),
                'signal_combiner': self.signal_combiner.get_info()
            },
            'config': self.config
        }
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """
        Get detailed strategy information for API endpoint.
        
        Returns:
            Dictionary with strategy details
        """
        return {
            'name': 'Hybrid Adaptive Strategy',
            'description': 'Advanced trading strategy combining multiple analytical modules',
            'version': '1.0.0',
            'components': {
                'volume_analyzer': self.volume_analyzer.get_info(),
                'price_analyzer': self.price_analyzer.get_info(),
                'risk_manager': self.risk_manager.get_info(),
                'signal_combiner': self.signal_combiner.get_info()
            },
            'config': self.config,
            'features': [
                'Adaptive volume threshold detection',
                'Multi-timeframe price analysis',
                'Dynamic risk management',
                'Signal quality scoring',
                'Position sizing optimization'
            ]
        }
