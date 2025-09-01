"""
Price analysis module for detecting price-based trading signals.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from ...models.backtest import CandleData

logger = logging.getLogger(__name__)

class PriceAnalyzer:
    """Analyzes price patterns to detect trading signals."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize price analyzer.
        
        Args:
            config: Configuration parameters
        """
        self.config = config
        self.min_price_change = config.get('min_price_change', 0.005)
        self.short_period = config.get('short_period', 5)
        self.long_period = config.get('long_period', 20)
        self.momentum_period = config.get('momentum_period', 10)
    
    def analyze(self, candles: List[CandleData], params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze price patterns and detect signals.
        
        Args:
            candles: List of candle data
            params: Strategy parameters
            
        Returns:
            List of price signals
        """
        try:
            if len(candles) < self.long_period + 1:
                logger.warning(f"Insufficient data for price analysis: {len(candles)} candles")
                return []
            
            # Convert to DataFrame for easier analysis
            df = self._candles_to_dataframe(candles)
            
            # Calculate price metrics
            df = self._calculate_price_metrics(df, params)
            
            # Detect price signals
            signals = self._detect_price_signals(df, params)
            
            logger.info(f"Price analysis completed: {len(signals)} signals detected")
            return signals
            
        except Exception as e:
            logger.error(f"Error in price analysis: {e}")
            return []
    
    def _candles_to_dataframe(self, candles: List[CandleData]) -> pd.DataFrame:
        """Convert candle data to pandas DataFrame."""
        data = []
        for candle in candles:
            data.append({
                'timestamp': candle.timestamp,
                'open': candle.open,
                'high': candle.high,
                'low': candle.low,
                'close': candle.close,
                'volume': candle.volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df
    
    def _calculate_price_metrics(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """Calculate price-based technical indicators."""
        
        # Price changes
        df['price_change'] = df['close'] - df['open']
        df['price_change_pct'] = df['price_change'] / df['open']
        df['high_low_range'] = df['high'] - df['low']
        df['close_change_pct'] = df['close'].pct_change()
        
        # Moving averages
        df['sma_short'] = df['close'].rolling(window=self.short_period).mean()
        df['sma_long'] = df['close'].rolling(window=self.long_period).mean()
        df['ema_short'] = df['close'].ewm(span=self.short_period).mean()
        df['ema_long'] = df['close'].ewm(span=self.long_period).mean()
        
        # Trend indicators
        df['trend_short'] = df['close'] - df['sma_short']
        df['trend_long'] = df['close'] - df['sma_long']
        df['trend_direction'] = np.where(df['trend_short'] > 0, 1, -1)
        
        # Momentum indicators
        df['momentum'] = df['close'] / df['close'].shift(self.momentum_period) - 1
        df['momentum_ma'] = df['momentum'].rolling(window=5).mean()
        
        # Volatility indicators
        df['volatility'] = df['close_change_pct'].rolling(window=self.long_period).std()
        df['atr'] = self._calculate_atr(df, 14)  # Average True Range
        
        # Support and resistance levels
        df['resistance'] = df['high'].rolling(window=self.long_period).max()
        df['support'] = df['low'].rolling(window=self.long_period).min()
        
        # Price position within range
        df['price_position'] = (df['close'] - df['support']) / (df['resistance'] - df['support'])
        
        # Breakout detection
        df['breakout_up'] = df['close'] > df['resistance'].shift(1)
        df['breakout_down'] = df['close'] < df['support'].shift(1)
        
        # Price action patterns
        df['doji'] = abs(df['close'] - df['open']) < (df['high'] - df['low']) * 0.1
        df['hammer'] = self._detect_hammer_pattern(df)
        df['shooting_star'] = self._detect_shooting_star_pattern(df)
        
        return df
    
    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Average True Range."""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    def _detect_hammer_pattern(self, df: pd.DataFrame) -> pd.Series:
        """Detect hammer candlestick pattern."""
        body = abs(df['close'] - df['open'])
        lower_shadow = df[['open', 'close']].min(axis=1) - df['low']
        upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
        total_range = df['high'] - df['low']
        
        # Hammer: small body, long lower shadow, small upper shadow
        hammer = (
            (body < total_range * 0.3) &
            (lower_shadow > body * 2) &
            (upper_shadow < body * 0.5)
        )
        
        return hammer
    
    def _detect_shooting_star_pattern(self, df: pd.DataFrame) -> pd.Series:
        """Detect shooting star candlestick pattern."""
        body = abs(df['close'] - df['open'])
        lower_shadow = df[['open', 'close']].min(axis=1) - df['low']
        upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
        total_range = df['high'] - df['low']
        
        # Shooting star: small body, long upper shadow, small lower shadow
        shooting_star = (
            (body < total_range * 0.3) &
            (upper_shadow > body * 2) &
            (lower_shadow < body * 0.5)
        )
        
        return shooting_star
    
    def _detect_price_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect price-based trading signals."""
        signals = []
        
        for i in range(self.long_period, len(df)):
            current = df.iloc[i]
            previous = df.iloc[i-1]
            
            # Check for significant price movement
            price_change_pct = abs(current['price_change_pct'])
            
            if price_change_pct >= self.min_price_change:
                # Analyze price direction and strength
                price_analysis = self._analyze_price_movement(df, i, params)
                
                if price_analysis['signal_detected']:
                    signal = {
                        'timestamp': current.name,
                        'type': 'price_movement',
                        'direction': price_analysis['direction'],
                        'strength': price_analysis['strength'],
                        'price_change_pct': current['price_change_pct'],
                        'momentum': current['momentum'],
                        'confidence': price_analysis['confidence'],
                        'metadata': {
                            'close': current['close'],
                            'trend_short': current['trend_short'],
                            'trend_long': current['trend_long'],
                            'volatility': current['volatility'],
                            'atr': current['atr'],
                            'price_position': current['price_position']
                        }
                    }
                    signals.append(signal)
        
        return signals
    
    def _analyze_price_movement(self, df: pd.DataFrame, index: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze price movement for signal detection."""
        current = df.iloc[index]
        
        # Determine direction
        direction = 'long' if current['price_change_pct'] > 0 else 'short'
        
        # Calculate signal strength
        strength = 0.0
        confidence = 0.0
        
        # Price change strength
        price_change_pct = abs(current['price_change_pct'])
        if price_change_pct > 0.02:  # 2%
            strength += 0.4
        elif price_change_pct > 0.01:  # 1%
            strength += 0.3
        elif price_change_pct > 0.005:  # 0.5%
            strength += 0.2
        
        # Trend confirmation
        if direction == 'long' and current['trend_short'] > 0:
            strength += 0.2
            confidence += 0.2
        elif direction == 'short' and current['trend_short'] < 0:
            strength += 0.2
            confidence += 0.2
        
        # Long-term trend alignment
        if direction == 'long' and current['trend_long'] > 0:
            strength += 0.1
            confidence += 0.1
        elif direction == 'short' and current['trend_long'] < 0:
            strength += 0.1
            confidence += 0.1
        
        # Momentum confirmation
        if direction == 'long' and current['momentum'] > 0:
            strength += 0.1
        elif direction == 'short' and current['momentum'] < 0:
            strength += 0.1
        
        # Breakout confirmation
        if current['breakout_up'] and direction == 'long':
            strength += 0.2
            confidence += 0.2
        elif current['breakout_down'] and direction == 'short':
            strength += 0.2
            confidence += 0.2
        
        # Price position in range
        if current['price_position'] > 0.8 and direction == 'long':
            strength += 0.1  # Near resistance, potential breakout
        elif current['price_position'] < 0.2 and direction == 'short':
            strength += 0.1  # Near support, potential breakdown
        
        # Volatility check (avoid signals in low volatility)
        if current['volatility'] < 0.01:  # Very low volatility
            strength -= 0.2
        
        return {
            'signal_detected': strength > 0.3,
            'direction': direction,
            'strength': min(strength, 1.0),
            'confidence': min(confidence, 1.0)
        }
    
    def get_price_statistics(self, candles: List[CandleData]) -> Dict[str, Any]:
        """Get price statistics for the given candles."""
        if not candles:
            return {}
        
        df = self._candles_to_dataframe(candles)
        df = self._calculate_price_metrics(df, self.config)
        
        return {
            'avg_price': df['close'].mean(),
            'max_price': df['close'].max(),
            'min_price': df['close'].min(),
            'price_volatility': df['close_change_pct'].std(),
            'avg_price_change_pct': df['price_change_pct'].mean(),
            'max_price_change_pct': df['price_change_pct'].max(),
            'min_price_change_pct': df['price_change_pct'].min(),
            'avg_momentum': df['momentum'].mean(),
            'trend_direction': df['trend_direction'].iloc[-1] if len(df) > 0 else 0
        }
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get analyzer information.
        
        Returns:
            Dictionary with analyzer details
        """
        return {
            'name': 'Price Analyzer',
            'description': 'Analyzes price patterns, trends, and momentum',
            'version': '1.0.0',
            'features': [
                'Multi-timeframe trend analysis',
                'Momentum calculation',
                'Volatility measurement',
                'Technical indicator integration'
            ],
            'config': self.config
        }
