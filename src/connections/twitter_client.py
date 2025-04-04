"""
Twitter Client using ElizaOS agent-twitter-client

This module provides a Twitter client implementation using the ElizaOS agent-twitter-client
Node.js package. It allows for Twitter operations without requiring a Twitter API key.
"""

import os
import json
import subprocess
import logging
import tempfile
from typing import Dict, Any, List, Optional, Union, Callable
from dotenv import load_dotenv
from src.connections.base_connection import BaseConnection, Action, ActionParameter

logger = logging.getLogger(__name__)

class TwitterClientError(Exception):
    """Exception raised for Twitter client errors."""
    pass

class TwitterClient(BaseConnection):
    """Twitter client using ElizaOS agent-twitter-client"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Twitter client with configuration"""
        super().__init__(config)
        
        # Load environment variables from .env file
        try:
            load_dotenv()
        except Exception as e:
            logger.warning(f"Could not load environment variables from .env file: {str(e)}")
            
        # Get Twitter credentials from environment variables
        self._twitter_username = os.getenv("TWITTER_USERNAME", "")
        self._twitter_password = os.getenv("TWITTER_PASSWORD", "")
        self._twitter_email = os.getenv("TWITTER_EMAIL", "")
        self._twitter_cookies = os.getenv("TWITTER_COOKIES", "")
        
        logger.info(f"Twitter credentials loaded. Username: {self._twitter_username and 'YES' or 'NO'}, " +
                    f"Password: {self._twitter_password and 'YES' or 'NO'}, " +
                    f"Email: {self._twitter_email and 'YES' or 'NO'}, " +
                    f"Cookies: {self._twitter_cookies and 'YES' or 'NO'}")
        
        # Check for required credentials
        if not ((self._twitter_username and self._twitter_password) or self._twitter_cookies):
            logger.warning("No Twitter credentials found. Limited functionality will be available.")
    
    @property
    def is_llm_provider(self) -> bool:
        """This is not an LLM provider"""
        return False
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the Twitter client configuration"""
        return config
    
    def register_actions(self) -> None:
        """Register available Twitter actions"""
        self.actions = {
            "get-trends": Action(
                name="get-trends",
                description="Get current Twitter trending topics",
                parameters=[]
            ),
            "get-user-tweets": Action(
                name="get-user-tweets",
                description="Get tweets from a specific user",
                parameters=[
                    ActionParameter(name="username", description="Twitter username", required=True, type=str),
                    ActionParameter(name="count", description="Number of tweets to retrieve", required=False, type=int)
                ]
            ),
            "get-tweet": Action(
                name="get-tweet",
                description="Get a specific tweet by ID",
                parameters=[
                    ActionParameter(name="tweet_id", description="Tweet ID", required=True, type=str)
                ]
            ),
            "post-tweet": Action(
                name="post-tweet",
                description="Post a new tweet",
                parameters=[
                    ActionParameter(name="text", description="Tweet text", required=True, type=str)
                ]
            ),
            "post-poll": Action(
                name="post-poll",
                description="Post a tweet with a poll",
                parameters=[
                    ActionParameter(name="text", description="Tweet text", required=True, type=str),
                    ActionParameter(name="options", description="Poll options", required=True, type=list),
                    ActionParameter(name="duration_minutes", description="Poll duration in minutes", required=False, type=int)
                ]
            ),
            "search-tweets": Action(
                name="search-tweets",
                description="Search for tweets matching a query",
                parameters=[
                    ActionParameter(name="query", description="Search query", required=True, type=str),
                    ActionParameter(name="count", description="Number of tweets to retrieve", required=False, type=int)
                ]
            ),
            "get-profile": Action(
                name="get-profile",
                description="Get a user's profile information",
                parameters=[
                    ActionParameter(name="username", description="Twitter username", required=True, type=str)
                ]
            ),
            "follow-user": Action(
                name="follow-user",
                description="Follow a user on Twitter",
                parameters=[
                    ActionParameter(name="username", description="Twitter username", required=True, type=str)
                ]
            ),
            "get-home-timeline": Action(
                name="get-home-timeline",
                description="Get the home timeline (requires authentication)",
                parameters=[
                    ActionParameter(name="count", description="Number of tweets to retrieve", required=False, type=int)
                ]
            ),
            "retweet": Action(
                name="retweet",
                description="Retweet a tweet",
                parameters=[
                    ActionParameter(name="tweet_id", description="Tweet ID", required=True, type=str)
                ]
            ),
            "like-tweet": Action(
                name="like-tweet",
                description="Like a tweet",
                parameters=[
                    ActionParameter(name="tweet_id", description="Tweet ID", required=True, type=str)
                ]
            ),
            "store-cookies": Action(
                name="store-cookies",
                description="Store Twitter cookies for future use",
                parameters=[]
            )
        }
    
    def _get_auth_code(self) -> str:
        """Generate authentication code based on available credentials"""
        if self._twitter_cookies:
            # We need to properly format the auth_token as a cookie object
            logger.info("Using Twitter cookies for authentication")
            auth_token = self._twitter_cookies
            if "auth_token" in auth_token:
                # If it's just a token value, format it properly
                if not auth_token.startswith("[") and not auth_token.startswith("{"):
                    # It's just a raw token
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
            return f"await scraper.setCookies({self._twitter_cookies});"
        elif self._twitter_username and self._twitter_password:
            logger.info(f"Using Twitter username '{self._twitter_username}' and password for authentication")
            return f"await scraper.login('{self._twitter_username}', '{self._twitter_password}');"
        else:
            logger.warning("No authentication credentials available")
            return "console.log('No authentication credentials available');"
    
    async def _run_twitter_operation(self, operation_code: str) -> Optional[str]:
        """Run a Twitter operation via Node.js"""
        auth_code = self._get_auth_code()
        
        # Generate the full Node.js script without using string formatting
        script_parts = [
            "// Use CommonJS syntax for requiring the module",
            "const twitterClient = require('agent-twitter-client');",
            "const Scraper = twitterClient.Scraper;",
            "const SearchMode = twitterClient.SearchMode;",
            "",
            "async function runTwitterOperation() {",
            "    try {",
            "        // Initialize the scraper",
            "        const scraper = new Scraper();",
            "        ",
            "        // Setup authentication",
            f"        {auth_code}",
            "        ",
            "        // Perform the operation",
            f"        {operation_code}",
            "        ",
            "    } catch (error) {",
            "        console.error('Error:', error.message);",
            "        process.exit(1);",
            "    }",
            "}",
            "",
            "runTwitterOperation();"
        ]
        
        script = "\n".join(script_parts)
        
        # Create a temporary JS file with a .cjs extension for CommonJS
        with tempfile.NamedTemporaryFile(suffix='.cjs', delete=False, mode='w') as temp_file:
            temp_script_path = temp_file.name
            temp_file.write(script)
        
        try:
            # Run the Node.js script
            result = subprocess.run(
                ["node", temp_script_path],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running Twitter operation: {e.stderr}")
            raise TwitterClientError(f"Twitter operation failed: {e.stderr}")
        finally:
            # Clean up temporary file
            if os.path.exists(temp_script_path):
                os.remove(temp_script_path)
    
    async def get_trends(self) -> List[Dict[str, Any]]:
        """Get current Twitter trending topics"""
        operation = """
            const trends = await scraper.getTrends();
            console.log(JSON.stringify(trends));
        """
        result = await self._run_twitter_operation(operation)
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.error("Failed to parse trends JSON")
                return []
        return []
    
    async def get_user_tweets(self, username: str, count: int = 10) -> List[Dict[str, Any]]:
        """Get tweets from a specific user"""
        operation = f"""
            const tweets = await scraper.getTweets('{username}', {count});
            console.log(JSON.stringify(tweets));
        """
        result = await self._run_twitter_operation(operation)
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.error("Failed to parse tweets JSON")
                return []
        return []
    
    async def get_tweet(self, tweet_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific tweet by ID"""
        operation = f"""
            const tweet = await scraper.getTweet('{tweet_id}');
            console.log(JSON.stringify(tweet));
        """
        result = await self._run_twitter_operation(operation)
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.error("Failed to parse tweet JSON")
                return None
        return None
    
    async def post_tweet(self, text: str) -> Optional[Dict[str, Any]]:
        """Post a new tweet"""
        # Escape single quotes for JavaScript
        escaped_text = text.replace("'", "\\'")
        
        operation = f"""
            const result = await scraper.sendTweet('{escaped_text}');
            console.log(JSON.stringify(result));
        """
        result = await self._run_twitter_operation(operation)
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.error("Failed to parse post result JSON")
                return None
        return None
    
    async def post_poll(self, text: str, options: List[str], 
                     duration_minutes: int = 120) -> Optional[Dict[str, Any]]:
        """Post a tweet with a poll"""
        # Escape single quotes for JavaScript
        escaped_text = text.replace("'", "\\'")
        
        # Format poll options for JavaScript
        options_json = json.dumps([{"label": opt} for opt in options])
        
        operation = f"""
            const pollOptions = {options_json};
            const result = await scraper.sendTweetV2(
                '{escaped_text}',
                undefined,
                {{
                    poll: {{
                        options: pollOptions,
                        durationMinutes: {duration_minutes}
                    }}
                }}
            );
            console.log(JSON.stringify(result));
        """
        result = await self._run_twitter_operation(operation)
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.error("Failed to parse poll tweet result JSON")
                return None
        return None
    
    async def search_tweets(self, query: str, count: int = 10) -> List[Dict[str, Any]]:
        """Search for tweets matching a query"""
        # Escape single quotes for JavaScript
        escaped_query = query.replace("'", "\\'")
        
        operation = f"""
            const tweets = await scraper.searchTweets('{escaped_query}', {count}, SearchMode.Latest);
            console.log(JSON.stringify(tweets));
        """
        result = await self._run_twitter_operation(operation)
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.error("Failed to parse search results JSON")
                return []
        return []
    
    async def get_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """Get a user's profile information"""
        operation = f"""
            const profile = await scraper.getProfile('{username}');
            console.log(JSON.stringify(profile));
        """
        result = await self._run_twitter_operation(operation)
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.error("Failed to parse profile JSON")
                return None
        return None
    
    async def follow_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Follow a user on Twitter"""
        operation = f"""
            const result = await scraper.followUser('{username}');
            console.log(JSON.stringify(result));
        """
        result = await self._run_twitter_operation(operation)
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.error("Failed to parse follow result JSON")
                return None
        return None
    
    async def get_home_timeline(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get the home timeline (requires authentication)"""
        operation = f"""
            const timeline = await scraper.fetchHomeTimeline({count});
            console.log(JSON.stringify(timeline));
        """
        result = await self._run_twitter_operation(operation)
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.error("Failed to parse timeline JSON")
                return []
        return []
    
    async def retweet(self, tweet_id: str) -> Optional[Dict[str, Any]]:
        """Retweet a tweet"""
        operation = f"""
            const result = await scraper.retweet('{tweet_id}');
            console.log(JSON.stringify(result));
        """
        result = await self._run_twitter_operation(operation)
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.error("Failed to parse retweet result JSON")
                return None
        return None
    
    async def like_tweet(self, tweet_id: str) -> Optional[Dict[str, Any]]:
        """Like a tweet"""
        operation = f"""
            const result = await scraper.likeTweet('{tweet_id}');
            console.log(JSON.stringify(result));
        """
        result = await self._run_twitter_operation(operation)
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.error("Failed to parse like result JSON")
                return None
        return None
    
    async def store_cookies(self) -> Optional[str]:
        """Store Twitter cookies for future use"""
        operation = """
            const cookies = await scraper.getCookies();
            console.log(JSON.stringify(cookies));
        """
        result = await self._run_twitter_operation(operation)
        if result:
            logger.info("Twitter cookies retrieved successfully")
            return result
        return None