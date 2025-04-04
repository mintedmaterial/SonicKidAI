"""
Test Twitter Client Integration

This script tests the TwitterClient class by using the factory to obtain an
authenticated client and perform search operations.

Usage:
    python test_tweet.py
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Load environment variables for Twitter credentials
from src.connections.twitter_client_factory import TwitterClientFactory

async def search_tweets(query: str = "cryptocurrency", count: int = 5):
    """Search for tweets with query"""
    logger.info(f"Testing search for '{query}'")
    
    client = await TwitterClientFactory.create_client()
    
    # Search for tweets 
    tweets = await client.search_tweets(query, count=count)
    
    if tweets:
        logger.info(f"Found {len(tweets)} tweets for query '{query}'")
        if len(tweets) > 0:
            logger.info(f"First tweet preview: {str(tweets[0])[:200]}...")
    else:
        logger.info(f"No tweets found for query '{query}'")
    
    return tweets

async def get_user_tweets(username: str = "AndreCronjeTech", count: int = 5):
    """Get tweets from a specific user"""
    logger.info(f"Testing get user tweets for @{username}")
    
    client = await TwitterClientFactory.create_client()
    
    # Get user tweets
    tweets = await client.get_user_tweets(username, count=count)
    
    if tweets:
        logger.info(f"Found {len(tweets)} tweets for user @{username}")
        if len(tweets) > 0:
            logger.info(f"First tweet preview: {str(tweets[0])[:200]}...")
    else:
        logger.info(f"No tweets found for user @{username}")
    
    return tweets

async def get_trends():
    """Get current Twitter trends"""
    logger.info(f"Testing get trends")
    
    client = await TwitterClientFactory.create_client()
    
    # Get trends
    trends = await client.get_trends()
    
    if trends:
        logger.info(f"Found {len(trends)} trends")
        if len(trends) > 0:
            logger.info(f"First trend preview: {str(trends[0])[:200]}...")
    else:
        logger.info(f"No trends found")
    
    return trends

async def test_all():
    """Run all test functions"""
    # Search tests
    await search_tweets("cryptocurrency")
    await search_tweets("SonicLabs")
    
    # User tweets tests
    await get_user_tweets("AndreCronjeTech")
    await get_user_tweets("SonicLabs")
    
    # Trends test
    await get_trends()

async def main():
    """Main entry point"""
    try:
        logger.info("Starting Twitter client tests")
        await test_all()
        logger.info("All tests completed")
    except Exception as e:
        logger.error(f"Error in tests: {e}")

if __name__ == "__main__":
    asyncio.run(main())