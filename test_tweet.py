"""
Test Twitter Client Implementation using ElizaOS agent-twitter-client

This script tests the ElizaOS Twitter client integration, which doesn't require
Twitter API keys. It demonstrates basic Twitter functionality including:
- Reading tweets
- Posting tweets
- Following users
- Getting trending topics

Usage:
    python test_tweet.py
"""

import os
import json
import asyncio
import logging
from datetime import datetime
import subprocess
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG level to see more information
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Twitter credentials from environment variables
# Load environment variables from .env file
try:
    load_dotenv()
    logger.info("Environment variables loaded from .env file")
except Exception as e:
    logger.warning(f"Could not load environment variables from .env file: {str(e)}")

# Get Twitter credentials from environment variables
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME", "")
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD", "")
TWITTER_EMAIL = os.getenv("TWITTER_EMAIL", "")
TWITTER_COOKIES = os.getenv("TWITTER_COOKIES", "")

# Debug output for credentials (safely masked)
logger.debug(f"Username: '{TWITTER_USERNAME}'")
logger.debug(f"Email: '{TWITTER_EMAIL}'")
logger.debug(f"Password length: {len(TWITTER_PASSWORD)}")

logger.info(f"Twitter credentials loaded. Username: {TWITTER_USERNAME and 'YES' or 'NO'}, " +
            f"Password: {TWITTER_PASSWORD and 'YES' or 'NO'}, " +
            f"Email: {TWITTER_EMAIL and 'YES' or 'NO'}, " +
            f"Cookies: {TWITTER_COOKIES and 'YES' or 'NO'}")

# Note: We'll build the Node.js script template dynamically to avoid string formatting issues

def get_auth_code():
    """Generate authentication code based on available credentials"""
    # Try different authentication methods in order of preference
    auth_token = os.getenv("TWITTER_AUTH_TOKEN")
    
    if TWITTER_COOKIES and TWITTER_COOKIES.strip():
        # Use pre-formatted cookies if available
        logger.info("Using Twitter cookies for authentication")
        
        # Check if the cookies string is already properly formatted
        if TWITTER_COOKIES.startswith('[') and ']' in TWITTER_COOKIES:
            return f"await scraper.setCookies({TWITTER_COOKIES});"
    
    # If we have an auth token, format it as cookies
    elif auth_token and auth_token.strip():
        logger.info(f"Using Twitter auth token for authentication")
        return f"""
            await scraper.setCookies([{{
                name: "auth_token",
                value: "{auth_token}",
                domain: ".twitter.com",
                path: "/",
                expires: -1,
                httpOnly: true,
                secure: true
            }}]);
        """
    
    # If no cookies or token, try username/password
    elif TWITTER_USERNAME and TWITTER_PASSWORD:
        if TWITTER_EMAIL:
            logger.info(f"Using Twitter username '{TWITTER_USERNAME}', password, and email '{TWITTER_EMAIL}' for authentication")
            return f"await scraper.login('{TWITTER_USERNAME}', '{TWITTER_PASSWORD}', '{TWITTER_EMAIL}');"
        else:
            logger.info(f"Using Twitter username '{TWITTER_USERNAME}' and password for authentication")
            return f"await scraper.login('{TWITTER_USERNAME}', '{TWITTER_PASSWORD}');"
    
    # Fallback to no authentication
    else:
        logger.warning("No authentication credentials available")
        return "console.log('No authentication credentials available');"

async def run_twitter_operation(operation_code):
    """Run a Twitter operation via Node.js"""
    auth_code = get_auth_code()
    
    # Generate the full Node.js script without using string formatting
    script_parts = [
        "// Use CommonJS syntax for requiring the module",
        "const twitterClient = require('agent-twitter-client');",
        "const Scraper = twitterClient.Scraper;",
        "const SearchMode = twitterClient.SearchMode;",
        "",
        "async function runTwitterOperation() {",
        "    try {",
        "        // Initialize the scraper with debug option",
        "        const scraper = new Scraper({ debug: true });",
        "        ",
        "        console.log('Attempting authentication...');",
        "        // Setup authentication",
        f"        {auth_code}",
        "        console.log('Authentication completed');",
        "        ",
        "        console.log('Executing operation...');",
        "        // Perform the operation",
        f"        {operation_code}",
        "        console.log('Operation completed successfully');",
        "        ",
        "    } catch (error) {",
        "        console.error('Error:', JSON.stringify(error, null, 2));",
        "        console.error('Error message:', error.message);",
        "        process.exit(1);",
        "    }",
        "}",
        "",
        "runTwitterOperation();"
    ]
    
    script = "\n".join(script_parts)
    
    # Create a temporary JS file with a .cjs extension for CommonJS
    temp_script_path = "temp_twitter_op.cjs"
    with open(temp_script_path, "w") as f:
        f.write(script)
    
    logger.debug(f"Generated script:\n{script}")
    
    try:
        # Run the Node.js script
        logger.debug("Executing Node.js script...")
        result = subprocess.run(
            ["node", temp_script_path],
            capture_output=True,
            text=True,
            check=False  # Don't raise exception on non-zero exit
        )
        
        # Log output regardless of success
        if result.stdout:
            logger.debug(f"Script stdout: {result.stdout}")
        
        # Check for errors
        if result.returncode != 0:
            logger.error(f"Script failed with exit code {result.returncode}")
            if result.stderr:
                logger.error(f"Script stderr: {result.stderr}")
            return None
        
        return result.stdout.strip()
    except Exception as e:
        logger.error(f"Error running Twitter operation: {str(e)}", exc_info=True)
        return None
    finally:
        # Clean up temporary file
        if os.path.exists(temp_script_path):
            os.remove(temp_script_path)

async def get_twitter_trends():
    """Get current Twitter trending topics"""
    operation = """
        const trends = await scraper.getTrends();
        console.log(JSON.stringify(trends));
    """
    return await run_twitter_operation(operation)

async def get_user_tweets(username, count=10):
    """Get tweets from a specific user"""
    operation = f"""
        const tweets = await scraper.getTweets('{username}', {count});
        console.log(JSON.stringify(tweets));
    """
    return await run_twitter_operation(operation)

async def get_tweet_by_id(tweet_id):
    """Get a specific tweet by ID"""
    operation = f"""
        const tweet = await scraper.getTweet('{tweet_id}');
        console.log(JSON.stringify(tweet));
    """
    return await run_twitter_operation(operation)

async def post_tweet(text):
    """Post a new tweet"""
    operation = f"""
        const result = await scraper.sendTweet('{text}');
        console.log(JSON.stringify(result));
    """
    return await run_twitter_operation(operation)

async def search_tweets(query, count=10):
    """Search for tweets matching a query"""
    operation = f"""
        const tweets = await scraper.searchTweets('{query}', {count}, SearchMode.Latest);
        console.log(JSON.stringify(tweets));
    """
    return await run_twitter_operation(operation)

async def get_user_profile(username):
    """Get a user's profile information"""
    operation = f"""
        const profile = await scraper.getProfile('{username}');
        console.log(JSON.stringify(profile));
    """
    return await run_twitter_operation(operation)

async def follow_user(username):
    """Follow a user on Twitter"""
    operation = f"""
        const result = await scraper.followUser('{username}');
        console.log(JSON.stringify(result));
    """
    return await run_twitter_operation(operation)

async def store_twitter_cookies():
    """Store Twitter cookies for future use"""
    operation = """
        const cookies = await scraper.getCookies();
        console.log(JSON.stringify(cookies));
    """
    cookies_json = await run_twitter_operation(operation)
    if cookies_json:
        logger.info("Twitter cookies retrieved successfully")
        logger.info("You can set these as TWITTER_COOKIES in your environment variables")
        return cookies_json
    return None

async def get_twitter_home_timeline(count=10):
    """Get the home timeline (requires authentication)"""
    operation = f"""
        const timeline = await scraper.fetchHomeTimeline({count});
        console.log(JSON.stringify(timeline));
    """
    return await run_twitter_operation(operation)

async def test_twitter_functionality():
    """Test various Twitter functions"""
    logger.info("Testing Twitter client functionality...")
    
    # Test if we have valid credentials
    if not (TWITTER_USERNAME and TWITTER_PASSWORD) and not TWITTER_COOKIES:
        logger.warning("No Twitter credentials found. Set TWITTER_USERNAME and TWITTER_PASSWORD or TWITTER_COOKIES")
        logger.info("Running in limited functionality mode (read-only for public data)")
    
    # Get trending topics
    logger.info("Fetching trending topics...")
    trends = await get_twitter_trends()
    if trends:
        logger.info(f"Successfully retrieved trending topics")
        trends_data = json.loads(trends)
        for i, trend in enumerate(trends_data[:5], 1):
            logger.info(f"  {i}. {trend.get('name', 'Unknown')} - {trend.get('tweet_volume', 'N/A')} tweets")
    
    # Get tweets from a popular account
    test_account = "elonmusk"
    logger.info(f"Fetching tweets from {test_account}...")
    tweets = await get_user_tweets(test_account, 3)
    if tweets:
        logger.info(f"Successfully retrieved tweets from {test_account}")
        try:
            tweets_data = json.loads(tweets)
            for i, tweet in enumerate(tweets_data[:3], 1):
                logger.info(f"  {i}. {tweet.get('text', 'No text')[:50]}...")
        except json.JSONDecodeError:
            logger.error("Error parsing tweets JSON")
    
    # Get user profile
    logger.info(f"Fetching profile for {test_account}...")
    profile = await get_user_profile(test_account)
    if profile:
        logger.info(f"Successfully retrieved profile for {test_account}")
        try:
            profile_data = json.loads(profile)
            logger.info(f"  Name: {profile_data.get('name', 'Unknown')}")
            logger.info(f"  Bio: {profile_data.get('description', 'No bio')[:50]}...")
            logger.info(f"  Followers: {profile_data.get('followers_count', 'Unknown')}")
        except json.JSONDecodeError:
            logger.error("Error parsing profile JSON")
    
    # If we have credentials, test authenticated functions
    if (TWITTER_USERNAME and TWITTER_PASSWORD) or TWITTER_COOKIES:
        # Get home timeline
        logger.info("Fetching home timeline...")
        timeline = await get_twitter_home_timeline(5)
        if timeline:
            logger.info("Successfully retrieved home timeline")
            try:
                timeline_data = json.loads(timeline)
                for i, tweet in enumerate(timeline_data[:3], 1):
                    logger.info(f"  {i}. {tweet.get('text', 'No text')[:50]}...")
            except json.JSONDecodeError:
                logger.error("Error parsing timeline JSON")
        
        # Post a test tweet
        test_tweet_text = f"Testing agent-twitter-client integration at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        logger.info(f"Posting test tweet: {test_tweet_text}")
        post_result = await post_tweet(test_tweet_text)
        if post_result:
            logger.info("Successfully posted tweet")
            try:
                post_data = json.loads(post_result)
                logger.info(f"  Tweet ID: {post_data.get('id', 'Unknown')}")
            except json.JSONDecodeError:
                logger.error("Error parsing post result JSON")
        
        # Store cookies for future use
        logger.info("Storing Twitter cookies...")
        await store_twitter_cookies()
    
    logger.info("Twitter client test completed")

async def main():
    """Main entry point"""
    try:
        await test_twitter_functionality()
    except Exception as e:
        logger.error(f"Error in Twitter test: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())