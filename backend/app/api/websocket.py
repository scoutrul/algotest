"""
WebSocket API endpoints for live candle streaming.
"""
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from typing import Optional

from ..services.websocket_manager import websocket_manager
from ..models.websocket import WebSocketMessage

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws/live-candle")
async def websocket_live_candle(websocket: WebSocket):
    """
    WebSocket endpoint for live candle data streaming.
    Parameters are passed via WebSocket messages.
    """
    connection_id = None
    symbol = None
    interval = None
    
    try:
        # Accept WebSocket connection first
        logger.info("Accepting WebSocket connection")
        await websocket.accept()
        logger.info("WebSocket connection accepted")
        
        # Wait for subscription message
        logger.info("Waiting for subscription message")
        subscription_message = await websocket.receive_text()
        logger.info(f"Received subscription message: {subscription_message}")
        
        try:
            subscription_data = json.loads(subscription_message)
            symbol = subscription_data.get('symbol')
            interval = subscription_data.get('interval')
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in subscription message: {subscription_message}")
            await websocket.close(code=1008, reason="Invalid subscription message format")
            return
        
        # Validate symbol and interval
        if not symbol or not interval:
            logger.warning(f"Invalid symbol or interval: {symbol}/{interval}")
            await websocket.close(code=1008, reason="Invalid symbol or interval")
            return
        
        # Connect to WebSocket manager
        logger.info(f"Connecting to WebSocket manager for {symbol}/{interval}")
        connection_id = await websocket_manager.connect(websocket, symbol, interval)
        logger.info(f"Connected to WebSocket manager with ID: {connection_id}")
        
        # Send welcome message
        welcome_message = WebSocketMessage(
            type="connection_established",
            data=None,
            symbol=symbol,
            interval=interval
        )
        await websocket_manager._send_to_connection(connection_id, welcome_message)
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for any incoming message (ping/pong)
                data = await websocket.receive_text()
                
                # Handle ping messages
                if data == "ping":
                    await websocket.send_text("pong")
                elif data == "health":
                    await websocket_manager.send_health_check(connection_id)
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {connection_id}")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket handler: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
    finally:
        if connection_id:
            await websocket_manager.disconnect(connection_id)

@router.websocket("/ws/health")
async def websocket_health(websocket: WebSocket):
    """
    WebSocket health check endpoint.
    """
    try:
        await websocket.accept()
        
        # Send health status
        health_data = {
            "type": "health_status",
            "status": "healthy",
            "active_connections": websocket_manager.get_connection_count(),
            "timestamp": websocket_manager.get_connection_info("") is not None
        }
        
        await websocket.send_text(str(health_data))
        
        # Keep connection alive for a short time
        import asyncio
        await asyncio.sleep(1)
        
    except Exception as e:
        logger.error(f"Health WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass

@router.get("/ws/stats")
async def get_websocket_stats():
    """
    Get WebSocket connection statistics.
    """
    return {
        "active_connections": websocket_manager.get_connection_count(),
        "connection_info": [
            {
                "connection_id": conn.connection_id,
                "symbol": conn.symbol,
                "interval": conn.interval,
                "connected_at": conn.connected_at.isoformat(),
                "last_activity": conn.last_activity.isoformat() if conn.last_activity else None
            }
            for conn in websocket_manager.connection_info.values()
        ]
    }
