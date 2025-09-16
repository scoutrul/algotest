#!/usr/bin/env python3
"""
Migration script to add Order Book tables to the database.
This script creates the necessary tables for liquidity data storage.
"""
import sys
import os
import logging
from sqlalchemy import create_engine, text

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.config import settings
from app.models.database import Base
from app.models.orderbook import OrderBookSnapshot, LiquidityAggregation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_orderbook_tables():
    """Create Order Book tables in the database."""
    logger.info("🚀 Starting Order Book tables migration...")
    
    try:
        # Create database engine
        engine = create_engine(settings.DATABASE_URL, echo=settings.DATABASE_ECHO)
        logger.info(f"📊 Connected to database: {settings.DATABASE_URL}")
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
            logger.info("✅ Database connection successful")
        
        # Create all tables (this will only create new ones, won't affect existing)
        Base.metadata.create_all(engine)
        logger.info("✅ Order Book tables created successfully")
        
        # Verify tables were created
        with engine.connect() as conn:
            # Check if order_book_snapshots table exists
            if engine.dialect.name == 'sqlite':
                result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='order_book_snapshots'"
                )).fetchone()
            else:  # PostgreSQL
                result = conn.execute(text(
                    "SELECT tablename FROM pg_tables WHERE tablename='order_book_snapshots'"
                )).fetchone()
            
            if result:
                logger.info("✅ order_book_snapshots table verified")
            else:
                logger.error("❌ order_book_snapshots table not found")
                return False
            
            # Check if liquidity_aggregations table exists
            if engine.dialect.name == 'sqlite':
                result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='liquidity_aggregations'"
                )).fetchone()
            else:  # PostgreSQL
                result = conn.execute(text(
                    "SELECT tablename FROM pg_tables WHERE tablename='liquidity_aggregations'"
                )).fetchone()
            
            if result:
                logger.info("✅ liquidity_aggregations table verified")
            else:
                logger.error("❌ liquidity_aggregations table not found")
                return False
        
        logger.info("🎉 Migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False


def show_table_info():
    """Display information about the created tables."""
    logger.info("\n📋 Table Information:")
    
    # OrderBookSnapshot table info
    logger.info("\n🔹 order_book_snapshots:")
    logger.info("   - Stores individual Order Book snapshots")
    logger.info("   - Columns: id, symbol, exchange, timestamp, best_bid, best_ask, spread, etc.")
    logger.info("   - Indexes: symbol+timestamp, symbol+exchange, timestamp")
    logger.info("   - JSON columns: bid_levels, ask_levels")
    
    # LiquidityAggregation table info
    logger.info("\n🔹 liquidity_aggregations:")
    logger.info("   - Stores aggregated liquidity metrics over time intervals")
    logger.info("   - Columns: id, symbol, exchange, interval, timestamp, avg_spread, etc.")
    logger.info("   - Indexes: symbol+interval+timestamp")
    logger.info("   - Intervals: 5m, 15m, 1h, 4h, 1d")


def check_existing_data():
    """Check if there's any existing data in the tables."""
    try:
        engine = create_engine(settings.DATABASE_URL, echo=False)
        
        with engine.connect() as conn:
            # Check order_book_snapshots
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM order_book_snapshots")).fetchone()
                snapshot_count = result[0] if result else 0
                logger.info(f"📊 Existing snapshots: {snapshot_count}")
            except Exception:
                logger.info("📊 Existing snapshots: 0 (table may be new)")
            
            # Check liquidity_aggregations
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM liquidity_aggregations")).fetchone()
                agg_count = result[0] if result else 0
                logger.info(f"📊 Existing aggregations: {agg_count}")
            except Exception:
                logger.info("📊 Existing aggregations: 0 (table may be new)")
                
    except Exception as e:
        logger.warning(f"⚠️ Could not check existing data: {e}")


def main():
    """Main migration function."""
    logger.info("🚀 Order Book Tables Migration")
    logger.info("=" * 50)
    
    # Show current configuration
    logger.info(f"🔧 Database URL: {settings.DATABASE_URL}")
    logger.info(f"🔧 Liquidity Feature Enabled: {settings.LIQUIDITY_FEATURE_ENABLED}")
    logger.info(f"🔧 Liquidity Symbols: {settings.LIQUIDITY_SYMBOLS}")
    logger.info(f"🔧 Collection Interval: {settings.LIQUIDITY_COLLECTION_INTERVAL}s")
    
    if not settings.LIQUIDITY_FEATURE_ENABLED:
        logger.warning("⚠️ Liquidity feature is disabled in configuration")
        logger.info("   Set LIQUIDITY_FEATURE_ENABLED=true to enable")
    
    logger.info("\n" + "=" * 50)
    
    # Check existing data first
    logger.info("\n🔍 Checking existing data...")
    check_existing_data()
    
    # Create tables
    logger.info("\n🏗️ Creating tables...")
    success = create_orderbook_tables()
    
    if success:
        # Show table information
        show_table_info()
        
        # Final check
        logger.info("\n🔍 Post-migration check...")
        check_existing_data()
        
        logger.info("\n" + "=" * 50)
        logger.info("🎉 Migration completed successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Start the backend server to begin Order Book collection")
        logger.info("2. Check the liquidity feature in the frontend")
        logger.info("3. Monitor logs for collection activity")
        
        if not settings.LIQUIDITY_FEATURE_ENABLED:
            logger.info("\n⚠️ Remember to enable the liquidity feature:")
            logger.info("   export LIQUIDITY_FEATURE_ENABLED=true")
        
        return 0
    else:
        logger.error("\n❌ Migration failed!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
