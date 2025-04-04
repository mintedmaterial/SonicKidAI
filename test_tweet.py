"""
Test Twitter Client functionality using agent-twitter-client package

This script demonstrates how to use the Twitter client without requiring
Twitter API keys. Instead, it uses the provided username, password, and
email credentials for authentication.
"""

import os
import json
import asyncio
import logging
import subprocess
from typing import Dict, List, Optional, Any, Union
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class TwitterClient:
    """Twitter client that uses agent-twitter-client package with Node.js interop"""

    def __init__(self):
        """Initialize the Twitter client"""
        self.username = os.getenv("TWITTER_USERNAME")
        self.password = os.getenv("TWITTER_PASSWORD")
        self.email = os.getenv("TWITTER_EMAIL")
        self.auth_token = os.getenv("TWITTER_AUTH_TOKEN")
        
        # Check if we have necessary credentials
        if not all([self.username, self.password, self.email]):
            logger.warning("Missing Twitter credentials. Set TWITTER_USERNAME, TWITTER_PASSWORD, and TWITTER_EMAIL environment variables.")
        
        # Save cookies path
        self.cookies_path = "twitter_cookies.json"
        
    async def get_profile(self, screen_name: str) -> Dict[str, Any]:
        """Get a Twitter profile by screen name"""
        logger.info(f"Getting profile for @{screen_name}...")
        
        script_parts = [
            "const twitterClient = require('agent-twitter-client');",
            "const Scraper = twitterClient.Scraper;",
            "",
            "async function getProfile() {",
            "    try {",
            "        // Create scraper with debug mode",
            "        console.log('Creating Twitter scraper...');",
            "        const scraper = new Scraper({ debug: true });",
            "",
            f"        // Try to get profile for @{screen_name}",
            "        console.log('Getting profile...');",
            f"        const profile = await scraper.getProfile('{screen_name}');",
            "        console.log('PROFILE_RESULT:', JSON.stringify(profile));",
            "    } catch (error) {",
            "        console.error('Error:', error.message);",
            "        process.exit(1);",
            "    }",
            "}",
            "",
            "getProfile().catch(console.error);"
        ]
        
        result = await self._run_node_script(script_parts)
        if not result:
            return {}
            
        # Extract profile JSON
        profile_json = self._extract_json_after_marker(result, "PROFILE_RESULT:")
        if profile_json:
            return profile_json
        return {}

    async def search_tweets(self, query: str, count: int = 10) -> List[Dict[str, Any]]:
        """Search for tweets using given query"""
        logger.info(f"Searching for tweets with query '{query}'...")

        script_parts = [
            "const twitterClient = require('agent-twitter-client');",
            "const Scraper = twitterClient.Scraper;",
            "const SearchMode = twitterClient.SearchMode;",
            "",
            "async function searchTweets() {",
            "    try {",
            "        // Create scraper with debug mode",
            "        console.log('Creating Twitter scraper...');",
            "        const scraper = new Scraper({ debug: true });",
            "",
            f"        // Search for tweets with query '{query}'",
            "        console.log('Searching for tweets...');",
            f"        const tweets = await scraper.searchTweets('{query}', {count}, SearchMode.Latest);",
            "        console.log('SEARCH_RESULTS:', JSON.stringify(tweets));",
            "    } catch (error) {",
            "        console.error('Error:', error.message);",
            "        process.exit(1);",
            "    }",
            "}",
            "",
            "searchTweets().catch(console.error);"
        ]
        
        result = await self._run_node_script(script_parts)
        if not result:
            return []
            
        # Extract search results JSON
        search_json = self._extract_json_after_marker(result, "SEARCH_RESULTS:")
        if search_json:
            return search_json if isinstance(search_json, list) else []
        return []
        
    async def get_user_tweets(self, screen_name: str, count: int = 10) -> List[Dict[str, Any]]:
        """Get a user's tweets"""
        logger.info(f"Getting tweets for @{screen_name}...")

        script_parts = [
            "const twitterClient = require('agent-twitter-client');",
            "const Scraper = twitterClient.Scraper;",
            "",
            "async function getUserTweets() {",
            "    try {",
            "        // Create scraper with debug mode",
            "        console.log('Creating Twitter scraper...');",
            "        const scraper = new Scraper({ debug: true });",
            "",
            f"        // Get tweets for @{screen_name}",
            "        console.log('Getting user tweets...');",
            f"        const tweets = await scraper.getTweets('{screen_name}', {count});",
            "        console.log('USER_TWEETS:', JSON.stringify(tweets));",
            "    } catch (error) {",
            "        console.error('Error:', error.message);",
            "        process.exit(1);",
            "    }",
            "}",
            "",
            "getUserTweets().catch(console.error);"
        ]
        
        result = await self._run_node_script(script_parts)
        if not result:
            return []
            
        # Extract tweets JSON
        tweets_json = self._extract_json_after_marker(result, "USER_TWEETS:")
        if tweets_json:
            return tweets_json if isinstance(tweets_json, list) else []
        return []
        
    async def get_tweet(self, tweet_id: str) -> Dict[str, Any]:
        """Get a specific tweet by ID"""
        logger.info(f"Getting tweet with ID {tweet_id}...")

        script_parts = [
            "const twitterClient = require('agent-twitter-client');",
            "const Scraper = twitterClient.Scraper;",
            "",
            "async function getTweet() {",
            "    try {",
            "        // Create scraper with debug mode",
            "        console.log('Creating Twitter scraper...');",
            "        const scraper = new Scraper({ debug: true });",
            "",
            f"        // Get tweet with ID {tweet_id}",
            "        console.log('Getting tweet...');",
            f"        const tweet = await scraper.getTweet('{tweet_id}');",
            "        console.log('TWEET_RESULT:', JSON.stringify(tweet));",
            "    } catch (error) {",
            "        console.error('Error:', error.message);",
            "        process.exit(1);",
            "    }",
            "}",
            "",
            "getTweet().catch(console.error);"
        ]
        
        result = await self._run_node_script(script_parts)
        if not result:
            return {}
            
        # Extract tweet JSON
        tweet_json = self._extract_json_after_marker(result, "TWEET_RESULT:")
        if tweet_json:
            return tweet_json
        return {}
    
    async def get_trends(self) -> List[Dict[str, Any]]:
        """Get current Twitter trends"""
        logger.info("Getting current Twitter trends...")

        script_parts = [
            "const twitterClient = require('agent-twitter-client');",
            "const Scraper = twitterClient.Scraper;",
            "",
            "async function getTrends() {",
            "    try {",
            "        // Create scraper with debug mode",
            "        console.log('Creating Twitter scraper...');",
            "        const scraper = new Scraper({ debug: true });",
            "",
            "        // Get trends",
            "        console.log('Getting trends...');",
            "        const trends = await scraper.getTrends();",
            "        console.log('TRENDS_RESULT:', JSON.stringify(trends));",
            "    } catch (error) {",
            "        console.error('Error:', error.message);",
            "        process.exit(1);",
            "    }",
            "}",
            "",
            "getTrends().catch(console.error);"
        ]
        
        result = await self._run_node_script(script_parts)
        if not result:
            return []
            
        # Extract trends JSON
        trends_json = self._extract_json_after_marker(result, "TRENDS_RESULT:")
        if trends_json:
            return trends_json if isinstance(trends_json, list) else []
        return []
    
    async def authenticate(self) -> bool:
        """Authenticate with Twitter using provided credentials"""
        logger.info("Authenticating with Twitter...")
        
        # Prepare login script based on available credentials
        if self.auth_token:
            script_parts = [
                "const twitterClient = require('agent-twitter-client');",
                "const Scraper = twitterClient.Scraper;",
                "",
                "async function authenticateWithCookies() {",
                "    try {",
                "        // Create scraper with debug mode",
                "        console.log('Creating Twitter scraper...');",
                "        const scraper = new Scraper({ debug: true });",
                "",
                "        // Set the auth token cookie",
                "        console.log('Setting auth token cookie...');",
                f"        const authToken = '{self.auth_token}';",
                "        const cookie = {",
                "            name: 'auth_token',",
                "            value: authToken,",
                "            domain: '.twitter.com',",
                "            path: '/',",
                "            expires: -1",
                "        };",
                "        await scraper.setCookies([cookie]);",
                "",
                "        // Check if we're logged in",
                "        console.log('Checking authentication status...');",
                "        const isLoggedIn = await scraper.isLoggedIn();",
                "        console.log('AUTH_RESULT:', JSON.stringify({ success: isLoggedIn }));",
                "",
                "        // Get and save cookies for future use if logged in",
                "        if (isLoggedIn) {",
                "            const cookies = await scraper.getCookies();",
                "            console.log('COOKIES_RESULT:', JSON.stringify(cookies));",
                "        }",
                "    } catch (error) {",
                "        console.error('Error:', error.message);",
                "        process.exit(1);",
                "    }",
                "}",
                "",
                "authenticateWithCookies().catch(console.error);"
            ]
        else:
            script_parts = [
                "const twitterClient = require('agent-twitter-client');",
                "const Scraper = twitterClient.Scraper;",
                "",
                "async function authenticateWithCredentials() {",
                "    try {",
                "        // Create scraper with debug mode",
                "        console.log('Creating Twitter scraper...');",
                "        const scraper = new Scraper({ debug: true });",
                "",
                "        // Authenticate with credentials",
                "        console.log('Logging in with credentials...');",
                f"        await scraper.login('{self.username}', '{self.password}', '{self.email}');",
                "",
                "        // Check if we're logged in",
                "        console.log('Checking authentication status...');",
                "        const isLoggedIn = await scraper.isLoggedIn();",
                "        console.log('AUTH_RESULT:', JSON.stringify({ success: isLoggedIn }));",
                "",
                "        // Get and save cookies for future use if logged in",
                "        if (isLoggedIn) {",
                "            const cookies = await scraper.getCookies();",
                "            console.log('COOKIES_RESULT:', JSON.stringify(cookies));",
                "        }",
                "    } catch (error) {",
                "        console.error('Error:', error.message);",
                "        process.exit(1);",
                "    }",
                "}",
                "",
                "authenticateWithCredentials().catch(console.error);"
            ]
        
        result = await self._run_node_script(script_parts)
        if not result:
            return False
            
        # Extract authentication result
        auth_json = self._extract_json_after_marker(result, "AUTH_RESULT:")
        if auth_json and isinstance(auth_json, dict) and auth_json.get("success", False):
            # Also extract and save cookies if available
            cookies_json = self._extract_json_after_marker(result, "COOKIES_RESULT:")
            if cookies_json:
                with open(self.cookies_path, "w") as f:
                    json.dump(cookies_json, f)
                logger.info(f"Saved Twitter cookies to {self.cookies_path}")
            return True
        return False
    
    async def _run_node_script(self, script_parts: List[str]) -> Optional[str]:
        """Run a Node.js script and return its output"""
        script = "\n".join(script_parts)
        
        # Write script to temporary file
        temp_script_path = "temp_twitter_script.cjs"
        with open(temp_script_path, "w") as f:
            f.write(script)
        
        try:
            # Run the Node.js script
            logger.debug("Executing Node.js script...")
            result = subprocess.run(
                ["node", temp_script_path],
                capture_output=True,
                text=True,
                check=False  # Don't raise exception on non-zero exit
            )
            
            # Check for errors
            if result.returncode != 0:
                logger.error(f"Script failed with exit code {result.returncode}")
                if result.stderr:
                    logger.error(f"Error: {result.stderr}")
                return None
            
            return result.stdout
        except Exception as e:
            logger.error(f"Error running Node.js script: {str(e)}")
            return None
        finally:
            # Clean up temporary file
            if os.path.exists(temp_script_path):
                os.remove(temp_script_path)
    
    def _extract_json_after_marker(self, text: str, marker: str) -> Union[Dict[str, Any], List[Dict[str, Any]], None]:
        """Extract JSON object or array after a specific marker in text"""
        try:
            # Find the marker
            marker_pos = text.find(marker)
            if marker_pos < 0:
                return None
                
            # Find the start of JSON (either { or [)
            json_start = None
            for i in range(marker_pos + len(marker), len(text)):
                if text[i] in ['{', '[']:
                    json_start = i
                    json_start_char = text[i]
                    break
                    
            if json_start is None:
                return None
                
            # Find the matching closing bracket
            closing_char = '}' if json_start_char == '{' else ']'
            open_count = 1
            json_end = None
            
            for i in range(json_start + 1, len(text)):
                if text[i] == json_start_char:
                    open_count += 1
                elif text[i] == closing_char:
                    open_count -= 1
                    if open_count == 0:
                        json_end = i + 1
                        break
                        
            if json_end is None:
                return None
                
            # Parse and return the JSON
            json_str = text[json_start:json_end]
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError, IndexError) as e:
            logger.error(f"Error extracting JSON: {str(e)}")
            return None

async def test_twitter_client():
    """Test Twitter client functionality"""
    try:
        # Initialize Twitter client
        client = TwitterClient()
        
        # Test basic search functionality first (doesn't require authentication)
        logger.info("Testing search functionality...")
        search_results = await client.search_tweets("SonicLabs", 5)
        logger.info(f"Search results: {json.dumps(search_results, indent=2)}")
        
        # Test getting trends (doesn't require authentication)
        logger.info("Testing trends functionality...")
        trends = await client.get_trends()
        logger.info(f"Trends: {json.dumps(trends, indent=2)}")
        
        # Try to authenticate if credentials are provided
        if client.username and client.password and client.email or client.auth_token:
            logger.info("Testing authentication...")
            auth_result = await client.authenticate()
            logger.info(f"Authentication result: {auth_result}")
            
            if auth_result:
                # Test getting a profile (can work without auth but gives more data with auth)
                logger.info("Testing profile retrieval...")
                profile = await client.get_profile("AndreCronjeTech")
                logger.info(f"Profile: {json.dumps(profile, indent=2)}")
                
                # Test getting user tweets
                logger.info("Testing user tweets retrieval...")
                user_tweets = await client.get_user_tweets("AndreCronjeTech", 3)
                logger.info(f"User tweets: {json.dumps(user_tweets, indent=2)}")
        else:
            logger.warning("Skipping authentication tests due to missing credentials")
        
        logger.info("Twitter client tests completed")
            
    except Exception as e:
        logger.error(f"Error testing Twitter client: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_twitter_client())