"""
Database service for managing candle data storage and retrieval.
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import create_engine, select, func, desc, and_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from ..config import settings
from ..models.database import Base, Candle, MarketDataStatus
from ..models.backtest import CandleData


class DatabaseService:
    """Service for database operations with candle data."""

    def __init__(self):
        self.engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.DATABASE_ECHO,
            pool_pre_ping=True,
            pool_recycle=300,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()

    async def save_candles(self, symbol: str, interval: str, candles: List[CandleData]) -> int:
        """Save candles to database. Returns number of saved candles."""
        if not candles:
            return 0

        saved_count = 0
        with self.get_session() as session:
            try:
                for candle in candles:
                    # Check if candle already exists
                    existing = session.execute(
                        select(Candle).where(
                            and_(
                                Candle.symbol == symbol,
                                Candle.interval == interval,
                                Candle.timestamp == candle.timestamp.replace(tzinfo=None)
                            )
                        )
                    ).first()

                    if existing:
                        continue  # Skip existing candles

                    # Create new candle record
                    db_candle = Candle(
                        symbol=symbol,
                        interval=interval,
                        timestamp=candle.timestamp.replace(tzinfo=None),
                        open=candle.open,
                        high=candle.high,
                        low=candle.low,
                        close=candle.close,
                        volume=candle.volume
                    )
                    session.add(db_candle)
                    saved_count += 1

                session.commit()
                await self._update_status(symbol, interval, session)
                return saved_count

            except IntegrityError as e:
                session.rollback()
                print(f"Integrity error saving candles: {e}")
                return 0
            except Exception as e:
                session.rollback()
                print(f"Error saving candles: {e}")
                return 0

    async def get_candles(
        self,
        symbol: str,
        interval: str,
        limit: int = 1000,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[CandleData]:
        """Get candles from database."""
        with self.get_session() as session:
            query = select(Candle).where(
                and_(Candle.symbol == symbol, Candle.interval == interval)
            )

            if start_time:
                query = query.where(Candle.timestamp >= start_time.replace(tzinfo=None))
            if end_time:
                query = query.where(Candle.timestamp < end_time.replace(tzinfo=None))

            query = query.order_by(desc(Candle.timestamp)).limit(limit)

            result = session.execute(query).scalars().all()

            # Convert to CandleData and reverse to chronological order
            candles = []
            for db_candle in reversed(result):
                candles.append(CandleData(
                    timestamp=db_candle.timestamp,
                    open=db_candle.open,
                    high=db_candle.high,
                    low=db_candle.low,
                    close=db_candle.close,
                    volume=db_candle.volume
                ))

            return candles

    async def get_candles_count(self, symbol: str, interval: str) -> int:
        """Get total number of candles for symbol/interval."""
        with self.get_session() as session:
            result = session.execute(
                select(func.count(Candle.id)).where(
                    and_(Candle.symbol == symbol, Candle.interval == interval)
                )
            ).scalar()
            return result or 0

    async def get_data_status(self, symbol: str, interval: str) -> Optional[MarketDataStatus]:
        """Get data synchronization status."""
        with self.get_session() as session:
            result = session.execute(
                select(MarketDataStatus).where(
                    and_(
                        MarketDataStatus.symbol == symbol,
                        MarketDataStatus.interval == interval
                    )
                )
            ).first()
            return result[0] if result else None

    async def _update_status(self, symbol: str, interval: str, session: Session):
        """Update data status after saving candles."""
        try:
            # Get min/max timestamps and count
            result = session.execute(
                select(
                    func.min(Candle.timestamp),
                    func.max(Candle.timestamp),
                    func.count(Candle.id)
                ).where(
                    and_(Candle.symbol == symbol, Candle.interval == interval)
                )
            ).first()

            if result:
                oldest_ts, newest_ts, count = result

                # Update or create status record
                status = session.execute(
                    select(MarketDataStatus).where(
                        and_(
                            MarketDataStatus.symbol == symbol,
                            MarketDataStatus.interval == interval
                        )
                    )
                ).first()

                if status:
                    status = status[0]
                    status.oldest_timestamp = oldest_ts
                    status.newest_timestamp = newest_ts
                    status.total_candles = count
                    status.last_updated = datetime.utcnow()
                else:
                    status = MarketDataStatus(
                        symbol=symbol,
                        interval=interval,
                        oldest_timestamp=oldest_ts,
                        newest_timestamp=newest_ts,
                        total_candles=count
                    )
                    session.add(status)

                session.commit()

        except Exception as e:
            print(f"Error updating status: {e}")
            session.rollback()

    async def get_missing_ranges(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Tuple[datetime, datetime]]:
        """Get ranges of missing data between start_time and end_time."""
        ranges = []
        current_start = start_time

        # Convert interval to seconds
        interval_seconds = self._interval_to_seconds(interval)

        with self.get_session() as session:
            while current_start < end_time:
                # Check if we have data for this time slot
                slot_end = current_start + timedelta(seconds=interval_seconds)

                existing = session.execute(
                    select(Candle).where(
                        and_(
                            Candle.symbol == symbol,
                            Candle.interval == interval,
                            Candle.timestamp >= current_start.replace(tzinfo=None),
                            Candle.timestamp < slot_end.replace(tzinfo=None)
                        )
                    )
                ).first()

                if not existing:
                    # Find the end of this gap
                    gap_end = current_start + timedelta(seconds=interval_seconds)
                    while gap_end < end_time:
                        next_slot_end = gap_end + timedelta(seconds=interval_seconds)
                        next_existing = session.execute(
                            select(Candle).where(
                                and_(
                                    Candle.symbol == symbol,
                                    Candle.interval == interval,
                                    Candle.timestamp >= gap_end.replace(tzinfo=None),
                                    Candle.timestamp < next_slot_end.replace(tzinfo=None)
                                )
                            )
                        ).first()
                        if next_existing:
                            break
                        gap_end = next_slot_end

                    ranges.append((current_start, min(gap_end, end_time)))

                current_start = slot_end

        return ranges

    def _interval_to_seconds(self, interval: str) -> int:
        """Convert interval string to seconds."""
        interval_map = {
            '1m': 60, '5m': 300, '15m': 900, '30m': 1800, '1h': 3600,
            '2h': 7200, '4h': 14400, '6h': 21600, '8h': 28800, '12h': 43200, '1d': 86400
        }
        return interval_map.get(interval, 900)  # Default to 15m


# Global database service instance
db_service = DatabaseService()

