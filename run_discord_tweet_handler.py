"""
Discord Tweet Handler Runner

This script runs the Discord Tweet Handler service, which listens for tweets from 
a dedicated Discord channel and processes them for AI analysis and database storage.
"""

import os
import asyncio
import logging
import signal
from dotenv import load_dotenv
from src.discord_tweet_handler import DiscordTweetHandler
from src.utils.ai_processor import AIProcessor
from src.utils.database import DatabaseConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("discord_tweet_handler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global reference for cleanup
tweet_handler = None
db_connector = None
ai_processor = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}. Initiating shutdown...")
    # Set event to trigger shutdown
    if 'loop' in globals() and loop.is_running():
        loop.create_task(shutdown())

async def shutdown():
    """Perform graceful shutdown"""
    logger.info("Performing graceful shutdown...")
    
    # Close all connections
    if tweet_handler:
        logger.info("Disconnecting tweet handler...")
        await tweet_handler.disconnect()
    
    if ai_processor:
        logger.info("Closing AI processor...")
        await ai_processor.close()
    
    if db_connector:
        logger.info("Closing database connection...")
        await db_connector.close()
    
    logger.info("Shutdown complete. Exiting...")
    
    # Stop the event loop
    loop = asyncio.get_event_loop()
    loop.stop()

async def process_tweet(tweet_content: str) -> str:
    """
    Process tweets from Discord with AI analysis
    
    Args:
        tweet_content: The content of the tweet to process
        
    Returns:
        str: AI-generated response to the tweet
    """
    global ai_processor
    
    try:
        # Initialize AI processor if needed
        if not ai_processor:
            logger.info("Initializing AI processor...")
            ai_processor = AIProcessor({
                'default_provider': 'anthropic',  # Use Anthropic Claude as requested
                'max_tokens': 1000
            })
        
        # SonicKid persona system prompt
        system_prompt = """You are SonicKid, the DeFi Mad King known for cross-chain expertise
        and strategic trading insights. Analyze this crypto tweet with your high-energy style.
        Be concise (under 500 characters) and use emojis strategically. Focus on market impact,
        technical analysis, and potential opportunities. Sign off as "👑 The Mad King"."""
        
        logger.info(f"Processing tweet: {tweet_content[:100]}...")
        
        # Generate AI response
        response = await ai_processor.generate_response(
            query=tweet_content,
            context={
                'system_prompt': system_prompt,
                'temperature': 0.8  # Slightly more creative responses
            }
        )
        
        if response:
            logger.info(f"Generated response ({len(response)} chars)")
            return response
        else:
            logger.warning("AI generated empty response")
            return "👑 Interesting tweet! I'll keep an eye on this. - The Mad King"
        
    except Exception as e:
        logger.error(f"Error processing tweet: {str(e)}")
        return f"I'm processing crypto tweets right now. Will analyze this soon! 👑"

async def run_discord_tweet_handler():
    """Run the Discord Tweet Handler service"""
    global tweet_handler, db_connector
    
    try:
        # Load environment variables
        load_dotenv()
        
        # Twitter feed channel ID (fixed to specific channel)
        TWITTER_FEED_CHANNEL_ID = "1333615004305330348"
        
        # Initialize database connector
        logger.info("Initializing database connector...")
        db_connector = DatabaseConnector()
        await db_connector.connect()
        
        # Check database setup
        tweet_count = await db_connector.get_tweet_count()
        logger.info(f"Current tweet count in database: {tweet_count}")
        
        # Initialize Discord tweet handler
        logger.info(f"Initializing Discord Tweet Handler for channel {TWITTER_FEED_CHANNEL_ID}...")
        tweet_handler = DiscordTweetHandler(
            channel_id=TWITTER_FEED_CHANNEL_ID,
            on_tweet_callback=process_tweet,
            db_connector=db_connector
        )
        
        # Connect and start handling tweets
        logger.info("Starting Discord tweet handler...")
        await tweet_handler.connect()
        
    except Exception as e:
        logger.error(f"Error in Discord tweet handler service: {str(e)}")
        await shutdown()

async def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    
    logger.info("Starting Discord Tweet Handler service...")
    
    try:
        # Run the discord tweet handler
        await run_discord_tweet_handler()
    except Exception as e:
        logger.error(f"Unhandled error in main: {str(e)}")
        await shutdown()

if __name__ == "__main__":
    # Store the loop reference for shutdown
    loop = asyncio.get_event_loop()
    
    try:
        # Run the main function
        loop.run_until_complete(main())
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt detected")
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
    finally:
        # Clean up before exit
        if loop.is_running():
            loop.run_until_complete(shutdown())
        
        # Close the loop
        loop.close()
        logger.info("Service stopped")