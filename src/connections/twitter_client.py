"""
Twitter Client Implementation

This module provides a Twitter client for posting tweets with 
authentication using username/password/email from environment variables.
"""

import os
import json
import asyncio
import logging
import tempfile
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class TwitterClient:
    """Twitter Client for posting tweets using agent-twitter-client"""
    
    def __init__(self):
        """Initialize the Twitter client"""
        self.username = os.environ.get('TWITTER_USERNAME', '')
        self.password = os.environ.get('TWITTER_PASSWORD', '')
        self.email = os.environ.get('TWITTER_EMAIL', '')
        self.auth_token = os.environ.get('TWITTER_AUTH_TOKEN', '')
        self.cookies_json = os.environ.get('TWITTER_COOKIES', '')
        self.cookies = None
        
        if self.cookies_json:
            try:
                self.cookies = json.loads(self.cookies_json)
            except json.JSONDecodeError:
                logger.error("Failed to parse TWITTER_COOKIES from environment")
                self.cookies = None
    
    async def authenticate(self) -> bool:
        """Authenticate with Twitter
        
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        # Create a temporary Node.js script for authentication
        script = self._create_auth_script()
        
        # Execute the script and get the output
        output = await self._run_node_script(script)
        if not output:
            logger.error("Failed to run authentication script")
            return False
        
        # Check if authentication was successful
        if "Login successful? true" in output:
            logger.info("Twitter authentication successful")
            return True
        else:
            logger.error(f"Twitter authentication failed: {output}")
            return False
    
    async def post_tweet(self, tweet_text: str) -> bool:
        """Post a tweet to Twitter
        
        Args:
            tweet_text: The text of the tweet to post
            
        Returns:
            bool: True if the tweet was posted successfully, False otherwise
        """
        if not tweet_text:
            logger.error("Cannot post empty tweet")
            return False
        
        # Create a temporary Node.js script for posting the tweet
        script = self._create_post_tweet_script(tweet_text)
        
        # Execute the script and get the output
        output = await self._run_node_script(script)
        if not output:
            logger.error("Failed to run tweet posting script")
            return False
        
        # Check if the tweet was posted successfully
        if "Tweet posted successfully" in output:
            logger.info("Tweet posted successfully")
            return True
        else:
            logger.error(f"Failed to post tweet: {output}")
            return False
    
    def _create_auth_script(self) -> str:
        """Create Node.js script for authentication
        
        Returns:
            str: JavaScript code for authenticating with Twitter
        """
        return """
            const { Scraper } = require('agent-twitter-client');
            
            async function authenticate() {
                try {
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
                    
                    if (isLoggedIn) {
                        // Get user profile
                        const profile = await scraper.me();
                        console.log('User profile:', JSON.stringify(profile, null, 2));
                        
                        // Get the cookies for future use
                        const cookies = await scraper.getCookies();
                        console.log('Cookies for future use:', JSON.stringify(cookies));
                    }
                    
                    process.exit(isLoggedIn ? 0 : 1);
                } catch (error) {
                    console.error('Error during authentication:', error.message);
                    console.error(error.stack);
                    process.exit(1);
                }
            }
            
            authenticate();
        """
    
    def _create_post_tweet_script(self, tweet_text: str) -> str:
        """Create Node.js script for posting a tweet
        
        Args:
            tweet_text: The text of the tweet to post
            
        Returns:
            str: JavaScript code for posting a tweet
        """
        # Escape any special characters in the tweet text
        safe_tweet_text = tweet_text.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
        
        return f"""
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
    
    async def _run_node_script(self, script: str) -> Optional[str]:
        """
        Run a Node.js script and return its output
        
        Args:
            script: Node.js script to run
            
        Returns:
            Script output or None if an error occurred
        """
        try:
            # Create a temporary file to hold the script
            with tempfile.NamedTemporaryFile(suffix='.cjs', mode='w', delete=False) as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(script)
            
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
                logger.error(f"Script execution failed with code {proc.returncode}")
                logger.error(f"Error output: {error_output}")
                return None
            
            return output
        except Exception as e:
            logger.exception(f"Error running Node.js script: {e}")
            return None