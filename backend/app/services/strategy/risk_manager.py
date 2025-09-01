"""
Risk management module for position sizing and risk control.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from ...models.backtest import CandleData, Trade, TradeDirection

logger = logging.getLogger(__name__)

class RiskManager:
    """Manages risk through position sizing, stop loss, and take profit."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize risk manager.
        
        Args:
            config: Configuration parameters
        """
        self.config = config
        self.take_profit = config.get('take_profit', 0.02)
        self.stop_loss = config.get('stop_loss', 0.01)
        self.initial_capital = config.get('initial_capital', 10000)
        self.max_position_size = config.get('max_position_size', 0.1)  # 10% of capital
        self.risk_per_trade = config.get('risk_per_trade', 0.02)  # 2% risk per trade
    
    def filter_signals(self, signals: List[Dict[str, Any]], candles: List[CandleData]) -> List[Dict[str, Any]]:
        """
        Filter signals based on risk criteria.
        
        Args:
            signals: List of trading signals
            candles: Historical candle data
            
        Returns:
            Filtered list of signals with risk management applied
        """
        try:
            if not signals:
                return []
            
            filtered_signals = []
            
            for signal in signals:
                # Apply risk management to signal
                risk_managed_signal = self._apply_risk_management(signal, candles)
                
                if risk_managed_signal and self._validate_risk_criteria(risk_managed_signal):
                    filtered_signals.append(risk_managed_signal)
            
            logger.info(f"Risk management filtered {len(signals)} signals to {len(filtered_signals)}")
            return filtered_signals
            
        except Exception as e:
            logger.error(f"Error in risk management: {e}")
            return []
    
    def create_trade(self, signal: Dict[str, Any], current_candle: CandleData, available_capital: float) -> Optional[Trade]:
        """
        Create a trade from a signal with proper risk management.
        
        Args:
            signal: Trading signal
            current_candle: Current market data
            available_capital: Available capital for trading
            
        Returns:
            Trade object or None if trade cannot be created
        """
        try:
            # Calculate position size
            position_size = self._calculate_position_size(signal, current_candle, available_capital)
            
            if position_size <= 0:
                return None
            
            # Calculate entry price
            entry_price = current_candle.close
            
            # Calculate stop loss and take profit
            stop_loss_price = self._calculate_stop_loss(entry_price, signal['direction'])
            take_profit_price = self._calculate_take_profit(entry_price, signal['direction'])
            
            # Create trade
            trade = Trade(
                id=f"trade_{int(datetime.now().timestamp())}",
                entry_time=current_candle.timestamp,
                direction=TradeDirection.LONG if signal['direction'] == 'long' else TradeDirection.SHORT,
                entry_price=entry_price,
                size=position_size,
                take_profit=take_profit_price,
                stop_loss=stop_loss_price
            )
            
            logger.info(f"Created trade: {trade.direction} {trade.size} at {trade.entry_price}")
            return trade
            
        except Exception as e:
            logger.error(f"Error creating trade: {e}")
            return None
    
    def check_exit_conditions(self, trade: Trade, current_candle: CandleData) -> Optional[Dict[str, Any]]:
        """
        Check if trade should be exited based on current market conditions.
        
        Args:
            trade: Active trade
            current_candle: Current market data
            
        Returns:
            Exit information or None if trade should continue
        """
        try:
            current_price = current_candle.close
            
            # Check take profit
            if trade.direction == TradeDirection.LONG and current_price >= trade.take_profit:
                return {
                    'should_exit': True,
                    'exit_price': trade.take_profit,
                    'exit_reason': 'take_profit',
                    'pnl': self._calculate_pnl(trade, trade.take_profit)
                }
            
            if trade.direction == TradeDirection.SHORT and current_price <= trade.take_profit:
                return {
                    'should_exit': True,
                    'exit_price': trade.take_profit,
                    'exit_reason': 'take_profit',
                    'pnl': self._calculate_pnl(trade, trade.take_profit)
                }
            
            # Check stop loss
            if trade.direction == TradeDirection.LONG and current_price <= trade.stop_loss:
                return {
                    'should_exit': True,
                    'exit_price': trade.stop_loss,
                    'exit_reason': 'stop_loss',
                    'pnl': self._calculate_pnl(trade, trade.stop_loss)
                }
            
            if trade.direction == TradeDirection.SHORT and current_price >= trade.stop_loss:
                return {
                    'should_exit': True,
                    'exit_price': trade.stop_loss,
                    'exit_reason': 'stop_loss',
                    'pnl': self._calculate_pnl(trade, trade.stop_loss)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")
            return None
    
    def _apply_risk_management(self, signal: Dict[str, Any], candles: List[CandleData]) -> Optional[Dict[str, Any]]:
        """Apply risk management rules to a signal."""
        try:
            # Add risk management parameters to signal
            signal['take_profit_pct'] = self.take_profit
            signal['stop_loss_pct'] = self.stop_loss
            signal['max_position_size'] = self.max_position_size
            signal['risk_per_trade'] = self.risk_per_trade
            
            # Calculate signal quality score
            signal['quality_score'] = self._calculate_signal_quality(signal, candles)
            
            # Filter based on quality score
            if signal['quality_score'] < 0.3:
                return None
            
            return signal
            
        except Exception as e:
            logger.error(f"Error applying risk management: {e}")
            return None
    
    def _validate_risk_criteria(self, signal: Dict[str, Any]) -> bool:
        """Validate signal against risk criteria."""
        try:
            # Check minimum quality score
            if signal.get('quality_score', 0) < 0.3:
                return False
            
            # Check signal strength
            if signal.get('strength', 0) < 0.3:
                return False
            
            # Check confidence level
            if signal.get('confidence', 0) < 0.2:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating risk criteria: {e}")
            return False
    
    def _calculate_position_size(self, signal: Dict[str, Any], current_candle: CandleData, available_capital: float) -> float:
        """Calculate position size based on risk management rules."""
        try:
            # Base position size (percentage of available capital)
            base_size = available_capital * self.max_position_size
            
            # Adjust based on signal quality
            quality_multiplier = signal.get('quality_score', 0.5)
            adjusted_size = base_size * quality_multiplier
            
            # Adjust based on volatility (reduce size in high volatility)
            volatility_adjustment = self._calculate_volatility_adjustment(current_candle)
            final_size = adjusted_size * volatility_adjustment
            
            # Ensure minimum and maximum limits
            min_size = available_capital * 0.01  # 1% minimum
            max_size = available_capital * self.max_position_size
            
            return max(min_size, min(final_size, max_size))
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    def _calculate_stop_loss(self, entry_price: float, direction: str) -> float:
        """Calculate stop loss price."""
        if direction == 'long':
            return entry_price * (1 - self.stop_loss)
        else:
            return entry_price * (1 + self.stop_loss)
    
    def _calculate_take_profit(self, entry_price: float, direction: str) -> float:
        """Calculate take profit price."""
        if direction == 'long':
            return entry_price * (1 + self.take_profit)
        else:
            return entry_price * (1 - self.take_profit)
    
    def _calculate_pnl(self, trade: Trade, exit_price: float) -> float:
        """Calculate profit/loss for a trade."""
        if trade.direction == TradeDirection.LONG:
            return trade.size * (exit_price - trade.entry_price) / trade.entry_price
        else:
            return trade.size * (trade.entry_price - exit_price) / trade.entry_price
    
    def _calculate_signal_quality(self, signal: Dict[str, Any], candles: List[CandleData]) -> float:
        """Calculate overall signal quality score."""
        try:
            quality_score = 0.0
            
            # Base score from signal strength
            quality_score += signal.get('strength', 0) * 0.4
            
            # Confidence score
            quality_score += signal.get('confidence', 0) * 0.3
            
            # Volume confirmation
            if signal.get('type') == 'volume_spike':
                volume_ratio = signal.get('volume_ratio', 1.0)
                if volume_ratio > 2.0:
                    quality_score += 0.2
                elif volume_ratio > 1.5:
                    quality_score += 0.1
            
            # Price momentum
            momentum = signal.get('momentum', 0)
            if abs(momentum) > 0.01:
                quality_score += 0.1
            
            return min(quality_score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating signal quality: {e}")
            return 0.0
    
    def _calculate_volatility_adjustment(self, current_candle: CandleData) -> float:
        """Calculate volatility adjustment for position sizing."""
        try:
            # Simple volatility calculation based on high-low range
            price_range = (current_candle.high - current_candle.low) / current_candle.close
            
            # Reduce position size in high volatility
            if price_range > 0.05:  # 5% range
                return 0.5
            elif price_range > 0.03:  # 3% range
                return 0.7
            elif price_range > 0.02:  # 2% range
                return 0.8
            else:
                return 1.0
                
        except Exception as e:
            logger.error(f"Error calculating volatility adjustment: {e}")
            return 1.0
    
    def get_risk_metrics(self, trades: List[Trade]) -> Dict[str, Any]:
        """Calculate risk metrics for a set of trades."""
        if not trades:
            return {}
        
        try:
            # Calculate basic metrics
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t.pnl and t.pnl > 0])
            losing_trades = len([t for t in trades if t.pnl and t.pnl < 0])
            
            # Calculate PnL metrics
            total_pnl = sum(t.pnl for t in trades if t.pnl)
            avg_win = np.mean([t.pnl for t in trades if t.pnl and t.pnl > 0]) if winning_trades > 0 else 0
            avg_loss = np.mean([t.pnl for t in trades if t.pnl and t.pnl < 0]) if losing_trades > 0 else 0
            
            # Calculate drawdown
            cumulative_pnl = np.cumsum([t.pnl for t in trades if t.pnl])
            running_max = np.maximum.accumulate(cumulative_pnl)
            drawdown = running_max - cumulative_pnl
            max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
                'total_pnl': total_pnl,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0,
                'max_drawdown': max_drawdown
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return {}
