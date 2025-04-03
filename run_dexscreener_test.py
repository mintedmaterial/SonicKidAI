"""Run DexScreener service test with a single update cycle"""
import asyncio
import logging
import time
import os
import sys
from datetime import datetime, timedelta

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.services.dexscreener_service import DexScreenerService, SONIC

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_dexscreener_test():
    """Run DexScreener test for a single update cycle"""
    try:
        logger.info("\n🔄 Starting DexScreener service test...")

        # Initialize service with 2-minute cache
        service = DexScreenerService(cache_duration=120)  # 2 minutes

        # Initialize service
        if not await service.connect():
            logger.error("❌ Failed to initialize service")
            return False

        # Test tokens to monitor
        test_tokens = ["METRO", "ANON", "THC", "GOGLZ", "USDC"]

        update_start = datetime.now()
        logger.info(f"\n🔄 Starting market data update at {update_start.strftime('%Y-%m-%d %H:%M:%S')}")

        # Test each token
        for token in test_tokens:
            logger.info(f"\n📊 Testing {token} pairs...")
            pairs = await service.search_pairs(token, SONIC)

            if pairs:
                logger.info(f"Found {len(pairs)} pairs")
                for pair in pairs[:2]:  # Show up to 2 pairs per token
                    logger.info("\nPair Details:")
                    logger.info(f"Pair: {pair['pair']}")
                    logger.info(f"Base Token: {pair['baseToken']['symbol']}")
                    logger.info(f"Quote Token: {pair['quoteToken']['symbol']}")
                    logger.info(f"Price USD: ${float(pair['priceUsd']):.8f}")
                    logger.info(f"24h Volume: ${float(pair['volume24h']):,.2f}")
                    logger.info(f"Liquidity: ${float(pair['liquidity']):,.2f}")
            else:
                logger.warning(f"No pairs found for {token}")

            # Brief pause between tokens
            await asyncio.sleep(1)

        # Show cache stats
        cache_info = service.get_cache_info()
        logger.info("\n📈 Cache Statistics:")
        logger.info(f"Last Update: {cache_info['last_update']}")
        logger.info(f"Cache Duration: {cache_info['cache_duration']} seconds")
        logger.info(f"Active Entries: {cache_info['active_entries']}/{cache_info['entries']}")

        update_end = datetime.now()
        update_duration = (update_end - update_start).total_seconds()
        logger.info(f"\n✅ Update completed in {update_duration:.1f} seconds")

        await service.close()
        logger.info("🔄 DexScreener service closed")
        return True

    except Exception as e:
        logger.error(f"❌ Service failed: {str(e)}")
        return False
    finally:
        if service:
            await service.close()
            logger.info("🔄 DexScreener service closed")

if __name__ == "__main__":
    try:
        asyncio.run(run_dexscreener_test())
    except KeyboardInterrupt:
        logger.info("\n👋 Service stopped by user")
    except Exception as e:
        logger.error(f"❌ Unhandled error: {str(e)}")