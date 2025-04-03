"""
Runner for Simplified Telegram Bot

This script runs the simplified Telegram bot with proper error handling and logging.
"""
import asyncio
import logging
import os
import signal
import sys
from dotenv import load_dotenv
from simplified_telegram_bot import SimplifiedTelegramBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global bot instance for signal handling
bot = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    asyncio.create_task(shutdown())

async def shutdown():
    """Perform graceful shutdown"""
    global bot
    if bot:
        logger.info("Stopping Telegram bot...")
        await bot.stop()
    logger.info("Telegram bot stopped")
    sys.exit(0)

async def main():
    """Main entry point"""
    global bot
    
    # Load environment variables
    logger.info("Loading environment variables...")
    load_dotenv(".env.telegram")
    
    # Check required environment variables
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN environment variable not set")
        logger.info("Please add a bot token to .env.telegram or set as environment variable")
        return
    
    # Register signal handlers
    logger.info("Registering signal handlers...")
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize and start the bot
        logger.info("Starting Simplified Telegram Bot...")
        bot = SimplifiedTelegramBot()
        connected = await bot.connect()
        
        if connected:
            logger.info("Bot initialized successfully")
            logger.info("Bot is running. Press CTRL+C to stop")
            await bot.start()
        else:
            logger.error("Failed to initialize bot")
            return
    
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        await shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)