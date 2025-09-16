"""
Order Book Collector Service for gathering real-time liquidity data.
"""
import asyncio
import ccxt
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..config import settings
from ..models.orderbook import OrderBookSnapshot, LiquidityAggregation
from ..services.database import get_db


class OrderBookCollector:
    """Service for collecting and storing Order Book snapshots."""
    
    def __init__(self, exchange_name: str = None):
        """Initialize the collector with exchange configuration."""
        self.exchange_name = exchange_name or settings.LIQUIDITY_EXCHANGE
        self.logger = logging.getLogger(f"{__name__}.{self.exchange_name}")
        
        # Initialize CCXT exchange
        try:
            exchange_class = getattr(ccxt, self.exchange_name)
            self.exchange = exchange_class({
                'enableRateLimit': True,
                'timeout': settings.BINANCE_TIMEOUT * 1000,  # CCXT expects milliseconds
                'options': {
                    'defaultType': 'spot',  # Use spot trading
                },
                'sandbox': False,  # Use production API
            })
            self.logger.info(f"Initialized {self.exchange_name} exchange connector")
        except AttributeError:
            self.logger.error(f"Unsupported exchange: {self.exchange_name}")
            raise ValueError(f"Exchange {self.exchange_name} is not supported by CCXT")
        except Exception as e:
            self.logger.error(f"Failed to initialize exchange {self.exchange_name}: {e}")
            raise
        
        # Collection settings
        self.collection_interval = settings.LIQUIDITY_COLLECTION_INTERVAL
        self.order_book_limit = settings.LIQUIDITY_ORDER_BOOK_LIMIT
        self.min_volume_threshold = settings.LIQUIDITY_MIN_VOLUME_THRESHOLD
        
        # State management
        self.is_running = False
        self.collection_task = None
        self.symbols = settings.LIQUIDITY_SYMBOLS.copy()
        
        # Statistics
        self.stats = {
            'total_snapshots': 0,
            'successful_collections': 0,
            'failed_collections': 0,
            'last_collection_time': None,
            'average_latency_ms': 0.0
        }

    async def collect_orderbook_snapshot(self, symbol: str) -> Optional[OrderBookSnapshot]:
        """Collect a single Order Book snapshot for the given symbol."""
        collection_start = datetime.now().timestamp()
        
        try:
            self.logger.debug(f"Collecting order book for {symbol}")
            
            # Fetch order book from exchange (sync call for ccxt)
            orderbook = self.exchange.fetch_order_book(
                symbol, 
                limit=self.order_book_limit
            )
            
            # Filter out small volume levels
            if self.min_volume_threshold > 0:
                orderbook['bids'] = [
                    [price, volume] for price, volume in orderbook['bids']
                    if volume >= self.min_volume_threshold
                ]
                orderbook['asks'] = [
                    [price, volume] for price, volume in orderbook['asks']
                    if volume >= self.min_volume_threshold
                ]
            
            # Create snapshot model
            snapshot = OrderBookSnapshot.from_ccxt_orderbook(
                symbol=symbol,
                exchange_name=self.exchange_name,
                orderbook_data=orderbook,
                collection_start_time=collection_start
            )
            
            self.logger.debug(
                f"Collected {symbol}: {snapshot.bid_levels_count} bids, "
                f"{snapshot.ask_levels_count} asks, spread: {snapshot.spread:.6f}"
            )
            
            return snapshot
            
        except ccxt.NetworkError as e:
            self.logger.warning(f"Network error collecting {symbol}: {e}")
            self.stats['failed_collections'] += 1
            return None
        except ccxt.ExchangeError as e:
            self.logger.warning(f"Exchange error collecting {symbol}: {e}")
            self.stats['failed_collections'] += 1
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error collecting {symbol}: {e}")
            self.stats['failed_collections'] += 1
            return None

    async def collect_all_symbols(self) -> List[OrderBookSnapshot]:
        """Collect Order Book snapshots for all configured symbols."""
        snapshots = []
        
        # Collect snapshots concurrently (but with rate limiting)
        semaphore = asyncio.Semaphore(3)  # Limit concurrent requests
        
        async def collect_with_semaphore(symbol):
            async with semaphore:
                return await self.collect_orderbook_snapshot(symbol)
        
        # Start all collection tasks
        tasks = [collect_with_semaphore(symbol) for symbol in self.symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for symbol, result in zip(self.symbols, results):
            if isinstance(result, Exception):
                self.logger.error(f"Collection task failed for {symbol}: {result}")
                self.stats['failed_collections'] += 1
            elif result is not None:
                snapshots.append(result)
                self.stats['successful_collections'] += 1
        
        return snapshots

    def store_snapshots(self, snapshots: List[OrderBookSnapshot]) -> int:
        """Store snapshots in the database."""
        if not snapshots:
            return 0
        
        stored_count = 0
        db: Session = next(get_db())
        
        try:
            for snapshot in snapshots:
                try:
                    # Use merge to handle detached instances
                    db.merge(snapshot)
                    stored_count += 1
                except IntegrityError:
                    # Skip duplicate snapshots (same symbol, exchange, timestamp)
                    db.rollback()
                    self.logger.debug(f"Duplicate snapshot skipped: {snapshot.symbol} at {snapshot.timestamp}")
                    continue
            
            db.commit()
            self.logger.info(f"Stored {stored_count} snapshots in database")
            
        except Exception as e:
            self.logger.error(f"Failed to store snapshots: {e}")
            db.rollback()
            stored_count = 0
        finally:
            db.close()
        
        return stored_count

    async def cleanup_old_data(self):
        """Clean up old snapshots based on retention policy."""
        if settings.LIQUIDITY_HISTORY_RETENTION_DAYS <= 0:
            return  # No cleanup if retention is disabled
        
        cutoff_date = datetime.now() - timedelta(days=settings.LIQUIDITY_HISTORY_RETENTION_DAYS)
        cutoff_timestamp = int(cutoff_date.timestamp() * 1000)
        
        db: Session = next(get_db())
        try:
            # Delete old snapshots
            deleted_count = db.query(OrderBookSnapshot).filter(
                OrderBookSnapshot.timestamp < cutoff_timestamp
            ).delete()
            
            # Delete old aggregations
            deleted_agg_count = db.query(LiquidityAggregation).filter(
                LiquidityAggregation.timestamp < cutoff_timestamp
            ).delete()
            
            db.commit()
            
            if deleted_count > 0 or deleted_agg_count > 0:
                self.logger.info(
                    f"Cleaned up {deleted_count} old snapshots and "
                    f"{deleted_agg_count} old aggregations"
                )
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
            db.rollback()
        finally:
            db.close()

    async def collection_cycle(self):
        """Execute one complete collection cycle."""
        cycle_start = datetime.now()
        
        try:
            # Collect snapshots
            snapshots = await self.collect_all_symbols()
            
            # Store in database
            stored_count = self.store_snapshots(snapshots)
            
            # Update statistics
            self.stats['total_snapshots'] += stored_count
            self.stats['last_collection_time'] = cycle_start
            
            # Calculate average latency
            if snapshots:
                total_latency = sum(
                    s.collection_latency_ms for s in snapshots 
                    if s.collection_latency_ms is not None
                )
                avg_latency = total_latency / len(snapshots) if snapshots else 0
                self.stats['average_latency_ms'] = avg_latency
            
            cycle_duration = (datetime.now() - cycle_start).total_seconds()
            self.logger.info(
                f"Collection cycle completed: {stored_count} snapshots stored, "
                f"cycle took {cycle_duration:.2f}s"
            )
            
        except Exception as e:
            self.logger.error(f"Collection cycle failed: {e}")
            self.stats['failed_collections'] += len(self.symbols)

    async def start_collection(self):
        """Start the background collection process."""
        if self.is_running:
            self.logger.warning("Collection is already running")
            return
        
        if not settings.LIQUIDITY_FEATURE_ENABLED:
            self.logger.info("Liquidity feature is disabled, not starting collection")
            return
        
        self.is_running = True
        self.logger.info(
            f"Starting Order Book collection for symbols: {self.symbols}, "
            f"interval: {self.collection_interval}s"
        )
        
        try:
            while self.is_running:
                # Run collection cycle
                await self.collection_cycle()
                
                # Cleanup old data periodically (every 100 cycles)
                if self.stats['total_snapshots'] % 100 == 0:
                    await self.cleanup_old_data()
                
                # Wait for next cycle
                if self.is_running:  # Check if still running after cycle
                    await asyncio.sleep(self.collection_interval)
                    
        except asyncio.CancelledError:
            self.logger.info("Collection task was cancelled")
        except Exception as e:
            self.logger.error(f"Collection process failed: {e}")
        finally:
            self.is_running = False
            self.logger.info("Order Book collection stopped")

    async def stop_collection(self):
        """Stop the background collection process."""
        if not self.is_running:
            return
        
        self.logger.info("Stopping Order Book collection...")
        self.is_running = False
        
        if self.collection_task and not self.collection_task.done():
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        return {
            **self.stats,
            'is_running': self.is_running,
            'exchange': self.exchange_name,
            'symbols': self.symbols,
            'collection_interval': self.collection_interval,
            'order_book_limit': self.order_book_limit
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to the exchange."""
        try:
            # Test with a simple market fetch
            markets = self.exchange.load_markets()
            
            # Test order book fetch for first symbol
            if self.symbols:
                test_symbol = self.symbols[0]
                orderbook = self.exchange.fetch_order_book(test_symbol, limit=5)
                
                return {
                    'success': True,
                    'exchange': self.exchange_name,
                    'markets_count': len(markets),
                    'test_symbol': test_symbol,
                    'test_orderbook_bids': len(orderbook.get('bids', [])),
                    'test_orderbook_asks': len(orderbook.get('asks', [])),
                    'message': 'Connection successful and order book fetched'
                }
            else:
                return {
                    'success': True,
                    'exchange': self.exchange_name,
                    'markets_count': len(markets),
                    'message': 'No symbols configured for testing, but markets loaded'
                }
                
        except Exception as e:
            return {
                'success': False,
                'exchange': self.exchange_name,
                'error': str(e)
            }


# Global collector instance
collector_instance: Optional[OrderBookCollector] = None


def get_collector() -> OrderBookCollector:
    """Get or create the global collector instance."""
    global collector_instance
    if collector_instance is None:
        collector_instance = OrderBookCollector()
    return collector_instance


async def start_background_collection():
    """Start background collection if feature is enabled."""
    if not settings.LIQUIDITY_FEATURE_ENABLED:
        logging.getLogger(__name__).info("Liquidity feature disabled, skipping collection")
        return
    
    collector = get_collector()
    
    # Test connection first
    test_result = collector.test_connection()
    if not test_result['success']:
        logging.getLogger(__name__).error(f"Exchange connection test failed: {test_result['error']}")
        return
    
    # Start collection in background
    collector.collection_task = asyncio.create_task(collector.start_collection())
    logging.getLogger(__name__).info("Background Order Book collection started")


async def stop_background_collection():
    """Stop background collection."""
    collector = get_collector()
    await collector.stop_collection()
