"""
Automatic price updater initializer

This module automatically initializes the price update service
when imported. It runs in a background thread to avoid blocking
the main application.
"""
import asyncio
import threading
import logging
import time
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Track the background thread
_updater_thread = None
_stop_event = threading.Event()

async def get_database_connection():
    """Get database connection from environment DATABASE_URL"""
    try:
        import asyncpg
        
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            logger.error("DATABASE_URL environment variable not found")
            return None
        
        conn = await asyncpg.connect(db_url)
        logger.info("✅ Database connection established")
        return conn
    except ImportError:
        logger.error("❌ asyncpg module not available")
        return None
    except Exception as e:
        logger.error(f"❌ Database connection error: {str(e)}")
        return None

async def fetch_sonic_pairs_from_dexscreener():
    """Fetch Sonic pairs directly from DexScreener API"""
    import aiohttp
    
    # First try Sonic/USDC pairs
    url = "https://api.dexscreener.com/latest/dex/search?q=SONIC%20USDC"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get("pairs", [])
                    
                    # Filter for Sonic chain pairs only
                    sonic_pairs = [pair for pair in pairs if pair.get("chainId") == "sonic"]
                    
                    # Also look for the SONIC token in the pairs
                    sonic_token_pairs = []
                    for pair in sonic_pairs:
                        base_token = pair.get("baseToken", {}).get("symbol", "").upper()
                        quote_token = pair.get("quoteToken", {}).get("symbol", "").upper()
                        
                        # Find SONIC tokens
                        if base_token in ["SONIC", "WSONIC", "OS"]:
                            # OS is Origin Sonic on this chain
                            if base_token == "OS":
                                pair["baseToken"]["alt_symbol"] = "SONIC"  # Add alternative symbol
                            sonic_token_pairs.append(pair)
                        elif "SONIC" in base_token:
                            sonic_token_pairs.append(pair)
                        elif quote_token in ["SONIC", "WSONIC", "OS"]:
                            # If SONIC is the quote token, we need to invert the price
                            price = pair.get("priceUsd", 0)
                            if price and float(price) > 0:
                                pair["priceUsd"] = str(1.0 / float(price))
                                pair["priceNative"] = str(1.0 / float(pair.get("priceNative", price)))
                            sonic_token_pairs.append(pair)
                    
                    if sonic_token_pairs:
                        logger.info(f"✅ Found {len(sonic_token_pairs)} SONIC token pairs on Sonic chain")
                        return sonic_token_pairs
                    
                    if sonic_pairs:
                        logger.info(f"✅ Found {len(sonic_pairs)} SONIC/USDC pairs on Sonic chain (but SONIC token not identified)")
                        return sonic_pairs
                    else:
                        logger.warning("⚠️ No SONIC/USDC pairs found on Sonic chain")
                else:
                    logger.warning(f"⚠️ DexScreener API returned status {response.status}")
    except Exception as e:
        logger.error(f"❌ Error fetching DexScreener pairs: {str(e)}")
    
    return []

async def save_pair_to_database(conn, pair_data: Dict[str, Any]) -> bool:
    """Save pair data to database"""
    import json
    
    try:
        # Extract relevant data
        pair_address = pair_data.get("pairAddress", "")
        pair_symbol = pair_data.get("pair", "")
        base_token = pair_data.get("baseToken", {}).get("symbol", "")
        base_token_alt = pair_data.get("baseToken", {}).get("alt_symbol", "")
        quote_token = pair_data.get("quoteToken", {}).get("symbol", "")
        price = pair_data.get("priceNative", 0)
        price_usd = pair_data.get("priceUsd", 0)
        price_change_24h = pair_data.get("priceChange", {}).get("h24", 0)
        volume_24h = pair_data.get("volume", {}).get("h24", 0)
        liquidity = pair_data.get("liquidity", {}).get("usd", 0)
        chain = pair_data.get("chainId", "")
        
        # Save to sonic_price_feed table
        await conn.execute("""
            INSERT INTO sonic_price_feed 
            (pair_address, pair_symbol, base_token, quote_token, price, price_usd, 
             price_change_24h, volume_24h, liquidity, chain, timestamp, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        """, pair_address, pair_symbol, base_token, quote_token, price, price_usd,
        price_change_24h, volume_24h, liquidity, chain, datetime.now(),
        json.dumps(pair_data))
        
        # Also save to price_feed_data table for legacy compatibility
        sonic_symbols = ["SONIC", "WSONIC", "OS"]
        is_sonic_token = base_token.upper() in sonic_symbols or base_token_alt.upper() in sonic_symbols
        
        if is_sonic_token:
            await conn.execute("""
                INSERT INTO price_feed_data
                (symbol, price, source, chain_id, volume_24h, price_change_24h, timestamp, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, "SONIC", price_usd, "dexscreener", "sonic", volume_24h, price_change_24h,
            datetime.now(), json.dumps(pair_data))
            
            # Use str() for price_usd to prevent format errors with different types
            logger.info(f"✅ Saved SONIC price: ${str(price_usd)} to database")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error saving pair to database: {str(e)}")
        return False

async def log_update_status(conn, update_type: str, status: str, details: Dict[str, Any]) -> bool:
    """Log update status to database"""
    import json
    
    try:
        await conn.execute("""
            INSERT INTO market_updates
            (update_type, status, last_updated, details)
            VALUES ($1, $2, $3, $4)
        """, update_type, status, datetime.now(), json.dumps(details))
        
        return True
    except Exception as e:
        logger.error(f"❌ Error logging update status: {str(e)}")
        return False

async def run_single_update():
    """Run a single price update cycle"""
    conn = None
    try:
        # Connect to database
        conn = await get_database_connection()
        if not conn:
            logger.error("❌ Cannot continue without database connection")
            return
        
        start_time = time.time()
        
        update_details = {
            "timestamp": datetime.now().isoformat(),
            "sonic_price_updated": False,
            "dexscreener_pairs_updated": 0,
            "duration": 0
        }
        
        try:
            # Fetch and save Sonic pairs from DexScreener
            sonic_pairs = await fetch_sonic_pairs_from_dexscreener()
            
            for pair in sonic_pairs:
                await save_pair_to_database(conn, pair)
            
            update_details["dexscreener_pairs_updated"] = len(sonic_pairs)
            
            # Log successful update
            update_details["duration"] = time.time() - start_time
            await log_update_status(conn, "sonic_price", "success", update_details)
            
        except Exception as e:
            logger.error(f"❌ Error in update cycle: {str(e)}")
            await log_update_status(conn, "sonic_price", "failed", {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
        
        # Calculate time elapsed
        elapsed = time.time() - start_time
        logger.info(f"✅ Update completed in {elapsed:.1f}s")
        
    except Exception as e:
        logger.error(f"❌ Service error: {str(e)}")
    finally:
        # Clean up
        if conn:
            await conn.close()
            logger.info("Database connection closed")

async def scheduled_updates(interval_seconds=60):
    """Run scheduled updates at the specified interval
    
    Args:
        interval_seconds: Seconds between updates (default: 60s to respect rate limits
          but keep dashboard fresh)
    """
    logger.info(f"🚀 Starting background price updater (interval: {interval_seconds}s)")
    
    while not _stop_event.is_set():
        try:
            await run_single_update()
            
            # Sleep until next update, checking for stop events
            for _ in range(interval_seconds):
                if _stop_event.is_set():
                    break
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ Error in update loop: {str(e)}")
            await asyncio.sleep(5)  # Shorter delay on error

def _run_background_updater():
    """Run the updater in a separate thread"""
    asyncio.run(scheduled_updates())

def start_background_updater():
    """Start the background updater thread"""
    global _updater_thread, _stop_event
    
    if _updater_thread is not None and _updater_thread.is_alive():
        logger.info("Price updater already running")
        return
    
    # Reset stop event
    _stop_event.clear()
    
    # Start updater in background thread
    _updater_thread = threading.Thread(target=_run_background_updater, daemon=True)
    _updater_thread.start()
    
    logger.info("✅ Background price updater started")

def stop_background_updater():
    """Stop the background updater thread"""
    global _stop_event
    
    if _updater_thread is None or not _updater_thread.is_alive():
        logger.info("No price updater running")
        return
    
    # Set stop event
    _stop_event.set()
    logger.info("⏹️ Stopping price updater...")

# Auto-initialize when imported
start_background_updater()