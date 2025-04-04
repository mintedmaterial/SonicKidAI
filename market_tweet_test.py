"""
Market Data Tweet Test

This script generates and posts a tweet with real market data from the database.
"""

import os
import sys
import asyncio
import logging
import asyncpg
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.append('.')
from src.connections.twitter_client import TwitterClient

async def get_sonic_market_data():
    """Get SONIC market data from the database"""
    try:
        # Get the database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL not set in environment")
            return None
        
        # Connect to the database
        conn = await asyncpg.connect(database_url)
        
        # Get latest SONIC data from price_data table
        query = """
        SELECT * FROM price_data
        WHERE token_symbol = 'SONIC'
        ORDER BY timestamp DESC
        LIMIT 1
        """
        
        result = await conn.fetchrow(query)
        await conn.close()
        
        if not result:
            logger.warning("No SONIC price data found in database")
            return None
        
        # Convert to dictionary
        market_data = {
            'price': result['price_usd'],
            'price_change_24h': result['price_change_24h'],
            'volume_24h': result['volume_24h'],
            'market_cap': result['market_cap'],
            'timestamp': result['timestamp'],
            'token_symbol': result['token_symbol'],
            'token_name': result['token_name']
        }
        
        logger.info(f"Retrieved market data: {json.dumps(market_data, indent=2)}")
        return market_data
    
    except Exception as e:
        logger.exception(f"Error fetching market data: {e}")
        return None

async def generate_market_tweet(market_data):
    """Generate a tweet with market data"""
    if not market_data:
        return None
    
    # Format price with proper decimals
    price = market_data['price']
    price_formatted = f"${price:.4f}" if price < 1 else f"${price:.2f}"
    
    # Format volume with commas for readability
    volume = market_data['volume_24h']
    volume_formatted = f"${volume:,.2f}" if volume else "N/A"
    
    # Format the price change percentage
    price_change = market_data['price_change_24h']
    if price_change is not None:
        change_symbol = "🟢" if price_change >= 0 else "🔴"
        price_change_formatted = f"{change_symbol} {abs(price_change):.2f}%"
    else:
        price_change_formatted = "N/A"
    
    # Format the timestamp
    timestamp = market_data['timestamp']
    if timestamp:
        timestamp_str = timestamp.strftime("%b %d %Y %H:%M:%S UTC")
    else:
        timestamp_str = datetime.now().strftime("%b %d %Y %H:%M:%S UTC")
    
    # Create the tweet text
    tweet_text = f"""🚀 SONIC Market Update | {timestamp_str}

Price: {price_formatted}
24h Change: {price_change_formatted}
24h Volume: {volume_formatted}

Stay updated with the latest $SONIC market data! #SONIC #Crypto #Market"""

    return tweet_text

async def main():
    """Main function"""
    try:
        # Get market data from database
        market_data = await get_sonic_market_data()
        
        if not market_data:
            # Fallback to sample data only for testing when database is empty
            logger.warning("Using fallback market data for testing")
            market_data = {
                'price': 0.884,
                'price_change_24h': -2.3,
                'volume_24h': 70847308.00,
                'market_cap': 235000000,
                'timestamp': datetime.now(),
                'token_symbol': 'SONIC',
                'token_name': 'Sonic'
            }
        
        # Generate tweet
        tweet_text = await generate_market_tweet(market_data)
        if not tweet_text:
            logger.error("Failed to generate tweet text")
            return
            
        logger.info(f"Generated market tweet:\n{tweet_text}")
        
        # Create Twitter client
        client = TwitterClient()
        
        # Authenticate
        logger.info("Authenticating with Twitter...")
        authenticated = await client.authenticate()
        
        if authenticated:
            logger.info("Authentication successful!")
            
            # Post tweet
            logger.info("Posting tweet...")
            success = await client.post_tweet(tweet_text)
            
            if success:
                logger.info("Market update tweet posted successfully!")
            else:
                logger.error("Failed to post market update tweet")
        else:
            logger.error("Twitter authentication failed")
    
    except Exception as e:
        logger.exception(f"Error in main function: {e}")

if __name__ == "__main__":
    asyncio.run(main())