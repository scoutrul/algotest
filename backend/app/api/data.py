"""
API endpoints for data management and synchronization.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any
from datetime import datetime
import logging

from ..services.database import db_service
from ..services.data_fetcher import DataFetcher
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/data", tags=["data"])

data_fetcher = DataFetcher()


@router.get("/status")
async def get_data_status() -> Dict[str, Any]:
    """Get data synchronization status for all symbols and intervals."""
    try:
        status_data = {}

        for symbol in settings.SUPPORTED_SYMBOLS:
            for interval in settings.SUPPORTED_INTERVALS:
                status = await db_service.get_data_status(symbol, interval)
                count = await db_service.get_candles_count(symbol, interval)

                status_data[f"{symbol}_{interval}"] = {
                    "symbol": symbol,
                    "interval": interval,
                    "total_candles": count,
                    "last_updated": status.last_updated.isoformat() if status else None,
                    "oldest_timestamp": status.oldest_timestamp.isoformat() if status and status.oldest_timestamp else None,
                    "newest_timestamp": status.newest_timestamp.isoformat() if status and status.newest_timestamp else None,
                }

        return {
            "database_status": "connected",
            "supported_symbols": settings.SUPPORTED_SYMBOLS,
            "supported_intervals": settings.SUPPORTED_INTERVALS,
            "data_status": status_data
        }

    except Exception as e:
        logger.error(f"Error getting data status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get data status: {str(e)}")


@router.post("/sync/{symbol:path}/{interval}")
async def sync_data(
    symbol: str,
    interval: str,
    background_tasks: BackgroundTasks,
    limit: int = 10000
) -> Dict[str, Any]:
    """Sync historical data for a specific symbol and interval."""
    try:
        # Validate inputs
        if symbol not in settings.SUPPORTED_SYMBOLS:
            raise HTTPException(status_code=400, detail=f"Unsupported symbol: {symbol}")
        if interval not in settings.SUPPORTED_INTERVALS:
            raise HTTPException(status_code=400, detail=f"Unsupported interval: {interval}")

        limit = min(limit, settings.MAX_CANDLES_LIMIT)

        # Start background sync
        background_tasks.add_task(sync_data_background, symbol, interval, limit)

        return {
            "message": f"Started syncing {symbol} {interval} data",
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
            "status": "syncing"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting data sync: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start data sync: {str(e)}")


@router.post("/sync-all")
async def sync_all_data(
    background_tasks: BackgroundTasks,
    limit_per_symbol: int = 5000
) -> Dict[str, Any]:
    """Sync historical data for all supported symbols and intervals."""
    try:
        limit_per_symbol = min(limit_per_symbol, settings.MAX_CANDLES_LIMIT)

        # Start background sync for all combinations
        for symbol in settings.SUPPORTED_SYMBOLS:
            for interval in settings.SUPPORTED_INTERVALS:
                background_tasks.add_task(sync_data_background, symbol, interval, limit_per_symbol)

        return {
            "message": f"Started syncing all data ({len(settings.SUPPORTED_SYMBOLS)} symbols × {len(settings.SUPPORTED_INTERVALS)} intervals)",
            "symbols": settings.SUPPORTED_SYMBOLS,
            "intervals": settings.SUPPORTED_INTERVALS,
            "limit_per_symbol": limit_per_symbol,
            "total_syncs": len(settings.SUPPORTED_SYMBOLS) * len(settings.SUPPORTED_INTERVALS),
            "status": "syncing_all"
        }

    except Exception as e:
        logger.error(f"Error starting all data sync: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start all data sync: {str(e)}")


async def sync_data_background(symbol: str, interval: str, limit: int):
    """Background task to sync data for a specific symbol and interval."""
    try:
        logger.info(f"Starting background sync for {symbol} {interval}")

        # Get current status and count
        current_count = await db_service.get_candles_count(symbol, interval)
        status = await db_service.get_data_status(symbol, interval)
        logger.info(f"Current data count for {symbol} {interval}: {current_count}")

        # Determine incremental fetch window: from newest_timestamp forward
        start_time = None
        if status and getattr(status, "newest_timestamp", None):
            # Fetch from the next interval after newest_timestamp to avoid DB short-circuit
            try:
                from datetime import timedelta
                interval_seconds = data_fetcher._get_interval_seconds(interval)
                start_time = status.newest_timestamp + timedelta(seconds=interval_seconds)
            except Exception:
                start_time = status.newest_timestamp

        # Prefer timeframe-based fetch to load missing tail; falls back to recent window
        if start_time:
            logger.info(
                f"Fetching missing candles from {start_time.isoformat()} for {symbol} {interval} (exchange)"
            )
            # Bypass DB short-circuit and fetch directly from exchange
            candles = await data_fetcher._fetch_timeframe_from_exchange(  # noqa: SLF001
                symbol=symbol,
                interval=interval,
                start_time=start_time,
                end_time=None,
                limit=limit,
            )
        else:
            logger.info(
                f"No existing data found, fetching recent window for {symbol} {interval}"
            )
            candles = await data_fetcher.fetch_candles(symbol, interval, limit)

        saved_count = await db_service.save_candles(symbol, interval, candles)

        logger.info(f"Background sync completed for {symbol} {interval}: saved {saved_count} candles")

    except Exception as e:
        logger.error(f"Error in background sync for {symbol} {interval}: {e}")


@router.delete("/clear/{symbol:path}/{interval}")
async def clear_data(symbol: str, interval: str) -> Dict[str, Any]:
    """Clear all data for a specific symbol and interval."""
    try:
        # Validate inputs
        if symbol not in settings.SUPPORTED_SYMBOLS:
            raise HTTPException(status_code=400, detail=f"Unsupported symbol: {symbol}")
        if interval not in settings.SUPPORTED_INTERVALS:
            raise HTTPException(status_code=400, detail=f"Unsupported interval: {interval}")

        # Get count before clearing
        count_before = await db_service.get_candles_count(symbol, interval)

        # Clear data (we'll need to add this method to database service)
        with db_service.get_session() as session:
            from ..models.database import Candle, MarketDataStatus

            # Delete candles
            session.query(Candle).filter(
                Candle.symbol == symbol,
                Candle.interval == interval
            ).delete()

            # Delete status
            session.query(MarketDataStatus).filter(
                MarketDataStatus.symbol == symbol,
                MarketDataStatus.interval == interval
            ).delete()

            session.commit()

        return {
            "message": f"Cleared data for {symbol} {interval}",
            "symbol": symbol,
            "interval": interval,
            "candles_removed": count_before
        }

    except Exception as e:
        logger.error(f"Error clearing data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear data: {str(e)}")


@router.get("/stats")
async def get_database_stats() -> Dict[str, Any]:
    """Get database statistics."""
    try:
        total_candles = 0
        symbol_stats = {}

        for symbol in settings.SUPPORTED_SYMBOLS:
            symbol_total = 0
            interval_stats = {}

            for interval in settings.SUPPORTED_INTERVALS:
                count = await db_service.get_candles_count(symbol, interval)
                interval_stats[interval] = count
                symbol_total += count

            symbol_stats[symbol] = {
                "total": symbol_total,
                "by_interval": interval_stats
            }
            total_candles += symbol_total

        return {
            "total_candles": total_candles,
            "symbols": symbol_stats,
            "database_url": settings.DATABASE_URL.replace("sqlite:///", "") if "sqlite" in settings.DATABASE_URL else "external_db"
        }

    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get database stats: {str(e)}")

