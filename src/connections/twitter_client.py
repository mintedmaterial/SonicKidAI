"""
Twitter Client integration

This module provides a Twitter client interface using the agent-twitter-client
Node.js package. It focuses on search functionality which doesn't require authentication.
"""

import os
import json
import logging
import subprocess
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

class TwitterClient:
    """Twitter client interface using agent-twitter-client package"""
    
    def __init__(self):
        """Initialize the Twitter client"""
        self.username = os.environ.get("TWITTER_USERNAME")
        self.password = os.environ.get("TWITTER_PASSWORD")
        self.email = os.environ.get("TWITTER_EMAIL")
        self.auth_token = os.environ.get("TWITTER_AUTH_TOKEN")
        
        # Log available credentials (without exposing sensitive info)
        logger.info(
            f"Twitter credentials loaded. Username: {'YES' if self.username else 'NO'}, "
            f"Password: {'YES' if self.password else 'NO'}, "
            f"Email: {'YES' if self.email else 'NO'}, "
            f"Auth Token: {'YES' if self.auth_token else 'NO'}"
        )
        
    async def search_tweets(self, query: str, count: int = 10, mode: str = "Latest") -> List[Dict[str, Any]]:
        """
        Search for tweets matching a query
        
        Args:
            query: Search query string
            count: Maximum number of tweets to retrieve
            mode: Search mode - 'Latest', 'Top', or 'Photos'
            
        Returns:
            List of tweet objects
        """
        logger.info(f"Searching for tweets with query '{query}', mode '{mode}'")
        
        script = self._create_search_script(query, count, mode)
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
    
    async def get_user_tweets(self, username: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get tweets from a specific user
        
        Args:
            username: Twitter username
            count: Maximum number of tweets to retrieve
            
        Returns:
            List of tweet objects
        """
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
    
    async def get_trends(self) -> List[Dict[str, Any]]:
        """
        Get current Twitter trends
        
        Returns:
            List of trend objects
        """
        logger.info("Getting Twitter trends")
        
        script = self._create_trends_script()
        result = await self._run_node_script(script)
        
        if not result:
            logger.warning("No trends returned")
            return []
        
        try:
            # Find result marker
            marker = "TRENDS_RESULT:"
            marker_pos = result.find(marker)
            if marker_pos < 0:
                logger.warning(f"Failed to find trends marker in output")
                return []
            
            # Extract JSON string
            result_text = result[marker_pos + len(marker):].strip()
            
            # Parse JSON
            if result_text.startswith('[') and result_text.endswith(']'):
                trends_data = json.loads(result_text)
                return trends_data if isinstance(trends_data, list) else []
            else:
                logger.warning(f"Unexpected trends format: {result_text[:100]}...")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode trends JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing trends: {e}")
            return []
    
    def _create_search_script(self, query: str, count: int, mode: str) -> str:
        """Create Node.js script for searching tweets"""
        return f"""
        const twitterClient = require('agent-twitter-client');
        const Scraper = twitterClient.Scraper;
        const SearchMode = twitterClient.SearchMode;
        
        async function searchTweets() {{
            try {{
                console.log('Creating Twitter scraper...');
                const scraper = new Scraper({{ debug: true }});
                
                console.log('Searching for tweets...');
                const tweets = await scraper.searchTweets('{query}', {count}, SearchMode.{mode});
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
    
    def _create_trends_script(self) -> str:
        """Create Node.js script for getting trends"""
        return """
        const twitterClient = require('agent-twitter-client');
        const Scraper = twitterClient.Scraper;
        
        async function getTrends() {
            try {
                console.log('Creating Twitter scraper...');
                const scraper = new Scraper({ debug: true });
                
                console.log('Getting trends...');
                const trends = await scraper.getTrends();
                console.log('TRENDS_RESULT:', JSON.stringify(trends));
                console.log('Get trends operation completed');
            } catch (error) {
                console.error('Error message:', error.message);
                process.exit(1);
            }
        }
        
        getTrends();
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