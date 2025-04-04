"""
Simplified Twitter Client Test

This standalone script tests Twitter functionality with the agent-twitter-client
NodeJS package without requiring other project dependencies.
"""

import os
import json
import logging
import asyncio
import subprocess
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class SimpleTwitterTest:
    """Simple Twitter client test"""
    
    def __init__(self):
        """Initialize the test client"""
        # Get credentials from environment variables
        self.username = os.environ.get("TWITTER_USERNAME", "MintedMaterial")
        self.password = os.environ.get("TWITTER_PASSWORD", "Myrecovery@1")
        self.email = os.environ.get("TWITTER_EMAIL", "MintedMaterial@gmail.com")
        self.auth_token = os.environ.get("TWITTER_AUTH_TOKEN", "30a88ac3c27a5a2b88742e38d6cbe71cf3663cb3")
        
        # Set cookie string format (used for authentication)
        self.cookie_str = os.environ.get("TWITTER_COOKIES", 
            '[{"name":"auth_token","value":"30a88ac3c27a5a2b88742e38d6cbe71cf3663cb3","domain":".twitter.com",'
            '"path":"/","expires":-1,"httpOnly":true,"secure":true}]'
        )
        
        # Store authentication status
        self.is_authenticated = False
        
        # Log available credentials (without exposing sensitive info)
        logger.info(
            f"Twitter credentials loaded. Username: {'YES' if self.username else 'NO'}, "
            f"Password: {'YES' if self.password else 'NO'}, "
            f"Email: {'YES' if self.email else 'NO'}, "
            f"Auth Token: {'YES' if self.auth_token else 'NO'}, "
            f"Cookies: {'YES' if self.cookie_str else 'NO'}"
        )
    
    async def login(self) -> bool:
        """Login to Twitter with auth token"""
        logger.info("Logging in to Twitter...")
        script = self._create_login_script()
        result = await self._run_node_script(script)
        
        if not result:
            logger.warning("No result returned from login script")
            return False
            
        try:
            # Check for auth success marker
            marker = "AUTH_RESULT:"
            marker_pos = result.find(marker)
            if marker_pos < 0:
                logger.warning("Failed to find auth result marker in output")
                return False
                
            # Extract JSON string
            result_text = result[marker_pos + len(marker):].strip()
            
            # Find JSON boundaries
            json_start = result_text.find('{')
            json_end = result_text.rfind('}')
            
            if json_start < 0 or json_end < 0:
                logger.warning("Failed to find JSON boundaries in auth result")
                return False
                
            json_str = result_text[json_start:json_end + 1]
            
            # Parse JSON
            auth_data = json.loads(json_str)
            self.is_authenticated = auth_data.get("success", False)
            
            return self.is_authenticated
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode auth result JSON: {e}")
            return False
        except Exception as e:
            logger.error(f"Error parsing auth result: {e}")
            return False
    
    async def search_tweets(self, query: str, count: int = 5) -> List[Dict[str, Any]]:
        """Search for tweets with query"""
        logger.info(f"Searching for tweets with query '{query}'")
        
        script = self._create_search_script(query, count)
        result = await self._run_node_script(script)
        
        if not result:
            logger.warning(f"No results returned for search query '{query}'")
            return []
        
        try:
            # Find search results marker
            marker = "SEARCH_RESULTS:"
            marker_pos = result.find(marker)
            if marker_pos < 0:
                logger.warning(f"Failed to find search results marker in output")
                return []
            
            # Extract JSON string
            result_text = result[marker_pos + len(marker):].strip()
            
            # Find JSON boundaries
            json_start = result_text.find('{')
            json_end = result_text.rfind('}')
            
            if json_start < 0 or json_end < 0:
                logger.warning("Failed to find JSON boundaries in search results")
                return []
                
            json_str = result_text[json_start:json_end + 1]
            
            # Parse JSON
            tweets_data = json.loads(json_str)
            
            # Handle different formats (results might be in a nested property)
            if isinstance(tweets_data, dict):
                # Check if there's a nested property containing the tweets
                for key in ['data', 'statuses', 'tweets', 'results']:
                    if key in tweets_data and isinstance(tweets_data[key], list):
                        return tweets_data[key]
                
                # If we couldn't find a nested list, check if it's empty
                if not tweets_data:
                    logger.info("Empty result from search query")
                    return []
                
                # Return the dict as a single-item list as fallback
                return [tweets_data]
                
            elif isinstance(tweets_data, list):
                return tweets_data
            else:
                logger.warning(f"Unexpected tweets data type: {type(tweets_data)}")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode search results JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing search results: {e}")
            return []
    
    async def get_user_tweets(self, username: str, count: int = 5) -> List[Dict[str, Any]]:
        """Get tweets from a specific user"""
        logger.info(f"Getting tweets for user @{username}")
        
        script = self._create_user_tweets_script(username, count)
        result = await self._run_node_script(script)
        
        if not result:
            logger.warning(f"No results returned for user @{username}")
            return []
        
        try:
            # Find result marker
            marker = "USER_TWEETS:"
            marker_pos = result.find(marker)
            if marker_pos < 0:
                logger.warning(f"Failed to find user tweets marker in output")
                return []
            
            # Extract JSON string
            result_text = result[marker_pos + len(marker):].strip()
            
            # Parse JSON
            if result_text.startswith('[') and result_text.endswith(']'):
                tweets_data = json.loads(result_text)
                return tweets_data if isinstance(tweets_data, list) else []
            elif result_text.startswith('{') and result_text.endswith('}'):
                # Result might be a single object
                tweet_data = json.loads(result_text)
                logger.warning(f"Unexpected user tweets format: {result_text[:100]}...")
                return [tweet_data] if isinstance(tweet_data, dict) else []
            else:
                logger.warning(f"Unexpected user tweets format: {result_text[:100]}...")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode user tweets JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing user tweets: {e}")
            return []
    
    def _create_login_script(self) -> str:
        """Create Node.js script for logging in with auth token"""
        # Clean the auth token to ensure it's in the correct format
        auth_token = self.auth_token.strip()
        
        # Escape any special characters in the cookie string
        cookie_str = self.cookie_str.replace('"', '\\"')
        
        return f"""
        const twitterClient = require('agent-twitter-client');
        const Scraper = twitterClient.Scraper;
        
        async function loginWithToken() {{
            try {{
                console.log('Creating Twitter scraper...');
                const scraper = new Scraper({{ debug: true }});
                
                // Set auth token and cookies
                console.log('Setting auth token...');
                
                // Parse the cookie string into an object
                const cookies = JSON.parse('{cookie_str}');
                
                // Set the cookies
                console.log('Setting cookies...');
                try {{
                    const result = await scraper.setCookies(cookies);
                    console.log('AUTH_RESULT:', JSON.stringify({{ success: result }}));
                }} catch (err) {{
                    console.error('Error setting cookies:', err.message);
                    
                    // Try alternative cookie format
                    console.log('Trying alternative cookie format...');
                    
                    // Create cookie object directly
                    const authCookie = {{
                        name: 'auth_token',
                        value: '{auth_token}',
                        domain: '.twitter.com',
                        path: '/',
                        expires: -1,
                        httpOnly: true,
                        secure: true
                    }};
                    
                    try {{
                        const result = await scraper.withCookie(authCookie);
                        console.log('AUTH_RESULT:', JSON.stringify({{ success: result }}));
                    }} catch (innerErr) {{
                        console.error('Error setting individual cookie:', innerErr.message);
                        console.log('AUTH_RESULT:', JSON.stringify({{ success: false, error: innerErr.message }}));
                    }}
                }}
                
                console.log('Login operation completed');
            }} catch (error) {{
                console.error('Error message:', error.message);
                console.log('AUTH_RESULT:', JSON.stringify({{ success: false, error: error.message }}));
                process.exit(1);
            }}
        }}
        
        loginWithToken();
        """
    
    def _create_search_script(self, query: str, count: int) -> str:
        """Create Node.js script for searching tweets"""
        return f"""
        const twitterClient = require('agent-twitter-client');
        const Scraper = twitterClient.Scraper;
        const SearchMode = twitterClient.SearchMode;
        
        async function searchTweets() {{
            try {{
                console.log('Creating Twitter scraper...');
                const scraper = new Scraper({{ debug: true }});
                
                // Attempt authentication with stored cookies
                const authCookie = {{
                    name: 'auth_token',
                    value: '{self.auth_token}',
                    domain: '.twitter.com',
                    path: '/',
                    expires: -1,
                    httpOnly: true,
                    secure: true
                }};
                
                try {{
                    await scraper.withCookie(authCookie);
                    console.log('Authentication applied');
                }} catch (err) {{
                    console.warn('Proceeding without authentication');
                }}
                
                console.log('Searching for tweets...');
                const tweets = await scraper.searchTweets('{query}', {count}, SearchMode.Latest);
                console.log('SEARCH_RESULTS:', JSON.stringify(tweets));
                console.log('Search operation completed');
            }} catch (error) {{
                console.error('Error message:', error.message);
                process.exit(1);
            }}
        }}
        
        searchTweets();
        """
    
    def _create_user_tweets_script(self, username: str, count: int) -> str:
        """Create Node.js script for getting user tweets"""
        return f"""
        const twitterClient = require('agent-twitter-client');
        const Scraper = twitterClient.Scraper;
        
        async function getUserTweets() {{
            try {{
                console.log('Creating Twitter scraper...');
                const scraper = new Scraper({{ debug: true }});
                
                // Attempt authentication with stored cookies
                const authCookie = {{
                    name: 'auth_token',
                    value: '{self.auth_token}',
                    domain: '.twitter.com',
                    path: '/',
                    expires: -1,
                    httpOnly: true,
                    secure: true
                }};
                
                try {{
                    await scraper.withCookie(authCookie);
                    console.log('Authentication applied');
                }} catch (err) {{
                    console.warn('Proceeding without authentication');
                }}
                
                console.log('Getting tweets for @{username}...');
                const tweets = await scraper.getTweets('{username}', {count});
                console.log('USER_TWEETS:', JSON.stringify(tweets));
                console.log('Get user tweets operation completed');
            }} catch (error) {{
                console.error('Error message:', error.message);
                process.exit(1);
            }}
        }}
        
        getUserTweets();
        """
    
    async def _run_node_script(self, script: str) -> Optional[str]:
        """
        Run a Node.js script and return its output
        
        Args:
            script: Node.js script to run
            
        Returns:
            Script output or None if an error occurred
        """
        # Create temp script file
        script_file = "temp_twitter_script.cjs"
        with open(script_file, "w") as f:
            f.write(script)
        
        try:
            # Run the script
            result = subprocess.run(
                ["node", script_file],
                capture_output=True,
                text=True,
                check=False
            )
            
            # Clean up
            if os.path.exists(script_file):
                os.remove(script_file)
            
            # Check for errors
            if result.returncode != 0:
                logger.error(f"Script execution failed with exit code {result.returncode}")
                if result.stderr:
                    logger.error(f"Error output: {result.stderr}")
                return None
            
            # Return stdout
            return result.stdout
            
        except Exception as e:
            logger.error(f"Error executing Node.js script: {e}")
            
            # Clean up on exception
            if os.path.exists(script_file):
                os.remove(script_file)
                
            return None

async def test_login():
    """Test login functionality"""
    logger.info("===== Testing Login Functionality =====")
    
    client = SimpleTwitterTest()
    auth_result = await client.login()
    
    logger.info(f"Authentication result: {auth_result}")
    
    return client

async def search_tweets(client: SimpleTwitterTest, query: str = "cryptocurrency"):
    """Test search for tweets with query"""
    logger.info(f"===== Testing Search for '{query}' =====")
    
    tweets = await client.search_tweets(query, count=5)
    
    if tweets:
        logger.info(f"Found {len(tweets)} tweets for query '{query}'")
        if len(tweets) > 0:
            logger.info(f"First tweet: {str(tweets[0])[:200]}...")
    else:
        logger.info(f"No tweets found for query '{query}'")

async def get_user_tweets(client: SimpleTwitterTest, username: str = "AndreCronjeTech"):
    """Test getting tweets from a specific user"""
    logger.info(f"===== Testing Get User Tweets for @{username} =====")
    
    tweets = await client.get_user_tweets(username, count=5)
    
    if tweets:
        logger.info(f"Found {len(tweets)} tweets for user @{username}")
        if len(tweets) > 0:
            logger.info(f"First tweet: {str(tweets[0])[:200]}...")
    else:
        logger.info(f"No tweets found for user @{username}")

async def main():
    """Main entry point"""
    try:
        logger.info("Starting Twitter test...")
        
        # Test login
        client = await test_login()
        
        # Test search
        await search_tweets(client, "cryptocurrency")
        await search_tweets(client, "SonicLabs")
        
        # Test user tweets
        await get_user_tweets(client, "AndreCronjeTech")
        await get_user_tweets(client, "SonicLabs")
        
        logger.info("Test completed")
    except Exception as e:
        logger.error(f"Error in test: {e}")

if __name__ == "__main__":
    asyncio.run(main())