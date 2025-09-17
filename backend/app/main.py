"""
Main FastAPI application for the BackTest Trading Bot.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import logging
import uvicorn

from .config import settings
from .api.backtest import router as backtest_router
from .api.performance import router as performance_router
from .api.market import router as market_router
from .api.data import router as data_router
from .api.orderbook import router as orderbook_router
from .api.basic import router as basic_router
from .api.websocket import router as websocket_router
from .api.test_websocket import router as test_websocket_router
from .middleware.performance import PerformanceMiddleware
from .services.database import db_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT
)

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add gzip compression middleware first (compresses responses > 1KB)
app.add_middleware(GZipMiddleware, minimum_size=1024)

# Add performance monitoring middleware
app.add_middleware(PerformanceMiddleware, enable_profiling=True)

# Add CORS middleware (should be last to handle all responses)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(basic_router)  # Basic endpoints first
app.include_router(backtest_router)
app.include_router(performance_router, prefix="/api/v1", tags=["performance"])
app.include_router(market_router)
app.include_router(data_router)

# 🔌 Include WebSocket router
app.include_router(websocket_router, tags=["websocket"])
app.include_router(test_websocket_router, tags=["test-websocket"])

# 🚀 Include Order Book router (liquidity feature)
if settings.LIQUIDITY_FEATURE_ENABLED:
    app.include_router(orderbook_router, tags=["liquidity"])
    logger.info("✅ Order Book API endpoints enabled")
else:
    logger.info("⚠️ Order Book API endpoints disabled (LIQUIDITY_FEATURE_ENABLED=false)")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "BackTest Trading Bot API",
        "version": settings.API_VERSION,
        "docs": "/docs",
        "health": "/api/v1/health",
        "features": {
            "backtesting": True,
            "market_data": True,
            "liquidity_analysis": settings.LIQUIDITY_FEATURE_ENABLED
        }
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )

@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("🚀 BackTest Trading Bot API starting up...")
    logger.info(f"📊 API Version: {settings.API_VERSION}")
    logger.info(f"🐛 Debug Mode: {settings.DEBUG}")
    logger.info(f"🌐 CORS Origins: {settings.CORS_ORIGINS}")
    logger.info(f"💧 Liquidity Feature: {'✅ Enabled' if settings.LIQUIDITY_FEATURE_ENABLED else '❌ Disabled'}")

    # Initialize database
    try:
        db_service.create_tables()
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise

    # Auto-update market data on startup
    try:
        from .api.data import sync_data_background
        import asyncio
        
        # Priority symbols and intervals for auto-update
        priority_updates = [
            ("BTC/USDT", "15m"),
            ("ETH/USDT", "15m"),
            ("BTC/USDT", "1h"),
            ("ETH/USDT", "1h"),
        ]
        
        logger.info("📈 Starting automatic market data update...")
        
        # Run updates in background without blocking startup
        async def auto_update_data():
            for symbol, interval in priority_updates:
                try:
                    await sync_data_background(symbol, interval, limit=2000)
                    logger.info(f"✅ Auto-updated {symbol} {interval}")
                except Exception as e:
                    logger.warning(f"⚠️ Auto-update failed for {symbol} {interval}: {e}")
        
        # Schedule the update task to run after startup completes
        asyncio.create_task(auto_update_data())
        logger.info("✅ Automatic data update scheduled")
        
    except Exception as e:
        logger.warning(f"⚠️ Failed to schedule automatic data update: {e}")

    # 🔌 Start WebSocket services
    try:
        from .services.binance_ws_client import binance_ws_client
        import asyncio
        
        logger.info("🔌 Starting WebSocket services...")
        
        # Start Binance WebSocket client
        asyncio.create_task(binance_ws_client.start())
        logger.info("✅ WebSocket services started")
        
    except Exception as e:
        logger.error(f"❌ Failed to start WebSocket services: {e}")
        # Don't raise here - let the app start without WebSocket
        logger.warning("⚠️ Application will continue without WebSocket services")

    # 🚀 Start Order Book collection if enabled
    if settings.LIQUIDITY_FEATURE_ENABLED:
        try:
            from .services.orderbook_collector import start_background_collection
            import asyncio
            
            logger.info("💧 Starting Order Book collection service...")
            
            # Start collection in background
            asyncio.create_task(start_background_collection())
            logger.info("✅ Order Book collection service started")
            
        except Exception as e:
            logger.error(f"❌ Failed to start Order Book collection: {e}")
            # Don't raise here - let the app start without liquidity feature
            logger.warning("⚠️ Application will continue without liquidity data collection")
    else:
        logger.info("⏭️ Order Book collection skipped (feature disabled)")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("🛑 BackTest Trading Bot API shutting down...")
    
    # Stop WebSocket services
    try:
        from .services.binance_ws_client import binance_ws_client
        logger.info("🔌 Stopping WebSocket services...")
        await binance_ws_client.stop()
        logger.info("✅ WebSocket services stopped")
    except Exception as e:
        logger.warning(f"⚠️ Error stopping WebSocket services: {e}")
    
    # Stop Order Book collection if running
    if settings.LIQUIDITY_FEATURE_ENABLED:
        try:
            from .services.orderbook_collector import stop_background_collection
            logger.info("💧 Stopping Order Book collection...")
            await stop_background_collection()
            logger.info("✅ Order Book collection stopped")
        except Exception as e:
            logger.warning(f"⚠️ Error stopping Order Book collection: {e}")
    
    logger.info("👋 Shutdown complete")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
