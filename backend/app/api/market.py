from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timedelta
import logging

from ..services.data_fetcher import DataFetcher
from ..models.backtest import CandleData
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["market"])

@router.get("/candles", response_model=List[CandleData])
async def get_candles(
    symbol: str = Query(..., description="Trading pair symbol, e.g. BTC/USDT"),
    interval: str = Query(..., description="Time interval, e.g. 15m"),
    start_time: Optional[datetime] = Query(None, description="Fetch candles ending at this time (exclusive), older data only"),
    end_time: Optional[datetime] = Query(None, description="Fetch candles ending at this time (exclusive), older data only - preferred over start_time"),
    limit: int = Query(1000, ge=1, le=settings.MAX_CANDLES_LIMIT, description="Max candles to return (cumulative), default 1000, max 10000")
):
    try:
        fetcher = DataFetcher()
        collected: List[CandleData] = []
        remaining = min(limit, settings.MAX_CANDLES_LIMIT)

        # Use end_time if provided, otherwise fallback to start_time for backward compatibility
        cursor_time = end_time or start_time
        end_cursor = cursor_time.replace(tzinfo=None) if (cursor_time and cursor_time.tzinfo) else cursor_time

        # Fetch in chunks of up to 1000 to respect exchange limits
        chunk_size = 1000
        while remaining > 0:
            batch_size = min(chunk_size, remaining)
            if end_cursor:
                batch = await fetcher.fetch_candles_with_timeframe(symbol, interval, end_time=end_cursor, limit=batch_size)
            else:
                batch = await fetcher.fetch_candles(symbol, interval, batch_size)
            if not batch:
                break
            collected.extend(batch)
            remaining -= len(batch)
            # Move cursor to the oldest candle's timestamp to continue older
            oldest = batch[0]
            # step back one second to avoid re-fetching the same candle
            end_cursor = oldest.timestamp - timedelta(seconds=1)
            # If fetched less than requested, likely reached the start of history
            if len(batch) < batch_size:
                break
        # Ensure chronological order
        collected.sort(key=lambda c: c.timestamp)
        # Trim if accidentally over-collected
        if len(collected) > limit:
            collected = collected[-limit:]
        return collected
    except Exception as e:
        logger.error(f"Error fetching candles: {e}")
        raise HTTPException(status_code=500, detail=str(e))
