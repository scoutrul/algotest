"""
Test WebSocket endpoint to isolate the issue.
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws/test")
async def websocket_test_simple(websocket: WebSocket):
    """Simple test WebSocket endpoint."""
    try:
        # Accept connection immediately
        await websocket.accept()
        logger.info("✅ Simple test WebSocket connected")
        
        # Send welcome message
        await websocket.send_text('{"type": "test", "message": "connected"}')
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                await websocket.send_text(f'Echo: {data}')
            except WebSocketDisconnect:
                break
    except Exception as e:
        logger.error(f"Error in simple test WebSocket: {e}")

@router.websocket("/ws/test/{symbol}/{interval}")
async def websocket_test(
    websocket: WebSocket,
    symbol: str,
    interval: str
):
    """Test WebSocket endpoint with parameters."""
    try:
        # Accept connection immediately
        await websocket.accept()
        logger.info(f"✅ Test WebSocket connected for {symbol} {interval}")
        
        # Send welcome message
        await websocket.send_text('{"type": "test", "message": "connected"}')
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                await websocket.send_text(f'Echo: {data}')
            except WebSocketDisconnect:
                logger.info("Test WebSocket disconnected")
                break
            except Exception as e:
                logger.error(f"Error in test WebSocket: {e}")
                break
                
    except Exception as e:
        logger.error(f"Test WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
