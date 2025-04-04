"""
Minimal Twitter Client Test

This script tests the Twitter client with minimal dependencies.
"""

import os
import json
import asyncio
import logging
import tempfile
from datetime import datetime
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        # Generate a simple test tweet
        current_date = datetime.now().strftime("%b %d %H:%M:%S")
        tweet_text = f"""#BanditKid Test Tweet - {current_date}

This is a minimal test tweet to verify Twitter client functionality.

#Test #Automation"""
        
        logger.info(f"Generated test tweet:\n{tweet_text}")
        
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