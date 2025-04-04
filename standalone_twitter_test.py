"""
Standalone Twitter Test

This script tests Twitter posting functionality without importing complex dependencies.
"""

import os
import sys
import asyncio
import logging
import tempfile
import subprocess
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def authenticate_twitter() -> bool:
    """Authenticate with Twitter using direct login method"""
    try:
        # Run the authentication script
        proc = await asyncio.create_subprocess_exec(
            'node', 'twitter_auth.cjs',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Get the output
        stdout, stderr = await proc.communicate()
        output = stdout.decode('utf-8')
        error_output = stderr.decode('utf-8')
        
        # Check if there was an error
        if proc.returncode != 0:
            logger.error(f"Authentication failed with code {proc.returncode}")
            logger.error(f"Error output: {error_output}")
            return False
        
        # Check if authentication was successful
        if "Login successful? true" in output:
            logger.info("Twitter authentication successful")
            return True
        else:
            logger.error(f"Twitter authentication failed: {output}")
            return False
            
    except Exception as e:
        logger.exception(f"Error running authentication script: {e}")
        return False

async def post_tweet(tweet_text: str) -> bool:
    """Post a tweet to Twitter using the authenticated scraper"""
    if not tweet_text:
        logger.error("Cannot post empty tweet")
        return False
    
    try:
        # Write tweet text to a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(tweet_text)
        
        # Run the post tweet script with the file path
        proc = await asyncio.create_subprocess_exec(
            'node', 'twitter_post.cjs', temp_file_path,
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

This is a standalone test tweet to verify Twitter client functionality.

#SONIC #Test #Crypto"""
        
        logger.info(f"Generated test tweet:\n{tweet_text}")
        
        # Authenticate
        logger.info("Authenticating with Twitter...")
        authenticated = await authenticate_twitter()
        
        if authenticated:
            logger.info("Authentication successful!")
            
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