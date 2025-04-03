"""
Direct Discord Webhook Service for Twitter Feed

This script runs the webhook endpoint directly (without using aiohttp) to handle
webhook requests from Discord to your application.
"""
import os
import json
import asyncio
import logging
import time
import signal
import asyncpg
from datetime import datetime, timezone
import re
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global database connection pool
db_pool = None

# Constants
TWITTER_FEED_CHANNEL_ID = "1333615004305330348"

async def store_tweet(tweet_data):
    """Store tweet data in the database"""
    if not db_pool:
        logger.error("Database connection not established")
        return False
        
    try:
        # Extract data from tweet payload
        username = tweet_data.get('author', {}).get('username', 'unknown_user')
        tweet_id = tweet_data.get('id', f"tweet-{datetime.now(timezone.utc).timestamp()}")
        content = tweet_data.get('text', '')
        
        # Extract contract addresses if present
        contract_addresses = []
        contract_regex = re.compile(r'0x[a-fA-F0-9]{40}')
        matches = contract_regex.findall(content)
        if matches:
            contract_addresses = matches
            
        # Build metadata
        metadata = {
            'authorName': tweet_data.get('author', {}).get('name', username),
            'profileImageUrl': tweet_data.get('author', {}).get('profile_image_url'),
            'publicMetrics': tweet_data.get('public_metrics', {
                'reply_count': 0,
                'retweet_count': 0,
                'like_count': 0
            }),
            'source': 'discord_webhook',
            'channelId': TWITTER_FEED_CHANNEL_ID
        }
        
        # Store in database
        query = """
        INSERT INTO twitter_scrape_data 
        (username, tweet_id, content, contract_addresses, timestamp, metadata)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (tweet_id) 
        DO UPDATE SET
            content = EXCLUDED.content,
            contract_addresses = EXCLUDED.contract_addresses,
            metadata = EXCLUDED.metadata
        RETURNING id
        """
        
        # Create a timezone-aware datetime
        current_time = datetime.now(timezone.utc)
        
        result = await db_pool.fetchval(
            query, 
            username, 
            tweet_id, 
            content, 
            contract_addresses, 
            current_time,
            json.dumps(metadata)
        )
        
        logger.info(f"Stored tweet in database with ID: {result}")
        return True
    except Exception as e:
        logger.error(f"Error storing tweet in database: {str(e)}")
        return False

async def format_tweet(author_name="Discord User", username="discord_user", 
                     content="Test tweet", profile_image=None):
    """Format tweet data"""
    # Generate tweet ID
    tweet_id = f"tweet-{datetime.now(timezone.utc).timestamp()}"
    
    # Format as tweet object
    tweet = {
        'id': tweet_id,
        'text': content,
        'author': {
            'name': author_name,
            'username': username,
            'profile_image_url': profile_image
        },
        'created_at': datetime.now(timezone.utc).isoformat(),
        'public_metrics': {
            'reply_count': 0,
            'retweet_count': 0,
            'like_count': 0
        }
    }
    
    return tweet

async def init_db():
    """Initialize database connection pool"""
    global db_pool
    
    try:
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            return False
            
        # Create connection pool
        logger.info("Creating database connection pool...")
        db_pool = await asyncpg.create_pool(database_url)
        
        # Test query to verify connection
        test = await db_pool.fetchval("SELECT 1")
        if test == 1:
            logger.info("✅ Database connection established and tested")
            return True
        else:
            logger.error("Database connection test failed")
            return False
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        return False

async def test_tweet_insertion():
    """Test inserting a tweet into the database"""
    # Format a test tweet
    tweet = await format_tweet(
        author_name="Test User", 
        username="test_user", 
        content="This is a test tweet from the webhook service"
    )
    
    # Store in database
    result = await store_tweet(tweet)
    
    if result:
        logger.info("✅ Test tweet insertion successful")
    else:
        logger.error("❌ Test tweet insertion failed")
    
    return result

async def run_direct_webhook_test():
    """Run the direct webhook test"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Initialize database
        logger.info("Initializing database connection...")
        db_connected = await init_db()
        
        if not db_connected:
            logger.error("Failed to connect to database. Exiting.")
            return
        
        # Run test tweet insertion
        logger.info("Testing tweet insertion...")
        await test_tweet_insertion()
        
        # Insert a tweet with SONIC mention
        sonic_tweet = await format_tweet(
            author_name="Crypto Trader", 
            username="crypto_trader", 
            content="$SONIC price is looking very bullish today! #crypto #defi"
        )
        
        # Store in database
        await store_tweet(sonic_tweet)
        logger.info("Stored SONIC tweet in database")
        
        # Insert a market update tweet
        market_tweet = await format_tweet(
            author_name="Market Analyst", 
            username="market_analyst", 
            content="Major market update: ETH breaking resistance levels and $SONIC showing strong momentum."
        )
        
        # Store in database
        await store_tweet(market_tweet)
        logger.info("Stored market update tweet in database")
        
        # Query to verify tweets in database
        total_count = await db_pool.fetchval("SELECT COUNT(*) FROM twitter_scrape_data")
        logger.info(f"Total tweets in database: {total_count}")
        
        # Sleep for a moment to let DB operations complete
        await asyncio.sleep(1)
        
    except Exception as e:
        logger.error(f"Error in direct webhook test: {str(e)}")
    finally:
        # Close database connection
        if db_pool:
            await db_pool.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    # Run the main function
    asyncio.run(run_direct_webhook_test())