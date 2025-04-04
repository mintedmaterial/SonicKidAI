"""
Simple Twitter Post Test

This script uses the agent-twitter-client library to post a pre-generated tweet
without any complex data retrieval or processing.
"""

import os
import sys
import json
import logging
import asyncio
import tempfile
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("python-dotenv not found, assuming environment variables are set")

class TwitterPostClient:
    """Client for posting tweets to Twitter"""
    
    def __init__(self):
        """Initialize the Twitter client"""
        self.auth_token = os.getenv("TWITTER_AUTH_TOKEN")
        if not self.auth_token:
            raise ValueError("TWITTER_AUTH_TOKEN environment variable not set")
        
        logger.info("TwitterPostClient initialized")
        
    async def authenticate(self) -> bool:
        """Authenticate with Twitter"""
        try:
            # Create and run the auth script
            auth_script = self._create_auth_script()
            result = await self._run_node_script(auth_script)
            
            if result and "Bearer token" in result:
                logger.info("Authentication successful")
                return True
            else:
                logger.error(f"Authentication failed: {result}")
                return False
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            return False
    
    async def post_tweet(self, tweet_text: str) -> bool:
        """Post a tweet to Twitter"""
        try:
            # Create and run the post tweet script
            post_script = self._create_post_tweet_script(tweet_text)
            result = await self._run_node_script(post_script)
            
            if result and "Tweet posted successfully" in result:
                logger.info("Tweet posted successfully")
                return True
            else:
                logger.error(f"Failed to post tweet: {result}")
                return False
        except Exception as e:
            logger.error(f"Error posting tweet: {str(e)}")
            return False
    
    def _create_auth_script(self) -> str:
        """Create Node.js script for authentication"""
        return f"""
        const {{ Scraper }} = require('agent-twitter-client');

        (async () => {{
            try {{
                const auth = {{ auth_token: '{self.auth_token}' }};
                const client = new Scraper(auth);
                const isAuthenticated = await client.isLoggedIn();
                
                if (isAuthenticated) {{
                    console.log('Authentication successful');
                    console.log('Bearer token: ' + client.bearerToken);
                }} else {{
                    console.log('Authentication failed');
                }}
            }} catch (error) {{
                console.error('Error:', error.message);
            }}
        }})();
        """
    
    def _create_post_tweet_script(self, tweet_text: str) -> str:
        """Create Node.js script for posting a tweet"""
        # Escape any quotes in the tweet text
        safe_tweet = tweet_text.replace("'", "\\'").replace('"', '\\"')
        
        return f"""
        const {{ Scraper }} = require('agent-twitter-client');

        (async () => {{
            try {{
                const auth = {{ auth_token: '{self.auth_token}' }};
                const client = new Scraper(auth);
                const isAuthenticated = await client.isLoggedIn();
                
                if (isAuthenticated) {{
                    console.log('Authentication successful, posting tweet...');
                    const result = await client.tweet('{safe_tweet}');
                    console.log('Tweet posted successfully:', JSON.stringify(result));
                }} else {{
                    console.log('Authentication failed, cannot post tweet');
                }}
            }} catch (error) {{
                console.error('Error:', error.message);
            }}
        }})();
        """
    
    async def _run_node_script(self, script: str) -> Optional[str]:
        """
        Run a Node.js script and return its output
        
        Args:
            script: Node.js script to run
            
        Returns:
            Script output or None if an error occurred
        """
        import subprocess
        
        try:
            # Create a temporary file for the script
            with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(script.encode('utf-8'))
            
            # Run the script
            process = await asyncio.create_subprocess_exec(
                'node', temp_file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Clean up the temporary file
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
            
            # Check for errors
            if process.returncode != 0:
                logger.error(f"Script execution failed with return code {process.returncode}")
                logger.error(f"Error output: {stderr.decode('utf-8')}")
                return None
            
            # Return the output
            return stdout.decode('utf-8')
        except Exception as e:
            logger.error(f"Error running Node.js script: {str(e)}")
            return None

async def post_test_tweet():
    """Post a test tweet"""
    # Hardcoded tweet for testing with updated data
    tweet_text = """🚀 SONIC MARKET UPDATE 🚀

Just aped into $SONIC @ $0.872 💰

24h Change: -2.53% 📊

Volume: $394,908.00

Testing tweet posting with our updated auth token! The market is looking interesting today. Let's see if this posts correctly!

#SONIC #DeFi #Crypto #Test"""

    logger.info(f"Test tweet content:\n{tweet_text}")
    logger.info(f"Tweet length: {len(tweet_text)} characters")
    
    # Create client and authenticate
    client = TwitterPostClient()
    auth_success = await client.authenticate()
    
    if not auth_success:
        logger.error("Authentication failed")
        return False
    
    # Post the tweet
    post_success = await client.post_tweet(tweet_text)
    logger.info(f"Tweet posting result: {'Success' if post_success else 'Failed'}")
    return post_success

async def main():
    """Main entry point"""
    logger.info("Starting simple Twitter post test")
    success = await post_test_tweet()
    
    if success:
        logger.info("Test completed successfully")
    else:
        logger.error("Test failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())