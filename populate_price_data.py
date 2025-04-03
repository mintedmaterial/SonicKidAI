#!/usr/bin/env python3
"""
Script to populate token price data for testing
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

async def get_database_connection():
    """Get database connection from environment DATABASE_URL"""
    import asyncpg
    
    try:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            logger.error("DATABASE_URL environment variable not found")
            return None
            
        conn = await asyncpg.connect(db_url)
        logger.info("✅ Database connection established")
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection error: {str(e)}")
        return None

async def save_pair_to_database(conn, pair_data: Dict[str, Any]) -> bool:
    """Save pair data to database"""
    if not conn:
        logger.error("No database connection")
        return False
        
    try:
        # Prepare data for insert
        pair_address = pair_data.get("pairAddress")
        base_token = pair_data.get("baseToken", {}).get("symbol", "UNKNOWN")
        quote_token = pair_data.get("quoteToken", {}).get("symbol", "UNKNOWN")
        chain_id = pair_data.get("chainId", "unknown")
        
        # Convert price and other numeric values
        price = float(pair_data.get("priceUsd", 0))
        price_native = float(pair_data.get("priceNative", 0))
        price_change_24h = float(pair_data.get("priceChange", {}).get("h24", 0))
        volume_24h = float(pair_data.get("volume", {}).get("h24", 0))
        liquidity = float(pair_data.get("liquidity", {}).get("usd", 0))
        
        # Prepare timestamp
        timestamp = datetime.now()
        
        # Convert data to JSON string for metadata
        metadata_json = json.dumps(pair_data)
        
        # Insert data into sonic_price_feed table
        query = """
            INSERT INTO sonic_price_feed (
                pair_address, pair_symbol, base_token, quote_token, price, price_usd,
                price_change_24h, volume_24h, liquidity, chain, timestamp, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        """
        pair_symbol = f"{base_token}/{quote_token}"
        
        await conn.execute(
            query,
            pair_address,
            pair_symbol,
            base_token,
            quote_token,
            price_native,
            price,
            price_change_24h,
            volume_24h,
            liquidity,
            chain_id,
            timestamp,
            metadata_json
        )
        
        logger.info(f"✅ Saved pair {pair_symbol} on {chain_id} to database")
        
        # Also save to price_feed_data table
        price_feed_query = """
            INSERT INTO price_feed_data (
                symbol, price, source, chain_id, volume_24h, price_change_24h, 
                timestamp, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """
        
        # Insert base token price
        await conn.execute(
            price_feed_query,
            base_token,
            price,
            "dexscreener",
            chain_id,
            volume_24h,
            price_change_24h,
            timestamp,
            metadata_json
        )
        
        logger.info(f"✅ Saved {base_token} price (${price:.6f}) to price_feed_data")
        
        # If quote token isn't a stablecoin, also save its price
        if quote_token not in ["USDC", "USDT", "BUSD", "DAI", "UST", "USDC.e"]:
            quote_price = 1.0 / price_native if price_native > 0 else 0
            quote_price_usd = 1.0 / price if price > 0 else 0
            
            await conn.execute(
                price_feed_query,
                quote_token,
                quote_price_usd,
                "dexscreener",
                chain_id,
                volume_24h,
                -price_change_24h,  # Inverse the price change
                timestamp,
                metadata_json
            )
            
            logger.info(f"✅ Saved {quote_token} price (${quote_price_usd:.6f}) to price_feed_data")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error saving pair to database: {str(e)}")
        return False

async def populate_test_data():
    """Populate test data into database"""
    # Sample data for Sonic chain
    sonic_pairs = [
        {
            "pairAddress": "0x63aac75153c340c8286a0ba8e9d1b912ca789d46",
            "baseToken": {
                "address": "0x8563f7e6982fbdd4d4e91e72f48cfc4af83a4852",
                "name": "Metro",
                "symbol": "METRO"
            },
            "quoteToken": {
                "address": "0x208eb26a5a57d7f0b47f04525a44da8fe0ca8c2f",
                "name": "Wrapped Sonic",
                "symbol": "wS"
            },
            "priceNative": 0.8413,
            "priceUsd": 0.8413,
            "txns": {
                "h1": {"buys": 1, "sells": 0},
                "h24": {"buys": 12, "sells": 8},
            },
            "volume": {
                "h1": 1000,
                "h24": 85000,
            },
            "priceChange": {
                "h1": 0.1,
                "h24": 5.2,
            },
            "liquidity": {
                "usd": 750000,
                "base": 550000,
                "quote": 462750,
            },
            "fdv": 8413000,
            "pairCreatedAt": 1679295762,
            "chainId": "sonic"
        },
        {
            "pairAddress": "0x9eea47a378ff7c39767ebb7fdc48de7b4ee21595",
            "baseToken": {
                "address": "0x208eb26a5a57d7f0b47f04525a44da8fe0ca8c2f",
                "name": "Wrapped Sonic",
                "symbol": "wS"
            },
            "quoteToken": {
                "address": "0xeb466342c20d5cad16bd5221d10f231de6826c6c",
                "name": "USD Coin",
                "symbol": "USDC.e"
            },
            "priceNative": 1.0,
            "priceUsd": 1.0,
            "txns": {
                "h1": {"buys": 3, "sells": 2},
                "h24": {"buys": 45, "sells": 38},
            },
            "volume": {
                "h1": 5000,
                "h24": 250000,
            },
            "priceChange": {
                "h1": 0.05,
                "h24": 1.8,
            },
            "liquidity": {
                "usd": 1500000,
                "base": 750000,
                "quote": 750000,
            },
            "fdv": 10000000,
            "pairCreatedAt": 1679225762,
            "chainId": "sonic"
        },
        {
            "pairAddress": "0x4df49a5e67e7c052fbf05e6e056ffb912ec9c7db",
            "baseToken": {
                "address": "0x6b3bd0478df43f72a5caecb9642c37628bf1fb9c",
                "name": "SONIC Protocol",
                "symbol": "SONIC"
            },
            "quoteToken": {
                "address": "0xeb466342c20d5cad16bd5221d10f231de6826c6c",
                "name": "USD Coin",
                "symbol": "USDC.e"
            },
            "priceNative": 0.025,
            "priceUsd": 0.025,
            "txns": {
                "h1": {"buys": 2, "sells": 1},
                "h24": {"buys": 28, "sells": 22},
            },
            "volume": {
                "h1": 2000,
                "h24": 75000,
            },
            "priceChange": {
                "h1": -0.1,
                "h24": 2.5,
            },
            "liquidity": {
                "usd": 500000,
                "base": 10000000,
                "quote": 250000,
            },
            "fdv": 2500000,
            "pairCreatedAt": 1679195762,
            "chainId": "sonic"
        }
    ]
    
    # Sample data for Ethereum chain
    ethereum_pairs = [
        {
            "pairAddress": "0x3416cf6c708da44db2624d63ea0aaef7113527c6",
            "baseToken": {
                "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "name": "Wrapped Ether",
                "symbol": "WETH"
            },
            "quoteToken": {
                "address": "0xdac17f958d2ee523a2206206994597c13d831ec7",
                "name": "Tether USD",
                "symbol": "USDT"
            },
            "priceNative": 3500.0,
            "priceUsd": 3500.0,
            "txns": {
                "h1": {"buys": 15, "sells": 12},
                "h24": {"buys": 320, "sells": 275},
            },
            "volume": {
                "h1": 120000,
                "h24": 2500000,
            },
            "priceChange": {
                "h1": 0.2,
                "h24": -1.5,
            },
            "liquidity": {
                "usd": 50000000,
                "base": 7142.85,
                "quote": 25000000,
            },
            "fdv": 420000000000,
            "pairCreatedAt": 1576925762,
            "chainId": "ethereum"
        },
        {
            "pairAddress": "0x1f98431c8ad98523631ae4a59f267346ea31f984",
            "baseToken": {
                "address": "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9",
                "name": "Aave",
                "symbol": "AAVE"
            },
            "quoteToken": {
                "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "name": "Wrapped Ether",
                "symbol": "WETH"
            },
            "priceNative": 0.025,
            "priceUsd": 87.5,
            "txns": {
                "h1": {"buys": 8, "sells": 5},
                "h24": {"buys": 90, "sells": 85},
            },
            "volume": {
                "h1": 50000,
                "h24": 980000,
            },
            "priceChange": {
                "h1": -0.5,
                "h24": 3.2,
            },
            "liquidity": {
                "usd": 12000000,
                "base": 68571.42,
                "quote": 1714.28,
            },
            "fdv": 1400000000,
            "pairCreatedAt": 1625925762,
            "chainId": "ethereum"
        }
    ]
    
    conn = await get_database_connection()
    if not conn:
        return False
    
    try:
        # Save Sonic pairs
        for pair in sonic_pairs:
            await save_pair_to_database(conn, pair)
        
        # Save Ethereum pairs
        for pair in ethereum_pairs:
            await save_pair_to_database(conn, pair)
        
        logger.info("✅ Successfully populated test data")
        await conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Error populating test data: {str(e)}")
        if conn:
            await conn.close()
        return False

if __name__ == "__main__":
    asyncio.run(populate_test_data())