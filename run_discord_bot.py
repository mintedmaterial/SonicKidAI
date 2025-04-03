"""Main script to run the Discord bot"""
import asyncio
import os
import logging
from dotenv import load_dotenv
from src.discord_tweet_handler import DiscordInstructorAgent
from src.connections.discord_connection import DiscordConnection
from src.utils.logging_config import setup_logging

# Initialize logging
logger = setup_logging()

async def main():
    """Main function to run the Discord bot"""
    handler = None
    try:
        # Load environment variables
        load_dotenv()
        logger.info("🔍 Loading environment variables...")

        # Verify environment variables
        discord_token = os.getenv('DISCORD_BOT_TOKEN')
        if not discord_token:
            logger.error("❌ DISCORD_BOT_TOKEN not found in environment variables")
            return False

        # Initialize Discord connection with debug logging
        logger.debug(f"Token starts with: {discord_token[:6]}...")
        discord_config = {
            'token': discord_token,
            'development_mode': True  # Enable detailed logging
        }
        discord_conn = DiscordConnection(discord_config)

        # Test token before proceeding
        if not await discord_conn.test_token():
            logger.error("❌ Discord token validation failed")
            return False

        logger.info("✅ Discord token validated successfully")

        # Initialize Discord handler
        handler = DiscordInstructorAgent(
            channel_id=1316237075762384926,  # Main channel
            discord_connection=discord_conn
        )

        logger.info("🚀 Starting Discord bot...")
        await handler.start()

        logger.info("✅ Bot started successfully! Listening for messages...")

        # Keep the bot running with enhanced health checks
        reconnect_attempts = 0
        max_reconnect_attempts = 3
        health_check_interval = 30  # seconds

        while True:
            try:
                if not handler._initialized or not handler.client.is_ready():
                    reconnect_attempts += 1
                    logger.warning(f"Bot connection lost (Attempt {reconnect_attempts}/{max_reconnect_attempts}), attempting to reconnect...")

                    # Check if we should keep trying
                    if reconnect_attempts > max_reconnect_attempts:
                        logger.error("❌ Max reconnection attempts reached, restarting bot...")
                        reconnect_attempts = 0
                        if handler:
                            await handler.stop()
                        handler = DiscordInstructorAgent(
                            channel_id=1316237075762384926,
                            discord_connection=discord_conn
                        )
                        await handler.start()
                    else:
                        await handler.start()
                else:
                    # Reset counter on successful connection
                    if reconnect_attempts > 0:
                        logger.info("✅ Bot successfully reconnected")
                        reconnect_attempts = 0

                    # Log periodic health status
                    logger.debug(f"Health check: Bot is {'ready' if handler.client.is_ready() else 'not ready'}, Status: {handler.client.status if handler.client else 'None'}")

                await asyncio.sleep(health_check_interval)
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(5)

    except KeyboardInterrupt:
        logger.info("👋 Received shutdown signal")
    except Exception as e:
        if "Privileged intents" in str(e):
            logger.error("❌ Bot requires privileged intents to be enabled in Discord Developer Portal")
            logger.error("Please enable MESSAGE CONTENT, SERVER MEMBERS, and PRESENCE intents")
        else:
            logger.error(f"❌ Discord bot error: {e}")
        raise
    finally:
        logger.info("🛑 Shutting down Discord bot...")
        if handler:
            try:
                await handler.stop()
                logger.info("✅ Bot shutdown complete")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")

if __name__ == "__main__":
    try:
        logger.info("🚀 Starting Discord bot process...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}")