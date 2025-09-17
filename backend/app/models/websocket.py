"""
WebSocket data models for live candle streaming.
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class KlineData(BaseModel):
    """Kline data structure for WebSocket messages."""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    isClosed: bool


class WebSocketMessage(BaseModel):
    """WebSocket message structure."""
    type: str
    data: Optional[KlineData] = None
    symbol: str
    interval: str
    timestamp: Optional[datetime] = None


class ConnectionInfo(BaseModel):
    """WebSocket connection information."""
    connection_id: str
    symbol: str
    interval: str
    connected_at: datetime
    last_activity: Optional[datetime] = None


class BinanceKlinePayload(BaseModel):
    """Binance WebSocket kline payload structure."""
    t: int  # open time
    o: str  # open price
    h: str  # high price
    l: str  # low price
    c: str  # close price
    v: str  # volume
    x: bool  # is closed


class BinanceWebSocketMessage(BaseModel):
    """Binance WebSocket message structure."""
    e: str  # event type
    E: int  # event time
    s: str  # symbol
    k: Optional[BinanceKlinePayload] = None
