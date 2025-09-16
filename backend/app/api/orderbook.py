"""
Order Book API endpoints for liquidity data access.
"""
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from ..config import settings
from ..services.database import get_db
from ..models.orderbook import OrderBookSnapshot, LiquidityAggregation
from ..services.orderbook_collector import get_collector

# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/orderbook", tags=["orderbook"])


@router.get("/health")
async def orderbook_health():
    """Health check for Order Book service."""
    if not settings.LIQUIDITY_FEATURE_ENABLED:
        return {
            "status": "disabled",
            "message": "Liquidity feature is disabled"
        }
    
    collector = get_collector()
    stats = collector.get_stats()
    
    return {
        "status": "healthy" if stats['is_running'] else "stopped",
        "feature_enabled": settings.LIQUIDITY_FEATURE_ENABLED,
        "exchange": stats['exchange'],
        "symbols": stats['symbols'],
        "collection_stats": {
            "is_running": stats['is_running'],
            "total_snapshots": stats['total_snapshots'],
            "successful_collections": stats['successful_collections'],
            "failed_collections": stats['failed_collections'],
            "last_collection_time": stats['last_collection_time'].isoformat() if stats['last_collection_time'] else None,
            "average_latency_ms": stats['average_latency_ms']
        }
    }


@router.get("/test-connection")
async def test_exchange_connection():
    """Test connection to the exchange."""
    if not settings.LIQUIDITY_FEATURE_ENABLED:
        raise HTTPException(status_code=503, detail="Liquidity feature is disabled")
    
    collector = get_collector()
    result = await collector.test_connection()
    
    if not result['success']:
        raise HTTPException(status_code=503, detail=f"Exchange connection failed: {result['error']}")
    
    return result


@router.get("/{symbol}/current")
async def get_current_orderbook(
    symbol: str,
    limit: int = Query(20, ge=1, le=100, description="Number of price levels to return")
):
    """Get current Order Book snapshot for a symbol."""
    if not settings.LIQUIDITY_FEATURE_ENABLED:
        raise HTTPException(status_code=503, detail="Liquidity feature is disabled")
    
    try:
        # Normalize symbol
        symbol = symbol.upper()
        
        # Get fresh snapshot from exchange
        collector = get_collector()
        snapshot = await collector.collect_orderbook_snapshot(symbol)
        
        if not snapshot:
            raise HTTPException(status_code=404, detail=f"Could not fetch order book for {symbol}")
        
        # Limit the number of levels if requested
        if limit and limit < len(snapshot.bid_levels):
            snapshot.bid_levels = snapshot.bid_levels[:limit]
        if limit and limit < len(snapshot.ask_levels):
            snapshot.ask_levels = snapshot.ask_levels[:limit]
        
        return {
            "symbol": symbol,
            "timestamp": snapshot.timestamp,
            "datetime": snapshot.get_datetime_utc().isoformat(),
            "exchange": snapshot.exchange,
            "best_bid": snapshot.best_bid,
            "best_ask": snapshot.best_ask,
            "spread": snapshot.spread,
            "spread_percentage": snapshot.spread_percentage,
            "bid_levels": snapshot.bid_levels,
            "ask_levels": snapshot.ask_levels,
            "total_bid_volume": snapshot.total_bid_volume,
            "total_ask_volume": snapshot.total_ask_volume,
            "collection_latency_ms": snapshot.collection_latency_ms
        }
        
    except Exception as e:
        logger.error(f"Error getting current order book for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get order book: {str(e)}")


@router.get("/{symbol}/history")
async def get_orderbook_history(
    symbol: str,
    db: Session = Depends(get_db),
    start_time: Optional[int] = Query(None, description="Start timestamp (milliseconds)"),
    end_time: Optional[int] = Query(None, description="End timestamp (milliseconds)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of snapshots"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order by timestamp")
):
    """Get historical Order Book snapshots for a symbol."""
    if not settings.LIQUIDITY_FEATURE_ENABLED:
        raise HTTPException(status_code=503, detail="Liquidity feature is disabled")
    
    try:
        # Normalize symbol - convert BTCUSDT to BTC/USDT for database query
        symbol = symbol.upper()
        if '/' not in symbol and len(symbol) >= 6:
            # Convert BTCUSDT to BTC/USDT format
            if symbol.endswith('USDT'):
                symbol = symbol[:-4] + '/USDT'
            elif symbol.endswith('USD'):
                symbol = symbol[:-3] + '/USD'
            elif symbol.endswith('BTC'):
                symbol = symbol[:-3] + '/BTC'
            elif symbol.endswith('ETH'):
                symbol = symbol[:-3] + '/ETH'
        
        # Build query
        query = db.query(OrderBookSnapshot).filter(
            OrderBookSnapshot.symbol == symbol
        )
        
        # Apply time filters
        if start_time:
            query = query.filter(OrderBookSnapshot.timestamp >= start_time)
        if end_time:
            query = query.filter(OrderBookSnapshot.timestamp <= end_time)
        
        # Apply ordering
        if order == "desc":
            query = query.order_by(desc(OrderBookSnapshot.timestamp))
        else:
            query = query.order_by(OrderBookSnapshot.timestamp)
        
        # Apply limit
        snapshots = query.limit(limit).all()
        
        return {
            "symbol": symbol,
            "count": len(snapshots),
            "start_time": start_time,
            "end_time": end_time,
            "snapshots": [snapshot.to_dict() for snapshot in snapshots]
        }
        
    except Exception as e:
        logger.error(f"Error getting order book history for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


@router.get("/{symbol}/liquidity-chart")
async def get_liquidity_chart_data(
    symbol: str,
    db: Session = Depends(get_db),
    start_time: Optional[int] = Query(None, description="Start timestamp (milliseconds)"),
    end_time: Optional[int] = Query(None, description="End timestamp (milliseconds)"),
    limit: int = Query(200, ge=1, le=1000, description="Maximum number of data points"),
    min_volume: float = Query(0.01, ge=0, description="Minimum volume threshold")
):
    """Get Order Book data formatted for Lightweight Charts visualization."""
    if not settings.LIQUIDITY_FEATURE_ENABLED:
        raise HTTPException(status_code=503, detail="Liquidity feature is disabled")
    
    try:
        # Normalize symbol - convert BTCUSDT to BTC/USDT for database query
        symbol = symbol.upper()
        if '/' not in symbol and len(symbol) >= 6:
            # Convert BTCUSDT to BTC/USDT format
            if symbol.endswith('USDT'):
                symbol = symbol[:-4] + '/USDT'
            elif symbol.endswith('USD'):
                symbol = symbol[:-3] + '/USD'
            elif symbol.endswith('BTC'):
                symbol = symbol[:-3] + '/BTC'
            elif symbol.endswith('ETH'):
                symbol = symbol[:-3] + '/ETH'
        
        # Build query
        query = db.query(OrderBookSnapshot).filter(
            OrderBookSnapshot.symbol == symbol
        )
        
        # Apply time filters
        if start_time:
            query = query.filter(OrderBookSnapshot.timestamp >= start_time)
        if end_time:
            query = query.filter(OrderBookSnapshot.timestamp <= end_time)
        
        # Order by timestamp and apply limit
        snapshots = query.order_by(desc(OrderBookSnapshot.timestamp)).limit(limit).all()
        
        # Convert to chart format
        chart_data = []
        for snapshot in reversed(snapshots):  # Reverse to get chronological order
            chart_point = snapshot.to_lightweight_chart_data()
            
            # Filter levels by minimum volume
            if min_volume > 0:
                chart_point['liquidity_levels'] = [
                    level for level in chart_point['liquidity_levels']
                    if abs(level['volume']) >= min_volume
                ]
            
            chart_data.append(chart_point)
        
        return {
            "symbol": symbol,
            "count": len(chart_data),
            "min_volume_filter": min_volume,
            "data": chart_data
        }
        
    except Exception as e:
        logger.error(f"Error getting liquidity chart data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chart data: {str(e)}")


@router.get("/{symbol}/density")
async def get_liquidity_density(
    symbol: str,
    db: Session = Depends(get_db),
    timeframe: str = Query("1h", regex="^(5m|15m|1h|4h|1d)$", description="Aggregation timeframe"),
    start_time: Optional[int] = Query(None, description="Start timestamp (milliseconds)"),
    end_time: Optional[int] = Query(None, description="End timestamp (milliseconds)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of data points")
):
    """Get aggregated liquidity density data for visualization."""
    if not settings.LIQUIDITY_FEATURE_ENABLED:
        raise HTTPException(status_code=503, detail="Liquidity feature is disabled")
    
    try:
        # Normalize symbol - convert BTCUSDT to BTC/USDT for database query
        symbol = symbol.upper()
        if '/' not in symbol and len(symbol) >= 6:
            # Convert BTCUSDT to BTC/USDT format
            if symbol.endswith('USDT'):
                symbol = symbol[:-4] + '/USDT'
            elif symbol.endswith('USD'):
                symbol = symbol[:-3] + '/USD'
            elif symbol.endswith('BTC'):
                symbol = symbol[:-3] + '/BTC'
            elif symbol.endswith('ETH'):
                symbol = symbol[:-3] + '/ETH'
        
        # Convert timeframe to milliseconds
        timeframe_ms = {
            "5m": 5 * 60 * 1000,
            "15m": 15 * 60 * 1000,
            "1h": 60 * 60 * 1000,
            "4h": 4 * 60 * 60 * 1000,
            "1d": 24 * 60 * 60 * 1000
        }[timeframe]
        
        # Set default time range if not provided
        if not end_time:
            end_time = int(datetime.now().timestamp() * 1000)
        if not start_time:
            start_time = end_time - (24 * 60 * 60 * 1000)  # 24 hours ago
        
        # Build query for snapshots in time range
        query = db.query(OrderBookSnapshot).filter(
            and_(
                OrderBookSnapshot.symbol == symbol,
                OrderBookSnapshot.timestamp >= start_time,
                OrderBookSnapshot.timestamp <= end_time
            )
        ).order_by(OrderBookSnapshot.timestamp)
        
        snapshots = query.all()
        
        # Aggregate data by timeframe
        aggregated_data = []
        current_bucket_start = start_time
        current_bucket_snapshots = []
        
        for snapshot in snapshots:
            # Check if snapshot belongs to current bucket
            bucket_start = (snapshot.timestamp // timeframe_ms) * timeframe_ms
            
            if bucket_start != current_bucket_start:
                # Process previous bucket
                if current_bucket_snapshots:
                    agg_point = _aggregate_snapshots(current_bucket_snapshots, current_bucket_start)
                    aggregated_data.append(agg_point)
                
                # Start new bucket
                current_bucket_start = bucket_start
                current_bucket_snapshots = []
            
            current_bucket_snapshots.append(snapshot)
        
        # Process last bucket
        if current_bucket_snapshots:
            agg_point = _aggregate_snapshots(current_bucket_snapshots, current_bucket_start)
            aggregated_data.append(agg_point)
        
        # Apply limit
        if len(aggregated_data) > limit:
            aggregated_data = aggregated_data[-limit:]
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "start_time": start_time,
            "end_time": end_time,
            "count": len(aggregated_data),
            "data": aggregated_data
        }
        
    except Exception as e:
        logger.error(f"Error getting liquidity density for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get density data: {str(e)}")


@router.get("/symbols")
async def get_available_symbols(db: Session = Depends(get_db)):
    """Get list of symbols with available Order Book data."""
    if not settings.LIQUIDITY_FEATURE_ENABLED:
        raise HTTPException(status_code=503, detail="Liquidity feature is disabled")
    
    try:
        # Get symbols from database
        db_symbols = db.query(OrderBookSnapshot.symbol).distinct().all()
        db_symbols = [row[0] for row in db_symbols]
        
        # Get configured symbols
        configured_symbols = settings.LIQUIDITY_SYMBOLS
        
        # Get latest snapshot info for each symbol
        symbol_info = []
        for symbol in set(db_symbols + configured_symbols):
            latest_snapshot = db.query(OrderBookSnapshot).filter(
                OrderBookSnapshot.symbol == symbol
            ).order_by(desc(OrderBookSnapshot.timestamp)).first()
            
            symbol_info.append({
                "symbol": symbol,
                "configured": symbol in configured_symbols,
                "has_data": symbol in db_symbols,
                "latest_timestamp": latest_snapshot.timestamp if latest_snapshot else None,
                "latest_datetime": latest_snapshot.get_datetime_utc().isoformat() if latest_snapshot else None
            })
        
        return {
            "symbols": symbol_info,
            "configured_symbols": configured_symbols,
            "collection_enabled": settings.LIQUIDITY_FEATURE_ENABLED
        }
        
    except Exception as e:
        logger.error(f"Error getting available symbols: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get symbols: {str(e)}")


@router.post("/collect-now")
async def trigger_collection(
    background_tasks: BackgroundTasks,
    symbols: Optional[List[str]] = Query(None, description="Symbols to collect (default: all configured)")
):
    """Trigger immediate Order Book collection for specified symbols."""
    if not settings.LIQUIDITY_FEATURE_ENABLED:
        raise HTTPException(status_code=503, detail="Liquidity feature is disabled")
    
    try:
        collector = get_collector()
        
        # Use provided symbols or default to configured ones
        target_symbols = symbols or settings.LIQUIDITY_SYMBOLS
        
        # Trigger collection in background
        async def collect_snapshots():
            original_symbols = collector.symbols.copy()
            try:
                collector.symbols = target_symbols
                snapshots = await collector.collect_all_symbols()
                stored_count = collector.store_snapshots(snapshots)
                logger.info(f"Manual collection completed: {stored_count} snapshots stored")
            finally:
                collector.symbols = original_symbols
        
        background_tasks.add_task(collect_snapshots)
        
        return {
            "message": f"Collection triggered for {len(target_symbols)} symbols",
            "symbols": target_symbols,
            "status": "started"
        }
        
    except Exception as e:
        logger.error(f"Error triggering collection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger collection: {str(e)}")


def _aggregate_snapshots(snapshots: List[OrderBookSnapshot], bucket_timestamp: int) -> Dict[str, Any]:
    """Aggregate multiple snapshots into a single data point."""
    if not snapshots:
        return {}
    
    # Calculate aggregated metrics
    spreads = [s.spread for s in snapshots if s.spread is not None]
    total_volumes = [s.total_volume for s in snapshots]
    bid_volumes = [s.total_bid_volume for s in snapshots]
    ask_volumes = [s.total_ask_volume for s in snapshots]
    
    # Get the most recent snapshot for representative data
    latest_snapshot = max(snapshots, key=lambda s: s.timestamp)
    
    return {
        "time": int(bucket_timestamp / 1000),  # Convert to seconds for Lightweight Charts
        "timestamp": bucket_timestamp,
        "datetime": datetime.utcfromtimestamp(bucket_timestamp / 1000).isoformat(),
        "symbol": latest_snapshot.symbol,
        "snapshots_count": len(snapshots),
        "avg_spread": sum(spreads) / len(spreads) if spreads else None,
        "min_spread": min(spreads) if spreads else None,
        "max_spread": max(spreads) if spreads else None,
        "avg_total_volume": sum(total_volumes) / len(total_volumes),
        "max_total_volume": max(total_volumes),
        "avg_bid_volume": sum(bid_volumes) / len(bid_volumes),
        "avg_ask_volume": sum(ask_volumes) / len(ask_volumes),
        "best_bid": latest_snapshot.best_bid,
        "best_ask": latest_snapshot.best_ask,
        "representative_bid_levels": latest_snapshot.bid_levels[:10],  # Top 10 levels
        "representative_ask_levels": latest_snapshot.ask_levels[:10]   # Top 10 levels
    }
