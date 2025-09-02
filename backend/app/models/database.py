"""
Database models for the BackTest Trading Bot.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Candle(Base):
    """Model for storing OHLCV candle data."""
    __tablename__ = "candles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    interval = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)

    # Composite indexes for efficient queries
    __table_args__ = (
        UniqueConstraint('symbol', 'interval', 'timestamp', name='unique_symbol_interval_timestamp'),
        Index('ix_candles_symbol_interval_timestamp', 'symbol', 'interval', 'timestamp'),
        Index('ix_candles_symbol_interval', 'symbol', 'interval'),
    )

    def __repr__(self):
        return f"<Candle(symbol='{self.symbol}', interval='{self.interval}', timestamp='{self.timestamp}', close={self.close})>"


class MarketDataStatus(Base):
    """Model for tracking data synchronization status."""
    __tablename__ = "market_data_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    interval = Column(String(10), nullable=False)
    last_updated = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    oldest_timestamp = Column(DateTime, nullable=True)
    newest_timestamp = Column(DateTime, nullable=True)
    total_candles = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint('symbol', 'interval', name='unique_symbol_interval_status'),
        Index('ix_market_data_status_symbol_interval', 'symbol', 'interval'),
    )

    def __repr__(self):
        return f"<MarketDataStatus(symbol='{self.symbol}', interval='{self.interval}', total_candles={self.total_candles})>"

