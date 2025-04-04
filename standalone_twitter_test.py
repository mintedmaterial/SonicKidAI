"""
Standalone Twitter Client Test

This script tests the Twitter client using real market data without dependencies on
the existing codebase. It implements authentication and posting directly.
"""

import os
import sys
import json
import asyncio
import logging
import asyncpg
import tempfile
from typing import Dict, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def get_db_data() -> Dict[str, Any]:
    """Get SONIC market data from the database - ONLY REAL DATA"""
    # Connect to the database
    conn_str = os.environ.get('DATABASE_URL')
    if not conn_str:
        logger.error("DATABASE_URL environment variable not set")
        raise ValueError("DATABASE_URL environment variable not set - cannot proceed without real data")
    
    try:
        # Create connection pool
        pool = await asyncpg.create_pool(conn_str)
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
            
            # Format the data - NO FALLBACKS, ONLY REAL DATA
            data = {
                "price": price_row["price"],
                "volume": price_row["volume_24h"],
                "change": price_row["price_change_24h"]
            }
            
            # Verify we have the essential data
            if data["price"] is None or data["volume"] is None or data["change"] is None:
                raise ValueError("Missing essential price data - cannot proceed without real data")
                
            logger.info(f"Retrieved market data: {json.dumps(data, indent=2)}")
            return data
    except Exception as e:
        logger.exception(f"Database error: {e}")
        raise

def generate_tweet(market_data: Dict[str, Any]) -> str:
    """Generate tweet content based on REAL market data"""
    # Format price with 3 decimal places
    price = "{:.4f}".format(market_data["price"])
    
    # Format volume with commas for readability
    volume = "{:,.2f}".format(market_data["volume"])
    
    # Format change with sign and percentage
    change = market_data["change"]
    change_str = "+" if change >= 0 else ""
    change_str += f"{change:.2f}%"
    
    # Current date
    date = datetime.now().strftime("%b %d")
    
    # Emoji for price movement
    price_emoji = "📈" if change >= 3.0 else "📊" if change >= 0 else "📉"
    
    # Create tweet content with real data
    tweet = f"""#BanditKid $SONIC Market Update - {date} {price_emoji}

💰 Price: ${price} ({change_str})
📊 24h Volume: ${volume}

#Sonic #SOL #Crypto #DeFi"""

    return tweet

async def authenticate_twitter() -> bool:
    """Authenticate with Twitter using direct login method"""
    try:
        # Get credentials from environment
        username = os.environ.get('TWITTER_USERNAME')
        password = os.environ.get('TWITTER_PASSWORD')
        email = os.environ.get('TWITTER_EMAIL')
        
        if not username or not password or not email:
            logger.error("Twitter credentials not set in environment variables")
            return False
        
        # Create the Node.js script for authentication
        auth_script = f"""
const {{ Scraper }} = require('agent-twitter-client');

async function authenticate() {{
    try {{
        // Log environment variables being used (without showing values)
        console.log('Using environment variables:');
        console.log('- TWITTER_USERNAME: ' + (process.env.TWITTER_USERNAME ? 'Set' : 'Not set'));
        console.log('- TWITTER_PASSWORD: ' + (process.env.TWITTER_PASSWORD ? 'Set' : 'Not set'));
        console.log('- TWITTER_EMAIL: ' + (process.env.TWITTER_EMAIL ? 'Set' : 'Not set'));
        
        // Create a new scraper instance
        const scraper = new Scraper();
        console.log('Created new scraper instance');
        
        // Login with credentials
        console.log('Attempting to login with environment credentials');
        await scraper.login(
            process.env.TWITTER_USERNAME,
            process.env.TWITTER_PASSWORD,
            process.env.TWITTER_EMAIL
        );
        
        // Check if login was successful
        const isLoggedIn = await scraper.isLoggedIn();
        console.log('Login successful?', isLoggedIn);
        
        if (isLoggedIn) {{
            // Get user profile
            const profile = await scraper.me();
            console.log('User profile:', JSON.stringify(profile, null, 2));
            
            // Get the cookies for future use
            const cookies = await scraper.getCookies();
            console.log('Cookies for future use:', JSON.stringify(cookies));
        }}
        
        process.exit(isLoggedIn ? 0 : 1);
    }} catch (error) {{
        console.error('Error during authentication:', error.message);
        console.error(error.stack);
        process.exit(1);
    }}
}}

authenticate();
"""
        
        # Run the authentication script
        with tempfile.NamedTemporaryFile(suffix='.cjs', mode='w', delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(auth_script)
        
        # Run the script using Node.js
        proc = await asyncio.create_subprocess_exec(
            'node', temp_file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Get the output
        stdout, stderr = await proc.communicate()
        output = stdout.decode('utf-8')
        error_output = stderr.decode('utf-8')
        
        # Clean up the temporary file
        os.unlink(temp_file_path)
        
        # Check if there was an error
        if proc.returncode != 0:
            logger.error(f"Authentication failed with code {proc.returncode}")
            logger.error(f"Error output: {error_output}")
            return False
        
        logger.info("Authentication output:")
        logger.info(output)
        
        # Check if authentication was successful
        if "Login successful? true" in output:
            logger.info("Twitter authentication successful")
            return True
        else:
            logger.error(f"Twitter authentication failed: {output}")
            return False
    
    except Exception as e:
        logger.exception(f"Error during authentication: {e}")
        return False

async def post_tweet(tweet_text: str) -> bool:
    """Post a tweet to Twitter using the authenticated scraper"""
    try:
        if not tweet_text:
            logger.error("Cannot post empty tweet")
            return False
        
        # Escape any special characters in the tweet text
        safe_tweet_text = tweet_text.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
        
        # Create the Node.js script for posting the tweet
        post_script = f"""
const {{ Scraper }} = require('agent-twitter-client');

async function postTweet() {{
    try {{
        // Create a new scraper instance
        const scraper = new Scraper();
        console.log('Created new scraper instance');
        
        // Login with credentials
        console.log('Logging in with credentials from environment variables');
        await scraper.login(
            process.env.TWITTER_USERNAME,
            process.env.TWITTER_PASSWORD,
            process.env.TWITTER_EMAIL
        );
        
        // Check if login was successful
        const isLoggedIn = await scraper.isLoggedIn();
        console.log('Login successful?', isLoggedIn);
        
        if (!isLoggedIn) {{
            console.error('Failed to log in to Twitter');
            process.exit(1);
        }}
        
        // Tweet content
        const tweetText = `{safe_tweet_text}`;
        console.log(`Tweet content (${{tweetText.length}} chars):\\n${{tweetText}}`);
        
        // Post the tweet
        console.log('Posting tweet...');
        const result = await scraper.sendTweet(tweetText);
        console.log('Tweet posted successfully:', JSON.stringify(result));
        process.exit(0);
    }} catch (error) {{
        console.error('Error posting tweet:', error.message);
        console.error(error.stack);
        process.exit(1);
    }}
}}

postTweet();
"""
        
        # Run the post tweet script
        with tempfile.NamedTemporaryFile(suffix='.cjs', mode='w', delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(post_script)
        
        # Run the script using Node.js
        proc = await asyncio.create_subprocess_exec(
            'node', temp_file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Get the output
        stdout, stderr = await proc.communicate()
        output = stdout.decode('utf-8')
        error_output = stderr.decode('utf-8')
        
        # Clean up the temporary file
        os.unlink(temp_file_path)
        
        # Check if there was an error
        if proc.returncode != 0:
            logger.error(f"Tweet posting failed with code {proc.returncode}")
            logger.error(f"Error output: {error_output}")
            return False
        
        logger.info("Tweet posting output:")
        logger.info(output)
        
        # Check if the tweet was posted successfully
        if "Tweet posted successfully" in output:
            logger.info("Tweet posted successfully")
            return True
        else:
            logger.error(f"Failed to post tweet: {output}")
            return False
    
    except Exception as e:
        logger.exception(f"Error posting tweet: {e}")
        return False

async def main():
    """Main function"""
    try:
        # Get market data
        logger.info("Getting market data...")
        market_data = await get_db_data()
        
        # Generate tweet content
        tweet_text = generate_tweet(market_data)
        logger.info(f"Generated tweet:\n{tweet_text}")
        
        # Authenticate with Twitter
        logger.info("Authenticating with Twitter...")
        authenticated = await authenticate_twitter()
        
        if authenticated:
            logger.info("Authentication successful")
            
            # Post tweet
            logger.info("Posting tweet...")
            success = await post_tweet(tweet_text)
            
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