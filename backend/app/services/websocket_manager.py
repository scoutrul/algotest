"""
WebSocket connection manager for handling client connections and data broadcasting.
"""
import asyncio
import json
import logging
from typing import Dict, Set, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from uuid import uuid4

from ..models.websocket import WebSocketMessage, ConnectionInfo
from .binance_ws_client import binance_ws_client

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections and data broadcasting."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_info: Dict[str, ConnectionInfo] = {}
        self.symbol_subscribers: Dict[str, Set[str]] = {}  # symbol_interval -> connection_ids
        
    def _get_stream_key(self, symbol: str, interval: str) -> str:
        """Get stream key for symbol and interval."""
        return f"{symbol}_{interval}"
    
    async def connect(self, websocket: WebSocket, symbol: str, interval: str) -> str:
        """Connect WebSocket and return connection ID."""
        # WebSocket is already accepted by the endpoint
        
        connection_id = str(uuid4())
        self.active_connections[connection_id] = websocket
        
        # Store connection info
        self.connection_info[connection_id] = ConnectionInfo(
            connection_id=connection_id,
            symbol=symbol,
            interval=interval,
            connected_at=datetime.now()
        )
        
        # Add to symbol subscribers
        stream_key = self._get_stream_key(symbol, interval)
        if stream_key not in self.symbol_subscribers:
            self.symbol_subscribers[stream_key] = set()
        self.symbol_subscribers[stream_key].add(connection_id)
        
        # Subscribe to Binance WebSocket
        await binance_ws_client.subscribe(symbol, interval, self._create_broadcast_callback(stream_key))
        
        logger.info(f"WebSocket connected: {connection_id} for {symbol} {interval}")
        return connection_id
    
    def _create_broadcast_callback(self, stream_key: str):
        """Create a callback function for broadcasting to specific stream."""
        async def broadcast_callback(message: WebSocketMessage):
            await self._broadcast_to_stream(stream_key, message)
        return broadcast_callback
    
    async def _broadcast_to_stream(self, stream_key: str, message: WebSocketMessage):
        """Broadcast message to all connections subscribed to this stream."""
        connection_ids = self.symbol_subscribers.get(stream_key, set())
        
        if not connection_ids:
            return
        
        # Create a copy to avoid modification during iteration
        connection_ids_copy = connection_ids.copy()
        
        for connection_id in connection_ids_copy:
            await self._send_to_connection(connection_id, message)
    
    async def _send_to_connection(self, connection_id: str, message: WebSocketMessage):
        """Send message to specific connection."""
        if connection_id not in self.active_connections:
            return
        
        websocket = self.active_connections[connection_id]
        
        try:
            # Convert message to JSON
            message_dict = message.dict()
            message_dict['timestamp'] = message.timestamp.isoformat() if message.timestamp else None
            
            await websocket.send_text(json.dumps(message_dict))
            
            # Update last activity
            if connection_id in self.connection_info:
                self.connection_info[connection_id].last_activity = datetime.now()
                
        except WebSocketDisconnect:
            await self.disconnect(connection_id)
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {e}")
            await self.disconnect(connection_id)
    
    async def disconnect(self, connection_id: str):
        """Disconnect WebSocket connection."""
        if connection_id not in self.active_connections:
            return
        
        websocket = self.active_connections[connection_id]
        connection_info = self.connection_info.get(connection_id)
        
        try:
            await websocket.close()
        except Exception as e:
            logger.error(f"Error closing WebSocket {connection_id}: {e}")
        
        # Remove from active connections
        del self.active_connections[connection_id]
        
        if connection_info:
            # Remove from symbol subscribers
            stream_key = self._get_stream_key(connection_info.symbol, connection_info.interval)
            if stream_key in self.symbol_subscribers:
                self.symbol_subscribers[stream_key].discard(connection_id)
                
                # If no more subscribers, unsubscribe from Binance
                if not self.symbol_subscribers[stream_key]:
                    await binance_ws_client.unsubscribe(
                        connection_info.symbol, 
                        connection_info.interval, 
                        self._create_broadcast_callback(stream_key)
                    )
                    del self.symbol_subscribers[stream_key]
            
            del self.connection_info[connection_id]
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_health_check(self, connection_id: str):
        """Send health check message to connection."""
        health_message = WebSocketMessage(
            type="health_check",
            data=None,
            symbol="",
            interval="",
            timestamp=datetime.now()
        )
        
        await self._send_to_connection(connection_id, health_message)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self.active_connections)
    
    def get_connection_info(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get connection information."""
        return self.connection_info.get(connection_id)
    
    def get_stream_subscriber_count(self, symbol: str, interval: str) -> int:
        """Get number of subscribers for a specific stream."""
        stream_key = self._get_stream_key(symbol, interval)
        return len(self.symbol_subscribers.get(stream_key, set()))
    
    async def broadcast_to_all(self, message: WebSocketMessage):
        """Broadcast message to all active connections."""
        for connection_id in list(self.active_connections.keys()):
            await self._send_to_connection(connection_id, message)

# Global instance
websocket_manager = WebSocketManager()
