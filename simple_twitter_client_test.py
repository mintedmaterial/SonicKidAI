"""
Simple Twitter Client Test

This script tests the Twitter client with basic tweet functionality.
"""

import os
import sys
import asyncio
import logging
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

async def main():
    """Main function"""
    try:
        # Generate a simple test tweet
        current_date = datetime.now().strftime("%b %d %H:%M:%S")
        tweet_text = f"""#BanditKid Test Tweet - {current_date}

This is a simple test tweet to verify Twitter client functionality with direct scripts.

#Test #Automation"""
        
        logger.info(f"Generated test tweet:\n{tweet_text}")
        
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
                logger.info("Tweet posted successfully!")
            else:
                logger.error("Failed to post tweet")
        else:
            logger.error("Twitter authentication failed")
    
    except Exception as e:
        logger.exception(f"Error in main function: {e}")

if __name__ == "__main__":
    asyncio.run(main())