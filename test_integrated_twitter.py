"""
Twitter Client Integration Test

This script tests the integrated Twitter client using real market data.
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any, List
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the project root to the path
sys.path.append('.')

from src.connections.twitter_client import TwitterClient

async def get_market_data() -> Dict[str, Any]:
    """Get SONIC market data from the database - ONLY REAL DATA, NO FALLBACKS"""
    from asyncpg import create_pool
    
    # Connect to the database
    conn_str = os.environ.get('DATABASE_URL')
    if not conn_str:
        logger.error("DATABASE_URL environment variable not set")
        raise ValueError("DATABASE_URL environment variable not set - cannot proceed without real data")
    
    pool = await create_pool(conn_str)
    async with pool.acquire() as conn:
        # Get the latest SONIC price
        price_row = await conn.fetchrow(
            """
            SELECT price, volume_24h, price_change_24h 
            FROM sonic_price_feed 
            ORDER BY timestamp DESC 
            LIMIT 1
            """
        )
        
        if not price_row:
            raise ValueError("No price data found for SONIC in the database - cannot proceed without real data")
        
        # Get market sentiment
        sentiment_row = await conn.fetchrow(
            """
            SELECT overall_sentiment 
            FROM market_sentiment 
            WHERE token_symbol = 'SONIC' 
            ORDER BY timestamp DESC 
            LIMIT 1
            """
        )
        
        # Get whale alerts
        whales = await conn.fetch(
            """
            SELECT amount, token_from, token_to, transaction_type 
            FROM whale_alerts 
            WHERE token_symbol = 'SONIC' 
            ORDER BY timestamp DESC 
            LIMIT 3
            """
        )
        
        # Get Twitter feed data for additional context
        tweets = await conn.fetch(
            """
            SELECT tweet_text, sentiment, importance_score
            FROM twitter_feed
            WHERE LOWER(tweet_text) LIKE '%sonic%' 
            ORDER BY created_at DESC
            LIMIT 5
            """
        )
        
        # Format the data - NO FALLBACKS, ONLY REAL DATA
        data = {
            "price": price_row["price"],
            "volume": price_row["volume_24h"],
            "change": price_row["price_change_24h"],
            "sentiment": sentiment_row["overall_sentiment"] if sentiment_row else None,
            "whales": [
                {
                    "amount": w["amount"],
                    "from": w["token_from"],
                    "to": w["token_to"],
                    "type": w["transaction_type"]
                } for w in whales
            ],
            "related_tweets": [
                {
                    "text": t["tweet_text"],
                    "sentiment": t["sentiment"],
                    "importance": t["importance_score"]
                } for t in tweets
            ]
        }
        
        # Verify we have the essential data
        if data["price"] is None or data["volume"] is None or data["change"] is None:
            raise ValueError("Missing essential price data - cannot proceed without real data")
            
        return data

def generate_tweet_content(market_data: Dict[str, Any]) -> str:
    """Generate tweet content based on REAL market data"""
    # Format price with 3 decimal places
    price = "{:.3f}".format(market_data["price"])
    
    # Format volume with commas for readability
    volume = "{:,.2f}".format(market_data["volume"])
    
    # Format change with sign and percentage
    change = market_data["change"]
    change_str = "+" if change >= 0 else ""
    change_str += f"{change:.2f}%"
    
    # Get sentiment (with null handling)
    sentiment = market_data["sentiment"] if market_data["sentiment"] else "neutral"
    
    # Current date
    date = datetime.now().strftime("%b %d")
    
    # Include whale information if available
    whale_info = ""
    if market_data["whales"] and len(market_data["whales"]) > 0:
        # Get the largest whale transaction
        largest_whale = max(market_data["whales"], key=lambda w: w["amount"]) if market_data["whales"] else None
        if largest_whale:
            whale_amount = "{:,.2f}".format(largest_whale["amount"])
            whale_type = largest_whale["type"].replace("_", " ").title()
            whale_info = f"\n🐋 Whale Activity: {whale_type} {whale_amount} SONIC"
    
    # Get top tweet sentiment if available
    market_insight = ""
    if market_data["related_tweets"] and len(market_data["related_tweets"]) > 0:
        # Find the most important tweet
        important_tweets = sorted(market_data["related_tweets"], 
                                 key=lambda t: t["importance"] if t["importance"] is not None else 0, 
                                 reverse=True)
        if important_tweets:
            top_tweet = important_tweets[0]
            if top_tweet["sentiment"]:
                sentiment_emoji = "🔥" if top_tweet["sentiment"] == "positive" else "❄️" if top_tweet["sentiment"] == "negative" else "⚖️"
                market_insight = f"\n{sentiment_emoji} Community: {top_tweet['sentiment'].title()} sentiment trending"
    
    # Emoji for price movement
    price_emoji = "📈" if change >= 3.0 else "📊" if change >= 0 else "📉"
    sentiment_emoji = "🔥" if sentiment == "bullish" else "⚖️" if sentiment == "neutral" else "❄️"
    
    # Create tweet content with real data
    tweet = f"""#BanditKid $SONIC Market Update - {date} {price_emoji}

💰 Price: ${price} ({change_str})
📊 24h Volume: ${volume}
{sentiment_emoji} Market Sentiment: {sentiment.title()}{whale_info}{market_insight}

#Sonic #SOL #Crypto #DeFi"""

    return tweet

async def main():
    """Main function"""
    try:
        # Get market data
        logger.info("Getting market data...")
        market_data = await get_market_data()
        logger.info(f"Market data: {json.dumps(market_data, indent=2)}")
        
        # Generate tweet content
        tweet_text = generate_tweet_content(market_data)
        logger.info(f"Generated tweet:\n{tweet_text}")
        
        # Create Twitter client
        client = TwitterClient()
        
        # Authenticate
        logger.info("Authenticating with Twitter...")
        authenticated = await client.authenticate()
        
        if authenticated:
            logger.info("Authentication successful")
            
            # Post tweet
            logger.info("Posting tweet...")
            success = await client.post_tweet(tweet_text)
            
            if success:
                logger.info("Tweet posted successfully!")
            else:
                logger.error("Failed to post tweet")
        else:
            logger.error("Twitter authentication failed")
    
    except Exception as e:
        logger.exception(f"Error in main function: {e}")

if __name__ == "__main__":
    asyncio.run(main())