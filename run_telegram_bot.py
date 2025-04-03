"""Run the Telegram bot with proper async handling"""
import logging
import os
import signal
import asyncio
from dotenv import load_dotenv
from src.services.whale_tracker_service import WhaleTrackerService
from src.services.market_service import MarketService
from src.services.huggingface_service import HuggingFaceService
from src.utils.ai_processor import AIProcessor
from src.connections.telegram import TelegramConnection
from src.server.db import Database

# Configure logging for development
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for development
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    raise KeyboardInterrupt

async def initialize_services():
    """Initialize all required services"""
    try:
        # Load configuration
        config = {
            'openrouter': {
                'api_key': os.getenv('OPENROUTER_API_KEY')
            },
            'anthropic': {
                'api_key': os.getenv('ANTHROPIC_API_KEY')
            },
            'development_mode': True  # Enable development mode
        }

        # Initialize database
        db = Database()
        pool = await db.get_pool()
        logger.debug("Database pool initialized")

        # Initialize AI services
        openrouter = AIProcessor(config)
        logger.debug("AI Processor initialized")

        # Initialize services
        whale_tracker = WhaleTrackerService(pool=pool)
        market_service = MarketService(
            config=config,
            equalizer=openrouter,
            openrouter=openrouter,
            db_pool=pool
        )
        huggingface = HuggingFaceService()

        logger.debug("Services initialized, starting WhaleTracker...")
        success = await whale_tracker.start()
        if not success:
            logger.error("Failed to start WhaleTracker service")
            return None, None, None

        logger.info("✅ Services initialized successfully")
        return whale_tracker, market_service, huggingface
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

async def test_bot_functionality(bot):
    """Test core bot functionality"""
    try:
        test_chat_id = int(os.getenv('TELEGRAM_TEST_CHAT_ID', '-1001234567890'))
        test_messages = [
            # Test market queries
            "@SonicKid_Bot What's the price of ETH?",
            "@SonicKid_Bot How's the market sentiment?",
            # Test authorized trade analysis (from @CoLT_145)
            "@SonicKid_Bot /trade BTC",
            # Test unauthorized trade attempt
            "@SonicKid_Bot /trade ETH"
        ]

        logger.debug("Starting test message sequence...")
        for msg in test_messages:
            try:
                await bot.send_message(test_chat_id, msg)
                logger.info(f"✅ Sent test message: {msg}")
                await asyncio.sleep(2)  # Wait between messages
            except Exception as e:
                logger.error(f"❌ Error sending test message: {str(e)}")

    except Exception as e:
        logger.error(f"Error in test functionality: {str(e)}")

async def main():
    """Main bot execution function"""
    bot = None
    try:
        # Load environment variables
        load_dotenv()

        # Initialize services
        whale_tracker, market_service, huggingface = await initialize_services()
        if not whale_tracker or not market_service or not huggingface:
            logger.error("Failed to initialize required services")
            return
            
        # Initialize CryptoPanic service
        from src.services.cryptopanic_service import CryptoPanicService
        crypto_panic = CryptoPanicService()
        await crypto_panic.initialize()
        logger.info("✅ CryptoPanic service initialized")

        # Initialize configuration
        config = {
            'token': os.getenv('TELEGRAM_BOT_TOKEN'),
            'whale_tracker': whale_tracker,
            'market_service': market_service,
            'huggingface': huggingface,
            'crypto_panic': crypto_panic,
            'authorized_users': ["@CoLT_145"],  # List of users allowed to trigger trades
            'development_mode': True  # Enable development mode
        }

        logger.info("🚀 Starting Telegram bot in development mode...")

        # Initialize and start bot
        bot = TelegramConnection(config)
        success = await bot.connect()

        if not success:
            logger.error("Failed to connect to Telegram")
            return

        logger.info("✅ Successfully connected to Telegram")

        # Run test cases in development mode
        if os.getenv('BOT_TEST_MODE', 'false').lower() == 'true':
            await test_bot_functionality(bot)

        # Keep the main task running with health checks
        while True:
            try:
                await asyncio.sleep(1)

                # Monitor service health in development mode
                if not await whale_tracker.is_connected():
                    status = await whale_tracker.get_connection_status()
                    logger.warning(f"Service connection issues detected: {status}")

                    # Attempt reconnection if needed
                    if not status['running']:
                        logger.info("Attempting to restart services...")
                        await whale_tracker.start()

            except asyncio.CancelledError:
                logger.info("Main loop cancelled, shutting down...")
                break

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error in main: {str(e)}", exc_info=True)
    finally:
        # Ensure proper cleanup
        if bot:
            try:
                await bot.close()
                logger.info("Bot closed successfully")
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")

if __name__ == "__main__":
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        logger.info("Starting bot in development mode...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")