"""
Insert test tweets directly into the database for the Twitter Feed

This script inserts tweets directly using raw SQL to avoid timezone issues
"""
import os
import json
import asyncio
import asyncpg
import logging
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Sample test tweets
TEST_TWEETS = [
    {
        "username": "crypto_trader",
        "name": "Crypto Trader",
        "tweet_id": "test-tweet-1",
        "content": "$SONIC price action is looking very bullish today! The market cap is increasing steadily and volume is picking up. #crypto #defi",
        "profile_image_url": "https://pbs.twimg.com/profile_images/1234567890/trader.jpg"
    },
    {
        "username": "market_analyst",
        "name": "Market Analyst",
        "tweet_id": "test-tweet-2",
        "content": "Major market update: ETH breaking resistance levels and $SONIC showing strong momentum. Expect increased volatility in the coming days.",
        "profile_image_url": "https://pbs.twimg.com/profile_images/9876543210/analyst.jpg"
    },
    {
        "username": "defi_expert",
        "name": "DeFi Expert",
        "tweet_id": "test-tweet-3",
        "content": "Just reviewed the $SONIC tokenomics and I'm impressed with their approach to incentivizing liquidity. This could be a game-changer for cross-chain DeFi.",
        "profile_image_url": "https://pbs.twimg.com/profile_images/5678901234/expert.jpg"
    }
]

async def insert_test_tweets():
    """Insert test tweets into the database"""
    conn = None
    try:
        # Load environment variables
        load_dotenv()
        
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            return False
        
        # Connect to database
        logger.info("Connecting to database...")
        conn = await asyncpg.connect(database_url)
        
        # Check if tweets already exist
        for tweet in TEST_TWEETS:
            tweet_id = tweet["tweet_id"]
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM twitter_scrape_data WHERE tweet_id = $1)",
                tweet_id
            )
            
            if exists:
                logger.info(f"Tweet {tweet_id} already exists, skipping")
                continue
            
            # Create metadata JSON
            metadata = {
                "authorName": tweet["name"],
                "profileImageUrl": tweet["profile_image_url"],
                "publicMetrics": {
                    "reply_count": 0,
                    "retweet_count": 0,
                    "like_count": 0
                },
                "source": "discord_webhook",
                "channelId": "1333615004305330348"
            }
            
            # Insert tweet using raw SQL
            logger.info(f"Inserting tweet: {tweet_id}")
            await conn.execute(
                """
                INSERT INTO twitter_scrape_data 
                (username, tweet_id, content, contract_addresses, timestamp, metadata, created_at)
                VALUES ($1, $2, $3, $4, NOW(), $5, NOW())
                """,
                tweet["username"],
                tweet_id,
                tweet["content"],
                [],  # Empty contract addresses
                json.dumps(metadata)
            )
            
            logger.info(f"✅ Successfully inserted tweet: {tweet_id}")
        
        # Count tweets
        total_count = await conn.fetchval("SELECT COUNT(*) FROM twitter_scrape_data")
        logger.info(f"Total tweets in database: {total_count}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error inserting test tweets: {str(e)}")
        return False
    finally:
        # Close connection
        if conn:
            await conn.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    # Run the main function
    asyncio.run(insert_test_tweets())