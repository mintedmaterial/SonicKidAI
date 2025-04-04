"""
Test Twitter Client Integration

This script tests the TwitterClient class with various operations:
1. Direct login with auth token and credentials
2. Search for tweets with and without authentication
3. Get user tweets for specific users
4. Get current Twitter trends

Usage:
    python test_twitter_client.py
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
from src.connections.twitter_client import TwitterClient
from src.connections.twitter_client_factory import TwitterClientFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

async def test_login():
    """Test login functionality with both auth token and credentials"""
    logger.info("===== Testing Login Functionality =====")
    
    client = await TwitterClientFactory.create_client()
    auth_result = await client.login()
    
    logger.info(f"Authentication result: {auth_result}")
    logger.info(f"Is authenticated: {client.is_authenticated}")
    
    return client

async def test_search_tweets(client: TwitterClient, query: str = "cryptocurrency"):
    """Test searching for tweets with a query"""
    logger.info(f"===== Testing Search Tweets with Query: '{query}' =====")
    
    # Test different search modes
    modes = ["Latest", "Top", "Photos"]
    
    for mode in modes:
        logger.info(f"Searching with mode: {mode}")
        tweets = await client.search_tweets(query, count=5, mode=mode)
        
        if tweets:
            logger.info(f"Found {len(tweets)} tweets in {mode} mode")
            if len(tweets) > 0:
                sample_tweet = tweets[0]
                logger.info(f"Sample tweet: {json.dumps(sample_tweet, indent=2)[:200]}...")
        else:
            logger.warning(f"No tweets found in {mode} mode")

async def test_get_user_tweets(client: TwitterClient, username: str = "AndreCronjeTech"):
    """Test getting tweets from a specific user"""
    logger.info(f"===== Testing Get User Tweets for @{username} =====")
    
    tweets = await client.get_user_tweets(username, count=5)
    
    if tweets:
        logger.info(f"Found {len(tweets)} tweets from @{username}")
        if len(tweets) > 0:
            sample_tweet = tweets[0]
            logger.info(f"Sample tweet: {json.dumps(sample_tweet, indent=2)[:200]}...")
    else:
        logger.warning(f"No tweets found for @{username}")

async def test_get_trends(client: TwitterClient):
    """Test getting current Twitter trends"""
    logger.info("===== Testing Get Trends =====")
    
    trends = await client.get_trends()
    
    if trends:
        logger.info(f"Found {len(trends)} trends")
        if len(trends) > 0:
            sample_trend = trends[0]
            logger.info(f"Sample trend: {json.dumps(sample_trend, indent=2)}")
    else:
        logger.warning("No trends found")

async def run_all_tests():
    """Run all tests sequentially"""
    # Load environment variables
    load_dotenv()
    
    # Test login
    client = await test_login()
    
    # Test search tweets
    await test_search_tweets(client, "SonicLabs")
    
    # Test search for crypto-related tweets
    await test_search_tweets(client, "cryptocurrency")
    
    # Test get user tweets
    await test_get_user_tweets(client, "AndreCronjeTech")
    
    # Test get user tweets for SonicLabs
    await test_get_user_tweets(client, "SonicLabs")
    
    # Test get trends
    await test_get_trends(client)
    
    logger.info("===== All Tests Completed =====")

async def main():
    """Main entry point"""
    try:
        await run_all_tests()
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        
if __name__ == "__main__":
    asyncio.run(main())