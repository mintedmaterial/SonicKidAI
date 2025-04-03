"""Run Discord bot with DexScreener market data integration"""
import asyncio
import logging
from datetime import datetime, timedelta
import os
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.services.dexscreener_service import DexScreenerService
from src.discord_tweet_handler import DiscordInstructorAgent
from src.connections.discord_connection import DiscordConnection

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_market_data_bot():
    """Run Discord bot with DexScreener integration"""
    try:
        logger.info("\n🤖 Starting DexScreener Market Data Service...")
        start_time = datetime.now()
        logger.info(f"Service start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Initialize DexScreener service with 2-minute cache
        dex_service = DexScreenerService(cache_duration=120)  # 2 minutes
        if not await dex_service.connect():
            logger.error("❌ Failed to initialize DexScreener service")
            return

        # Initialize Discord connection (if available)
        discord_enabled = False
        if os.getenv('DISCORD_BOT_TOKEN') and os.getenv('DISCORD_TEST_CHANNEL'):
            try:
                config = {
                    'token': os.getenv('DISCORD_BOT_TOKEN'),
                    'channel_id': os.getenv('DISCORD_TEST_CHANNEL')
                }
                discord_conn = DiscordConnection(config)
                agent = DiscordInstructorAgent(int(config['channel_id']), discord_conn)
                agent.dex_service = dex_service
                await agent.start()
                discord_enabled = True
                logger.info("✅ Discord bot integration enabled")
            except Exception as e:
                logger.warning(f"⚠️ Discord integration not available: {str(e)}")
        else:
            logger.info("ℹ️ Running in DexScreener-only mode (Discord integration disabled)")

        # Test tokens to monitor
        test_tokens = ["METRO", "ANON", "THC", "GOGLZ", "USDC"]

        last_run = datetime.now()
        interval = timedelta(minutes=5)  # 5-minute interval
        next_run = last_run + interval

        logger.info(f"Service configured for {interval.total_seconds()/60:.0f}-minute updates")
        logger.info(f"First update scheduled for: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

        while True:
            try:
                current_time = datetime.now()

                # Only run if interval has passed
                if current_time >= next_run:
                    update_start = datetime.now()
                    logger.info(f"\n🔄 Starting market data update at {update_start.strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.info(f"Time since last run: {(current_time - last_run).total_seconds():.1f} seconds")

                    # Update each token pair
                    all_pairs = []
                    for token in test_tokens:
                        logger.info(f"\n📊 Updating {token} pairs...")
                        pairs = await dex_service.search_pairs(token)

                        if pairs:
                            all_pairs.extend(pairs)
                            logger.info(f"Found {len(pairs)} pairs")

                            # Log sample pairs
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

                    # Update Discord bot if enabled
                    if discord_enabled and all_pairs:
                        await agent.update_market_data(all_pairs)
                        logger.info("✅ Discord bot data updated")

                    # Show cache stats
                    cache_info = dex_service.get_cache_info()
                    logger.info("\n📈 Cache Statistics:")
                    logger.info(f"Last Update: {cache_info['last_update']}")
                    logger.info(f"Cache Duration: {cache_info['cache_duration']} seconds")
                    logger.info(f"Active Entries: {cache_info['active_entries']}/{cache_info['entries']}")

                    update_end = datetime.now()
                    update_duration = (update_end - update_start).total_seconds()
                    logger.info(f"\n✅ Update completed in {update_duration:.1f} seconds")

                    last_run = current_time
                    next_run = current_time + interval
                    logger.info(f"Next update scheduled for: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

                # Sleep for 30 seconds before checking again
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"❌ Error during update cycle: {str(e)}")
                await asyncio.sleep(60)  # Wait longer on error

    except Exception as e:
        logger.error(f"❌ Service failed: {str(e)}")
    finally:
        if dex_service:
            await dex_service.close()
            logger.info("🔄 DexScreener service closed")

if __name__ == "__main__":
    try:
        asyncio.run(run_market_data_bot())
    except KeyboardInterrupt:
        logger.info("\n👋 Service stopped by user")
    except Exception as e:
        logger.error(f"❌ Unhandled error: {str(e)}")