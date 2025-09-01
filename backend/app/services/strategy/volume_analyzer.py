"""
Volume analysis module for detecting volume-based trading signals.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from ...models.backtest import CandleData

logger = logging.getLogger(__name__)

class VolumeAnalyzer:
    """Analyzes volume patterns to detect trading signals."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize volume analyzer.
        
        Args:
            config: Configuration parameters
        """
        self.config = config
        self.base_volume_threshold = config.get('volume_threshold', 1.5)
        self.lookback_period = config.get('lookback_period', 20)
        self.min_volume_change = config.get('min_volume_change', 0.1)
    
    def analyze(self, candles: List[CandleData], params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze volume patterns and detect signals.
        
        Args:
            candles: List of candle data
            params: Strategy parameters
            
        Returns:
            List of volume signals
        """
        try:
            if len(candles) < self.lookback_period + 1:
                logger.warning(f"Insufficient data for volume analysis: {len(candles)} candles")
                return []
            
            # Convert to DataFrame for easier analysis
            df = self._candles_to_dataframe(candles)
            
            # Calculate volume metrics
            df = self._calculate_volume_metrics(df, params)
            
            # Detect volume signals
            signals = self._detect_volume_signals(df, params)
            
            logger.info(f"Volume analysis completed: {len(signals)} signals detected")
            return signals
            
        except Exception as e:
            logger.error(f"Error in volume analysis: {e}")
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
    
    def _calculate_volume_metrics(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """Calculate volume-based technical indicators."""
        
        # Volume moving averages
        df['volume_sma'] = df['volume'].rolling(window=self.lookback_period).mean()
        df['volume_ema'] = df['volume'].ewm(span=self.lookback_period).mean()
        
        # Volume ratio (current volume / average volume)
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Volume change percentage
        df['volume_change_pct'] = df['volume'].pct_change()
        
        # Volume volatility (standard deviation)
        df['volume_volatility'] = df['volume'].rolling(window=self.lookback_period).std()
        
        # Volume momentum (rate of change)
        df['volume_momentum'] = df['volume'] / df['volume'].shift(self.lookback_period)
        
        # Adaptive volume threshold based on volatility
        volatility = df['volume_volatility'].rolling(window=self.lookback_period).mean()
        df['adaptive_threshold'] = self.base_volume_threshold * (1 + volatility / df['volume_sma'])
        
        # Volume spike detection
        df['volume_spike'] = df['volume_ratio'] > df['adaptive_threshold']
        
        # Volume trend (increasing/decreasing)
        df['volume_trend'] = df['volume'].rolling(window=5).apply(
            lambda x: 1 if x.iloc[-1] > x.iloc[0] else -1, raw=False
        )
        
        return df
    
    def _detect_volume_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect volume-based trading signals."""
        signals = []
        
        for i in range(self.lookback_period, len(df)):
            current = df.iloc[i]
            previous = df.iloc[i-1]
            
            # Check for volume spike
            if current['volume_spike']:
                # Additional volume confirmation
                volume_confirmation = self._check_volume_confirmation(df, i, params)
                
                if volume_confirmation['confirmed']:
                    signal = {
                        'timestamp': current.name,
                        'type': 'volume_spike',
                        'strength': volume_confirmation['strength'],
                        'volume_ratio': current['volume_ratio'],
                        'volume_change_pct': current['volume_change_pct'],
                        'volume_trend': current['volume_trend'],
                        'confidence': min(volume_confirmation['strength'], 1.0),
                        'metadata': {
                            'volume': current['volume'],
                            'volume_sma': current['volume_sma'],
                            'volume_volatility': current['volume_volatility'],
                            'adaptive_threshold': current['adaptive_threshold']
                        }
                    }
                    signals.append(signal)
        
        return signals
    
    def _check_volume_confirmation(self, df: pd.DataFrame, index: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check additional volume confirmation criteria."""
        current = df.iloc[index]
        
        # Base confirmation
        confirmed = True
        strength = 0.5
        
        # Volume ratio strength
        volume_ratio = current['volume_ratio']
        if volume_ratio > 2.0:
            strength += 0.3
        elif volume_ratio > 1.5:
            strength += 0.2
        elif volume_ratio > 1.2:
            strength += 0.1
        
        # Volume trend confirmation
        if current['volume_trend'] > 0:
            strength += 0.1
        
        # Volume change percentage
        volume_change = abs(current['volume_change_pct'])
        if volume_change > 0.5:
            strength += 0.2
        elif volume_change > 0.2:
            strength += 0.1
        
        # Check for consecutive volume spikes (stronger signal)
        consecutive_spikes = self._count_consecutive_volume_spikes(df, index)
        if consecutive_spikes > 1:
            strength += 0.1 * consecutive_spikes
        
        # Volume volatility check (avoid false signals in low volatility)
        if current['volume_volatility'] < current['volume_sma'] * 0.1:
            strength -= 0.2
            confirmed = False
        
        return {
            'confirmed': confirmed and strength > 0.3,
            'strength': min(strength, 1.0)
        }
    
    def _count_consecutive_volume_spikes(self, df: pd.DataFrame, index: int) -> int:
        """Count consecutive volume spikes."""
        count = 0
        for i in range(index, max(0, index - 5), -1):
            if df.iloc[i]['volume_spike']:
                count += 1
            else:
                break
        return count
    
    def get_volume_statistics(self, candles: List[CandleData]) -> Dict[str, Any]:
        """Get volume statistics for the given candles."""
        if not candles:
            return {}
        
        df = self._candles_to_dataframe(candles)
        df = self._calculate_volume_metrics(df, self.config)
        
        return {
            'avg_volume': df['volume'].mean(),
            'max_volume': df['volume'].max(),
            'min_volume': df['volume'].min(),
            'volume_volatility': df['volume'].std(),
            'volume_spikes': df['volume_spike'].sum(),
            'avg_volume_ratio': df['volume_ratio'].mean(),
            'max_volume_ratio': df['volume_ratio'].max()
        }
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get analyzer information.
        
        Returns:
            Dictionary with analyzer details
        """
        return {
            'name': 'Volume Analyzer',
            'description': 'Analyzes volume patterns and spikes for trading signals',
            'version': '1.0.0',
            'features': [
                'Adaptive volume threshold calculation',
                'Volume spike detection',
                'Volume ratio analysis',
                'Technical indicator integration'
            ],
            'config': self.config
        }
