"""
Signal combiner module for combining multiple signal sources.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from ...models.backtest import CandleData

logger = logging.getLogger(__name__)

class SignalCombiner:
    """Combines signals from multiple sources with weighted scoring."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize signal combiner.
        
        Args:
            config: Configuration parameters
        """
        self.config = config
        self.volume_weight = config.get('volume_weight', 0.4)
        self.price_weight = config.get('price_weight', 0.4)
        self.momentum_weight = config.get('momentum_weight', 0.2)
        self.min_combined_score = config.get('min_combined_score', 0.5)
        self.signal_timeout = config.get('signal_timeout', 300)  # 5 minutes
    
    def combine_signals(
        self, 
        volume_signals: List[Dict[str, Any]], 
        price_signals: List[Dict[str, Any]], 
        candles: List[CandleData]
    ) -> List[Dict[str, Any]]:
        """
        Combine volume and price signals into final trading signals.
        
        Args:
            volume_signals: List of volume-based signals
            price_signals: List of price-based signals
            candles: Historical candle data
            
        Returns:
            List of combined trading signals
        """
        try:
            if not volume_signals and not price_signals:
                return []
            
            # Convert signals to DataFrame for easier processing
            volume_df = self._signals_to_dataframe(volume_signals, 'volume')
            price_df = self._signals_to_dataframe(price_signals, 'price')
            
            # Combine signals by timestamp
            combined_signals = self._combine_by_timestamp(volume_df, price_df, candles)
            
            # Filter and score combined signals
            final_signals = self._filter_and_score_signals(combined_signals)
            
            logger.info(f"Signal combination completed: {len(final_signals)} final signals")
            return final_signals
            
        except Exception as e:
            logger.error(f"Error combining signals: {e}")
            return []
    
    def _signals_to_dataframe(self, signals: List[Dict[str, Any]], signal_type: str) -> pd.DataFrame:
        """Convert signals to DataFrame for processing."""
        if not signals:
            return pd.DataFrame()
        
        data = []
        for signal in signals:
            data.append({
                'timestamp': signal['timestamp'],
                'type': signal_type,
                'strength': signal.get('strength', 0),
                'confidence': signal.get('confidence', 0),
                'direction': signal.get('direction', 'unknown'),
                'metadata': signal.get('metadata', {}),
                'original_signal': signal
            })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df.set_index('timestamp', inplace=True)
        
        return df
    
    def _combine_by_timestamp(
        self, 
        volume_df: pd.DataFrame, 
        price_df: pd.DataFrame, 
        candles: List[CandleData]
    ) -> List[Dict[str, Any]]:
        """Combine signals by timestamp proximity."""
        combined_signals = []
        
        # Get all unique timestamps
        all_timestamps = set()
        if not volume_df.empty:
            all_timestamps.update(volume_df.index)
        if not price_df.empty:
            all_timestamps.update(price_df.index)
        
        if not all_timestamps:
            return combined_signals
        
        # Sort timestamps
        sorted_timestamps = sorted(all_timestamps)
        
        for timestamp in sorted_timestamps:
            # Find signals within time window
            time_window = timedelta(seconds=self.signal_timeout)
            
            # Get volume signals in time window
            volume_signals_in_window = []
            if not volume_df.empty:
                volume_mask = (volume_df.index >= timestamp - time_window) & (volume_df.index <= timestamp + time_window)
                volume_signals_in_window = volume_df[volume_mask].to_dict('records')
            
            # Get price signals in time window
            price_signals_in_window = []
            if not price_df.empty:
                price_mask = (price_df.index >= timestamp - time_window) & (price_df.index <= timestamp + time_window)
                price_signals_in_window = price_df[price_mask].to_dict('records')
            
            # Combine signals in this time window
            if volume_signals_in_window or price_signals_in_window:
                combined_signal = self._create_combined_signal(
                    timestamp, 
                    volume_signals_in_window, 
                    price_signals_in_window,
                    candles
                )
                
                if combined_signal:
                    combined_signals.append(combined_signal)
        
        return combined_signals
    
    def _create_combined_signal(
        self, 
        timestamp: datetime, 
        volume_signals: List[Dict[str, Any]], 
        price_signals: List[Dict[str, Any]],
        candles: List[CandleData]
    ) -> Optional[Dict[str, Any]]:
        """Create a combined signal from volume and price signals."""
        try:
            # Calculate combined scores
            volume_score = self._calculate_volume_score(volume_signals)
            price_score = self._calculate_price_score(price_signals)
            momentum_score = self._calculate_momentum_score(timestamp, candles)
            
            # Calculate weighted combined score
            combined_score = (
                volume_score * self.volume_weight +
                price_score * self.price_weight +
                momentum_score * self.momentum_weight
            )
            
            # Determine signal direction
            direction = self._determine_signal_direction(volume_signals, price_signals)
            
            # Calculate confidence
            confidence = self._calculate_combined_confidence(volume_signals, price_signals)
            
            # Create combined signal
            combined_signal = {
                'timestamp': timestamp,
                'type': 'combined',
                'direction': direction,
                'strength': combined_score,
                'confidence': confidence,
                'volume_score': volume_score,
                'price_score': price_score,
                'momentum_score': momentum_score,
                'metadata': {
                    'volume_signals_count': len(volume_signals),
                    'price_signals_count': len(price_signals),
                    'volume_weight': self.volume_weight,
                    'price_weight': self.price_weight,
                    'momentum_weight': self.momentum_weight
                }
            }
            
            return combined_signal
            
        except Exception as e:
            logger.error(f"Error creating combined signal: {e}")
            return None
    
    def _calculate_volume_score(self, volume_signals: List[Dict[str, Any]]) -> float:
        """Calculate combined volume signal score."""
        if not volume_signals:
            return 0.0
        
        # Average strength of volume signals
        avg_strength = np.mean([s.get('strength', 0) for s in volume_signals])
        
        # Boost score for multiple volume signals
        count_boost = min(len(volume_signals) * 0.1, 0.3)
        
        return min(avg_strength + count_boost, 1.0)
    
    def _calculate_price_score(self, price_signals: List[Dict[str, Any]]) -> float:
        """Calculate combined price signal score."""
        if not price_signals:
            return 0.0
        
        # Average strength of price signals
        avg_strength = np.mean([s.get('strength', 0) for s in price_signals])
        
        # Boost score for multiple price signals
        count_boost = min(len(price_signals) * 0.1, 0.3)
        
        return min(avg_strength + count_boost, 1.0)
    
    def _calculate_momentum_score(self, timestamp: datetime, candles: List[CandleData]) -> float:
        """Calculate momentum score based on recent price action."""
        try:
            # Find candle closest to timestamp
            closest_candle = None
            min_diff = float('inf')
            
            for candle in candles:
                diff = abs((candle.timestamp - timestamp).total_seconds())
                if diff < min_diff:
                    min_diff = diff
                    closest_candle = candle
            
            if not closest_candle:
                return 0.0
            
            # Calculate momentum based on price change
            price_change_pct = (closest_candle.close - closest_candle.open) / closest_candle.open
            
            # Convert to score (0-1)
            momentum_score = min(abs(price_change_pct) * 10, 1.0)
            
            return momentum_score
            
        except Exception as e:
            logger.error(f"Error calculating momentum score: {e}")
            return 0.0
    
    def _determine_signal_direction(self, volume_signals: List[Dict[str, Any]], price_signals: List[Dict[str, Any]]) -> str:
        """Determine the overall signal direction."""
        directions = []
        
        # Collect directions from volume signals
        for signal in volume_signals:
            if 'direction' in signal:
                directions.append(signal['direction'])
        
        # Collect directions from price signals
        for signal in price_signals:
            if 'direction' in signal:
                directions.append(signal['direction'])
        
        if not directions:
            return 'unknown'
        
        # Count directions
        long_count = directions.count('long')
        short_count = directions.count('short')
        
        # Return majority direction
        if long_count > short_count:
            return 'long'
        elif short_count > long_count:
            return 'short'
        else:
            # If tied, return the direction of the strongest signal
            all_signals = volume_signals + price_signals
            if all_signals:
                strongest_signal = max(all_signals, key=lambda s: s.get('strength', 0))
                return strongest_signal.get('direction', 'unknown')
            return 'unknown'
    
    def _calculate_combined_confidence(self, volume_signals: List[Dict[str, Any]], price_signals: List[Dict[str, Any]]) -> float:
        """Calculate combined confidence score."""
        confidences = []
        
        # Collect confidences from volume signals
        for signal in volume_signals:
            if 'confidence' in signal:
                confidences.append(signal['confidence'])
        
        # Collect confidences from price signals
        for signal in price_signals:
            if 'confidence' in signal:
                confidences.append(signal['confidence'])
        
        if not confidences:
            return 0.0
        
        # Average confidence with boost for multiple signals
        avg_confidence = np.mean(confidences)
        count_boost = min(len(confidences) * 0.05, 0.2)
        
        return min(avg_confidence + count_boost, 1.0)
    
    def _filter_and_score_signals(self, combined_signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter and score combined signals."""
        filtered_signals = []
        
        for signal in combined_signals:
            # Apply minimum score filter
            if signal['strength'] >= self.min_combined_score:
                # Add final quality score
                signal['quality_score'] = self._calculate_final_quality_score(signal)
                filtered_signals.append(signal)
        
        # Sort by quality score (highest first)
        filtered_signals.sort(key=lambda s: s['quality_score'], reverse=True)
        
        return filtered_signals
    
    def _calculate_final_quality_score(self, signal: Dict[str, Any]) -> float:
        """Calculate final quality score for a combined signal."""
        try:
            quality_score = 0.0
            
            # Base score from combined strength
            quality_score += signal.get('strength', 0) * 0.4
            
            # Confidence score
            quality_score += signal.get('confidence', 0) * 0.3
            
            # Signal alignment bonus
            volume_score = signal.get('volume_score', 0)
            price_score = signal.get('price_score', 0)
            
            # Bonus for aligned signals
            if volume_score > 0.5 and price_score > 0.5:
                quality_score += 0.2
            elif volume_score > 0.3 and price_score > 0.3:
                quality_score += 0.1
            
            # Momentum bonus
            momentum_score = signal.get('momentum_score', 0)
            if momentum_score > 0.5:
                quality_score += 0.1
            
            return min(quality_score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating final quality score: {e}")
            return 0.0
    
    def get_signal_statistics(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about the combined signals."""
        if not signals:
            return {}
        
        try:
            directions = [s.get('direction', 'unknown') for s in signals]
            strengths = [s.get('strength', 0) for s in signals]
            confidences = [s.get('confidence', 0) for s in signals]
            
            return {
                'total_signals': len(signals),
                'long_signals': directions.count('long'),
                'short_signals': directions.count('short'),
                'avg_strength': np.mean(strengths),
                'max_strength': np.max(strengths),
                'min_strength': np.min(strengths),
                'avg_confidence': np.mean(confidences),
                'max_confidence': np.max(confidences),
                'min_confidence': np.min(confidences)
            }
            
        except Exception as e:
            logger.error(f"Error calculating signal statistics: {e}")
            return {}
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get signal combiner information.
        
        Returns:
            Dictionary with signal combiner details
        """
        return {
            'name': 'Signal Combiner',
            'description': 'Combines and weights signals from multiple analyzers',
            'version': '1.0.0',
            'features': [
                'Multi-analyzer signal combination',
                'Weighted signal scoring',
                'Signal quality assessment',
                'Confidence calculation',
                'Signal filtering'
            ],
            'config': self.config
        }
