"""
Binance WebSocket client for live candle data streaming.
"""
import asyncio
import json
import logging
from typing import Dict, Set, Callable, Optional
from datetime import datetime
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from ..models.websocket import BinanceWebSocketMessage, KlineData, WebSocketMessage

logger = logging.getLogger(__name__)

class BinanceWebSocketClient:
    """Binance WebSocket client for streaming kline data."""
    
    BINANCE_WS_URL = "wss://stream.binance.com:9443/ws"
    
    def __init__(self):
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.subscribers: Dict[str, Set[Callable]] = {}
        self.running = False
        self.reconnect_tasks: Dict[str, asyncio.Task] = {}
        
    def _get_stream_name(self, symbol: str, interval: str) -> str:
        """Convert symbol and interval to Binance stream name."""
        binance_symbol = symbol.replace('/', '').lower()
        return f"{binance_symbol}@kline_{interval}"
    
    def _parse_kline_data(self, message: BinanceWebSocketMessage, symbol: str, interval: str) -> WebSocketMessage:
        """Parse Binance kline message to our format."""
        k = message.k
        if not k:
            raise ValueError("Invalid kline data")
            
        kline_data = KlineData(
            timestamp=k.t,
            open=float(k.o),
            high=float(k.h),
            low=float(k.l),
            close=float(k.c),
            volume=float(k.v),
            isClosed=k.x
        )
        
        return WebSocketMessage(
            type="kline_update",
            data=kline_data,
            symbol=symbol,
            interval=interval,
            timestamp=datetime.now()
        )
    
    async def _connect_to_binance(self, symbol: str, interval: str) -> websockets.WebSocketServerProtocol:
        """Connect to Binance WebSocket stream."""
        stream_name = self._get_stream_name(symbol, interval)
        url = f"{self.BINANCE_WS_URL}/{stream_name}"
        
        logger.info(f"Connecting to Binance WebSocket: {url}")
        
        try:
            websocket = await websockets.connect(url)
            logger.info(f"Connected to Binance WebSocket for {symbol} {interval}")
            return websocket
        except Exception as e:
            logger.error(f"Failed to connect to Binance WebSocket: {e}")
            raise
    
    async def _handle_binance_message(self, websocket: websockets.WebSocketServerProtocol, 
                                    symbol: str, interval: str):
        """Handle incoming messages from Binance WebSocket."""
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    binance_msg = BinanceWebSocketMessage(**data)
                    
                    # Parse and broadcast to subscribers
                    ws_message = self._parse_kline_data(binance_msg, symbol, interval)
                    await self._broadcast_to_subscribers(symbol, interval, ws_message)
                    
                except Exception as e:
                    logger.error(f"Error processing Binance message: {e}")
                    continue
                    
        except ConnectionClosed:
            logger.warning(f"Binance WebSocket connection closed for {symbol} {interval}")
        except WebSocketException as e:
            logger.error(f"Binance WebSocket error for {symbol} {interval}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in Binance WebSocket handler: {e}")
    
    async def _broadcast_to_subscribers(self, symbol: str, interval: str, message: WebSocketMessage):
        """Broadcast message to all subscribers for this symbol/interval."""
        stream_key = f"{symbol}_{interval}"
        subscribers = self.subscribers.get(stream_key, set())
        
        if not subscribers:
            return
            
        # Create a copy to avoid modification during iteration
        subscribers_copy = subscribers.copy()
        
        for callback in subscribers_copy:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                logger.error(f"Error in subscriber callback: {e}")
    
    async def _reconnect_loop(self, symbol: str, interval: str):
        """Reconnection loop for a specific stream."""
        stream_key = f"{symbol}_{interval}"
        
        while self.running:
            try:
                websocket = await self._connect_to_binance(symbol, interval)
                self.connections[stream_key] = websocket
                
                # Handle messages
                await self._handle_binance_message(websocket, symbol, interval)
                
            except Exception as e:
                logger.error(f"Reconnection error for {symbol} {interval}: {e}")
                
            # Wait before reconnecting
            if self.running:
                await asyncio.sleep(5)
    
    async def subscribe(self, symbol: str, interval: str, callback: Callable):
        """Subscribe to kline updates for a symbol/interval."""
        stream_key = f"{symbol}_{interval}"
        
        # Add subscriber
        if stream_key not in self.subscribers:
            self.subscribers[stream_key] = set()
        self.subscribers[stream_key].add(callback)
        
        # Start connection if not already running
        if stream_key not in self.connections and stream_key not in self.reconnect_tasks:
            self.reconnect_tasks[stream_key] = asyncio.create_task(
                self._reconnect_loop(symbol, interval)
            )
        
        logger.info(f"Subscribed to {symbol} {interval}")
    
    async def unsubscribe(self, symbol: str, interval: str, callback: Callable):
        """Unsubscribe from kline updates."""
        stream_key = f"{symbol}_{interval}"
        
        if stream_key in self.subscribers:
            self.subscribers[stream_key].discard(callback)
            
            # If no more subscribers, close connection
            if not self.subscribers[stream_key]:
                del self.subscribers[stream_key]
                
                # Close connection
                if stream_key in self.connections:
                    websocket = self.connections[stream_key]
                    await websocket.close()
                    del self.connections[stream_key]
                
                # Cancel reconnection task
                if stream_key in self.reconnect_tasks:
                    self.reconnect_tasks[stream_key].cancel()
                    del self.reconnect_tasks[stream_key]
                
                logger.info(f"Unsubscribed from {symbol} {interval}")
    
    async def start(self):
        """Start the WebSocket client."""
        self.running = True
        logger.info("Binance WebSocket client started")
    
    async def stop(self):
        """Stop the WebSocket client."""
        self.running = False
        
        # Cancel all reconnection tasks
        for task in self.reconnect_tasks.values():
            task.cancel()
        self.reconnect_tasks.clear()
        
        # Close all connections
        for websocket in self.connections.values():
            await websocket.close()
        self.connections.clear()
        
        # Clear subscribers
        self.subscribers.clear()
        
        logger.info("Binance WebSocket client stopped")

# Global instance
binance_ws_client = BinanceWebSocketClient()
