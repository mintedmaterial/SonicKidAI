"""Run DexScreener service with regular price updates"""
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

# Add the project root to Python path
sys.path.append(os.path.abspath("."))

# Import our service
from src.services.dexscreener_service import DexScreenerService

async def run_dexscreener_service():
    """Run DexScreener service to keep price data up to date"""
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting DexScreener price update service")
    
    # Initialize service
    dexscreener_service = DexScreenerService(cache_duration=120)  # 2 minute cache
    
    # Connect to service
    initialized = await dexscreener_service.connect()
    if not initialized:
        logger.error("❌ Failed to initialize DexScreener service")
        return False
    
    logger.info("✅ DexScreener service initialized successfully")
    
    try:
        # Test SONIC price data first
        logger.info("Testing SONIC price data from SonicScan...")
        sonic_price_data = await dexscreener_service.fetch_sonic_price()
        if sonic_price_data and sonic_price_data.get('result', {}).get('ethusd'):
            price = float(sonic_price_data['result']['ethusd'])
            logger.info(f"✅ SONIC price from SonicScan: ${price:.4f}")
        else:
            logger.warning("⚠️ Failed to get SONIC price from SonicScan")
        
        # Test direct SONIC/USDC pair search
        logger.info("Testing SONIC/USDC pair search...")
        sonic_pairs = await dexscreener_service.search_pairs("SONIC/USDC", "sonic", force_refresh=True)
        if sonic_pairs:
            logger.info(f"✅ Found {len(sonic_pairs)} SONIC/USDC pairs")
            # Show details of first pair
            pair = sonic_pairs[0]
            logger.info(f"Pair: {pair.get('pair', 'Unknown')}")
            logger.info(f"Price: ${pair.get('priceUsd', 0)}")
            logger.info(f"24h Volume: ${pair.get('volume24h', 0)}")
            
            # Save this pair to database for testing
            await dexscreener_service.save_pair_data_to_database(pair)
            
            # Also save to legacy table
            base_token = pair.get('baseToken', {}).get('symbol', '')
            if base_token and base_token.upper() in ['SONIC', 'WSONIC']:
                logger.info(f"Saving {base_token} to legacy table...")
                await dexscreener_service.save_price_data_to_legacy_table('SONIC', pair, 'dexscreener')
        else:
            logger.warning("⚠️ No SONIC/USDC pairs found, searching for any SONIC pairs...")
            
            # Try with just "SONIC"
            sonic_pairs = await dexscreener_service.search_pairs("SONIC", "sonic", force_refresh=True)
            if sonic_pairs:
                logger.info(f"✅ Found {len(sonic_pairs)} SONIC pairs")
                # Show details of first pair
                pair = sonic_pairs[0]
                logger.info(f"Pair: {pair.get('pair', 'Unknown')}")
                logger.info(f"Price: ${pair.get('priceUsd', 0)}")
                logger.info(f"24h Volume: ${pair.get('volume24h', 0)}")
                
                # Save this pair to database for testing
                await dexscreener_service.save_pair_data_to_database(pair)
                
                # Also save to legacy table
                base_token = pair.get('baseToken', {}).get('symbol', '')
                if base_token and base_token.upper() in ['SONIC', 'WSONIC']:
                    logger.info(f"Saving {base_token} to legacy table...")
                    await dexscreener_service.save_price_data_to_legacy_table('SONIC', pair, 'dexscreener')
        
        # Run regular price updates for 2 minutes (will update every 30 seconds)
        logger.info("\n=== Starting Regular Price Updates ===")
        update_task = asyncio.create_task(
            dexscreener_service.start_regular_price_updates(update_interval=30)
        )
        
        # Let it run for 2 minutes
        logger.info("Running price updates for 2 minutes...")
        await asyncio.sleep(120)
        
        # Stop updates
        logger.info("Stopping price updates...")
        await dexscreener_service.stop_price_updates()
        
        # Wait for task to complete
        try:
            await asyncio.wait_for(update_task, timeout=5)
            logger.info("✅ Price update task stopped successfully")
        except asyncio.TimeoutError:
            logger.warning("⚠️ Price update task timeout - force cancelling")
            update_task.cancel()
        
        logger.info("✅ DexScreener service completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error running DexScreener service: {str(e)}")
        return False
    finally:
        # Clean up
        await dexscreener_service.close()
        logger.info("✅ Resources cleaned up")

if __name__ == "__main__":
    asyncio.run(run_dexscreener_service())