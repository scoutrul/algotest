"""
Order Book models for storing liquidity snapshots and historical data.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Index, UniqueConstraint, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
import json
from decimal import Decimal

from .database import Base


class OrderBookSnapshot(Base):
    """Model for storing Order Book snapshots with liquidity data."""
    __tablename__ = "order_book_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50), nullable=False, default="binance")
    timestamp = Column(Integer, nullable=False, index=True)
    
    # Best bid/ask prices and spread
    best_bid = Column(Float, nullable=True)
    best_ask = Column(Float, nullable=True)
    spread = Column(Float, nullable=True)
    spread_percentage = Column(Float, nullable=True)
    
    # Total volumes
    total_bid_volume = Column(Float, nullable=False, default=0.0)
    total_ask_volume = Column(Float, nullable=False, default=0.0)
    total_volume = Column(Float, nullable=False, default=0.0)
    
    # Liquidity depth metrics
    bid_levels_count = Column(Integer, nullable=False, default=0)
    ask_levels_count = Column(Integer, nullable=False, default=0)
    
    # JSON data for bid/ask levels
    # Format: [{"price": 100.5, "volume": 1.2}, ...]
    bid_levels = Column(JSON, nullable=False)
    ask_levels = Column(JSON, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=func.now())
    collection_latency_ms = Column(Integer, nullable=True)  # Time to collect data
    
    # Composite indexes for efficient queries
    __table_args__ = (
        UniqueConstraint('symbol', 'exchange', 'timestamp', name='unique_symbol_exchange_timestamp'),
        Index('ix_orderbook_symbol_timestamp', 'symbol', 'timestamp'),
        Index('ix_orderbook_symbol_exchange', 'symbol', 'exchange'),
        Index('ix_orderbook_created_at', 'created_at'),
    )

    def get_datetime_utc(self):
        """Convert timestamp to datetime object."""
        return datetime.utcfromtimestamp(self.timestamp / 1000)

    def calculate_metrics(self):
        """Calculate and update derived metrics."""
        if self.best_bid and self.best_ask:
            self.spread = self.best_ask - self.best_bid
            self.spread_percentage = (self.spread / self.best_ask) * 100 if self.best_ask > 0 else 0
        
        self.total_volume = self.total_bid_volume + self.total_ask_volume
        self.bid_levels_count = len(self.bid_levels) if self.bid_levels else 0
        self.ask_levels_count = len(self.ask_levels) if self.ask_levels else 0

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'exchange': self.exchange,
            'timestamp': self.timestamp,
            'datetime': self.get_datetime_utc().isoformat() if self.timestamp else None,
            'best_bid': self.best_bid,
            'best_ask': self.best_ask,
            'spread': self.spread,
            'spread_percentage': self.spread_percentage,
            'total_bid_volume': self.total_bid_volume,
            'total_ask_volume': self.total_ask_volume,
            'total_volume': self.total_volume,
            'bid_levels_count': self.bid_levels_count,
            'ask_levels_count': self.ask_levels_count,
            'bid_levels': self.bid_levels,
            'ask_levels': self.ask_levels,
            'collection_latency_ms': self.collection_latency_ms
        }

    @classmethod
    def from_ccxt_orderbook(cls, symbol, exchange_name, orderbook_data, collection_start_time=None):
        """Create OrderBookSnapshot from CCXT orderbook data."""
        timestamp = orderbook_data.get('timestamp') or int(datetime.now().timestamp() * 1000)
        
        # Extract bid/ask data
        bids = orderbook_data.get('bids', [])
        asks = orderbook_data.get('asks', [])
        
        # Calculate metrics
        best_bid = bids[0][0] if bids else None
        best_ask = asks[0][0] if asks else None
        
        total_bid_volume = sum(level[1] for level in bids)
        total_ask_volume = sum(level[1] for level in asks)
        
        # Convert to our format
        bid_levels = [{'price': price, 'volume': volume} for price, volume in bids]
        ask_levels = [{'price': price, 'volume': volume} for price, volume in asks]
        
        # Calculate collection latency
        collection_latency_ms = None
        if collection_start_time:
            collection_latency_ms = int((datetime.now().timestamp() - collection_start_time) * 1000)
        
        # Create instance
        snapshot = cls(
            symbol=symbol,
            exchange=exchange_name,
            timestamp=timestamp,
            best_bid=best_bid,
            best_ask=best_ask,
            total_bid_volume=total_bid_volume,
            total_ask_volume=total_ask_volume,
            bid_levels=bid_levels,
            ask_levels=ask_levels,
            collection_latency_ms=collection_latency_ms
        )
        
        # Calculate derived metrics
        snapshot.calculate_metrics()
        
        return snapshot

    def __repr__(self):
        return (f"<OrderBookSnapshot(symbol='{self.symbol}', exchange='{self.exchange}', "
                f"timestamp={self.timestamp}, spread={self.spread})>")


class LiquidityAggregation(Base):
    """Model for storing aggregated liquidity data over time intervals."""
    __tablename__ = "liquidity_aggregations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50), nullable=False, default="binance")
    interval = Column(String(10), nullable=False, index=True)  # 5m, 15m, 1h, 4h, 1d
    timestamp = Column(Integer, nullable=False, index=True)  # Start of interval
    
    # Aggregated metrics
    avg_spread = Column(Float, nullable=True)
    min_spread = Column(Float, nullable=True)
    max_spread = Column(Float, nullable=True)
    avg_total_volume = Column(Float, nullable=True)
    max_total_volume = Column(Float, nullable=True)
    
    # Liquidity depth evolution
    avg_bid_levels = Column(Float, nullable=True)
    avg_ask_levels = Column(Float, nullable=True)
    
    # Sample count for this aggregation
    snapshots_count = Column(Integer, nullable=False, default=0)
    
    created_at = Column(DateTime, nullable=False, default=func.now())
    
    __table_args__ = (
        UniqueConstraint('symbol', 'exchange', 'interval', 'timestamp', 
                        name='unique_symbol_exchange_interval_timestamp'),
        Index('ix_liquidity_agg_symbol_interval_timestamp', 'symbol', 'interval', 'timestamp'),
    )

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'symbol': self.symbol,
            'exchange': self.exchange,
            'interval': self.interval,
            'timestamp': self.timestamp,
            'datetime': datetime.utcfromtimestamp(self.timestamp / 1000).isoformat(),
            'avg_spread': self.avg_spread,
            'min_spread': self.min_spread,
            'max_spread': self.max_spread,
            'avg_total_volume': self.avg_total_volume,
            'max_total_volume': self.max_total_volume,
            'avg_bid_levels': self.avg_bid_levels,
            'avg_ask_levels': self.avg_ask_levels,
            'snapshots_count': self.snapshots_count
        }

    def __repr__(self):
        return (f"<LiquidityAggregation(symbol='{self.symbol}', interval='{self.interval}', "
                f"timestamp={self.timestamp})>")
