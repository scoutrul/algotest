#!/usr/bin/env python3
"""
Script to initialize the database with some sample data for testing.
"""
import sys
import os
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.database import db_service
from app.services.data_fetcher import DataFetcher
from app.config import settings


async def init_database():
    """Initialize database with sample data."""
    print("Initializing database...")

    # Create tables
    db_service.create_tables()
    print("✓ Database tables created")

    # Initialize data fetcher
    fetcher = DataFetcher()

    # Sample data to fetch
    symbols = ['BTC/USDT']
    intervals = ['15m', '1h', '1d']
    days_back = 30

    total_fetched = 0

    for symbol in symbols:
        for interval in intervals:
            try:
                print(f"Fetching {symbol} {interval} data...")

                # Calculate start date
                start_date = datetime.utcnow() - timedelta(days=days_back)

                # Fetch data
                candles = await fetcher.fetch_candles_with_timeframe(
                    symbol=symbol,
                    interval=interval,
                    start_time=start_date,
                    limit=1000
                )

                if candles:
                    print(f"✓ Fetched {len(candles)} candles for {symbol} {interval}")
                    total_fetched += len(candles)
                else:
                    print(f"⚠ No data fetched for {symbol} {interval}")

            except Exception as e:
                print(f"✗ Error fetching {symbol} {interval}: {e}")

    print(f"\n🎉 Database initialization complete!")
    print(f"📊 Total candles stored: {total_fetched}")

    # Show database stats
    stats = await db_service.get_database_stats()
    print(f"📈 Database statistics: {stats}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(init_database())

