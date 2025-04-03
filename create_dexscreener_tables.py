"""Create DexScreener price feed database tables"""
import asyncio
import logging
import os
import sys
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

async def create_tables():
    """Create necessary database tables for price feeds"""
    import psycopg2
    import json
    
    logging.info("Creating DexScreener database tables")
    
    # Get database URL from environment
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logging.error("DATABASE_URL environment variable not found")
        return False
    
    try:
        # Create database connection
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Create sonic_price_feed table for DexScreener pair data
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sonic_price_feed (
            id SERIAL PRIMARY KEY,
            pair_address TEXT NOT NULL,
            pair_symbol TEXT NOT NULL,
            base_token TEXT NOT NULL,
            quote_token TEXT NOT NULL,
            price FLOAT NOT NULL,
            price_usd FLOAT NOT NULL,
            price_change_24h FLOAT,
            volume_24h FLOAT,
            liquidity FLOAT,
            chain TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
            metadata JSONB
        )
        """)
        
        # Create price_feed_data table for legacy compatibility
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_feed_data (
            id SERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            price FLOAT NOT NULL,
            source TEXT NOT NULL,
            chain_id TEXT NOT NULL,
            volume_24h FLOAT,
            price_change_24h FLOAT,
            timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
            metadata JSONB
        )
        """)
        
        # Create market_updates table for logging update status
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_updates (
            id SERIAL PRIMARY KEY,
            update_type TEXT NOT NULL,
            status TEXT NOT NULL,
            last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
            details JSONB
        )
        """)
        
        # Create indexes for faster queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sonic_price_feed_pair_address ON sonic_price_feed(pair_address)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sonic_price_feed_base_token ON sonic_price_feed(base_token)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_feed_data_symbol ON price_feed_data(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_feed_data_source ON price_feed_data(source)")
        
        # Commit the changes
        conn.commit()
        
        # Close the connection
        cursor.close()
        conn.close()
        
        logging.info("✅ Successfully created all required tables")
        return True
        
    except Exception as e:
        logging.error(f"❌ Error creating tables: {str(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(create_tables())