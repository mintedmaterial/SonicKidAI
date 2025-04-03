"""Sonic Price Updater Service

This script runs a dedicated service that updates the Sonic token price
in the database every 3 minutes using DexScreener data with fallbacks.
"""
import asyncio
import logging
import os
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Setup signal handling for graceful shutdown
is_shutting_down = False

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global is_shutting_down
    logger.info(f"Signal {signum} received, initiating shutdown...")
    is_shutting_down = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Import database and service functions
import asyncpg
import aiohttp
import json

# Sonic chain constants
SONIC_CHAIN_ID = 146
SONIC_CHAIN_NAME = "sonic"

async def get_database_connection():
    """Get database connection from environment DATABASE_URL"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL environment variable not found")
        return None
    
    try:
        conn = await asyncpg.connect(db_url)
        logger.info("✅ Database connection established")
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection error: {str(e)}")
        return None

async def fetch_sonic_price_from_sonicscan():
    """Fetch Sonic price from SonicScan.org API"""
    url = "https://api.sonicscan.org/api?module=stats&action=ethprice"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "1" and data.get("result", {}).get("ethusd"):
                        price = float(data["result"]["ethusd"])
                        logger.info(f"✅ SonicScan price: ${price:.4f}")
                        return data
                    else:
                        logger.warning("⚠️ SonicScan API returned no price data")
                else:
                    logger.warning(f"⚠️ SonicScan API returned status {response.status}")
    except Exception as e:
        logger.error(f"❌ Error fetching SonicScan price: {str(e)}")
    
    return None

async def fetch_sonic_pairs_from_dexscreener():
    """Fetch Sonic pairs directly from DexScreener API"""
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
                        if base_token in ["SONIC", "WSONIC"]:
                            sonic_token_pairs.append(pair)
                        elif "SONIC" in base_token:
                            sonic_token_pairs.append(pair)
                        elif quote_token in ["SONIC", "WSONIC"]:
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
    
    # If no Sonic/USDC pairs found, try OS (Origin Sonic) token which is often associated with SONIC
    logger.info("Trying fallback search for OS (Origin Sonic) token...")
    url = "https://api.dexscreener.com/latest/dex/search?q=OS%20USDC"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get("pairs", [])
                    
                    # Filter for Sonic chain pairs with OS token
                    sonic_pairs = []
                    for pair in pairs:
                        if pair.get("chainId") == "sonic":
                            base_token = pair.get("baseToken", {}).get("symbol", "").upper()
                            if base_token == "OS":
                                # This is likely Origin Sonic (OS) token
                                # Modify to indicate it's really SONIC token for our purposes
                                pair["baseToken"]["alt_symbol"] = "SONIC"  # Add alternative symbol for our records
                                sonic_pairs.append(pair)
                    
                    if sonic_pairs:
                        logger.info(f"✅ Found {len(sonic_pairs)} OS (Origin Sonic) pairs on Sonic chain")
                        return sonic_pairs
                    else:
                        logger.warning("⚠️ No OS (Origin Sonic) pairs found on Sonic chain")
                else:
                    logger.warning(f"⚠️ DexScreener API returned status {response.status}")
    except Exception as e:
        logger.error(f"❌ Error fetching OS token pairs: {str(e)}")
    
    # Last resort - try any token on Sonic chain
    logger.info("Trying last resort search for any token on Sonic chain...")
    url = "https://api.dexscreener.com/latest/dex/tokens/sonic"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get("pairs", [])
                    
                    # Just get the first few pairs on Sonic chain for data
                    sonic_pairs = [pair for pair in pairs if pair.get("chainId") == "sonic"][:5]
                    
                    if sonic_pairs:
                        logger.info(f"✅ Found {len(sonic_pairs)} general pairs on Sonic chain")
                        return sonic_pairs
                    else:
                        logger.warning("⚠️ No pairs found on Sonic chain")
                else:
                    logger.warning(f"⚠️ DexScreener API returned status {response.status}")
    except Exception as e:
        logger.error(f"❌ Error fetching general Sonic chain pairs: {str(e)}")
    
    return []

async def save_pair_to_database(conn, pair_data: Dict[str, Any]) -> bool:
    """Save pair data to database"""
    try:
        # Extract relevant data
        pair_address = pair_data.get("pairAddress", "")
        pair_symbol = pair_data.get("pair", "")
        base_token = pair_data.get("baseToken", {}).get("symbol", "")
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
        if base_token.upper() in ["SONIC", "WSONIC"]:
            await conn.execute("""
                INSERT INTO price_feed_data
                (symbol, price, source, chain_id, volume_24h, price_change_24h, timestamp, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, "SONIC", price_usd, "dexscreener", "sonic", volume_24h, price_change_24h,
            datetime.now(), json.dumps(pair_data))
            
            logger.info(f"✅ Saved SONIC price: ${price_usd:.4f} to database")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error saving pair to database: {str(e)}")
        return False

async def save_sonicscan_price(conn, price_data: Dict[str, Any]) -> bool:
    """Save SonicScan price to database"""
    try:
        price = float(price_data.get("result", {}).get("ethusd", 0))
        
        # Save to price_feed_data table
        await conn.execute("""
            INSERT INTO price_feed_data
            (symbol, price, source, chain_id, volume_24h, price_change_24h, timestamp, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, "SONIC", price, "sonicscan", "sonic", 0, 0,
        datetime.now(), json.dumps(price_data))
        
        logger.info(f"✅ Saved SonicScan price: ${price:.4f} to database")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error saving SonicScan price to database: {str(e)}")
        return False

async def log_update_status(conn, update_type: str, status: str, details: Dict[str, Any]) -> bool:
    """Log update status to database"""
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

async def run_price_update_service(update_interval: int = 180):
    """Run the Sonic price update service
    
    Args:
        update_interval: Update interval in seconds (default: 3 minutes)
    """
    logger.info(f"🚀 Starting Sonic price update service (interval: {update_interval}s)")
    
    conn = None
    try:
        # Connect to database
        conn = await get_database_connection()
        if not conn:
            logger.error("❌ Cannot continue without database connection")
            return
        
        # Run update loop until shutdown signal
        while not is_shutting_down:
            start_time = time.time()
            
            update_details = {
                "timestamp": datetime.now().isoformat(),
                "sonic_price_updated": False,
                "dexscreener_pairs_updated": 0,
                "duration": 0
            }
            
            try:
                # 1. Fetch Sonic price from SonicScan
                sonic_price = await fetch_sonic_price_from_sonicscan()
                if sonic_price:
                    await save_sonicscan_price(conn, sonic_price)
                    update_details["sonic_price_updated"] = True
                
                # 2. Fetch and save Sonic pairs from DexScreener
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
            
            # Calculate time to next update
            elapsed = time.time() - start_time
            sleep_time = max(1, update_interval - elapsed)
            
            logger.info(f"Update completed in {elapsed:.1f}s. Next update in {sleep_time:.1f}s.")
            
            # Sleep until next update or shutdown
            sleep_start = time.time()
            while time.time() - sleep_start < sleep_time:
                if is_shutting_down:
                    break
                await asyncio.sleep(1)
        
        logger.info("Shutting down price update service...")
        
    except Exception as e:
        logger.error(f"❌ Service error: {str(e)}")
    finally:
        # Clean up
        if conn:
            await conn.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    # Add signal handlers
    loop = asyncio.get_event_loop()
    
    try:
        # Run the price update service
        loop.run_until_complete(run_price_update_service(180))  # 3 minute updates
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    finally:
        # Clean up
        loop.close()
        logger.info("Service stopped")