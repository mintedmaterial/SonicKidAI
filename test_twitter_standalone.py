"""
Standalone Twitter API Test Script

This script is designed to run independently to test the Twitter API integration
using the agent-twitter-client package without relying on the main application
structure and dependencies.
"""
import os
import json
import asyncio
import subprocess
import tempfile
from typing import Dict, List, Any, Optional
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class StandaloneTwitterClient:
    """Standalone Twitter client for API testing"""
    
    def __init__(self):
        """Initialize the Twitter client"""
        # Load environment variables
        self.auth_token = os.environ.get("TWITTER_AUTH_TOKEN", "")
        self.auth_multi_token = os.environ.get("TWITTER_AUTH_MULTI_TOKEN", "")
        self.username = os.environ.get("TWITTER_USERNAME", "")
        self.password = os.environ.get("TWITTER_PASSWORD", "")
        self.email = os.environ.get("TWITTER_EMAIL", "")
        
        if not self.auth_token:
            logger.warning("TWITTER_AUTH_TOKEN not found in environment variables")
            
        if not self.username or not self.password:
            logger.warning("TWITTER_USERNAME or TWITTER_PASSWORD not found in environment variables")
    
    async def authenticate(self) -> bool:
        """Authenticate with Twitter"""
        logger.info("Starting Twitter authentication")
        
        try:
            script = self._create_auth_script()
            result = await self._run_node_script(script)
            
            if not result:
                logger.error("Authentication failed: No result from script")
                return False
            
            try:
                data = json.loads(result)
                if data.get("success", False):
                    logger.info("Authentication successful")
                    if "token" in data:
                        logger.info(f"Got token: {data['token'][:20]}...")
                    return True
                else:
                    logger.error(f"Authentication failed: {data.get('error', 'Unknown error')}")
                    return False
            except json.JSONDecodeError:
                logger.error(f"Failed to parse authentication result: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
    
    async def search_tweets(self, query: str, count: int = 5) -> List[Dict[str, Any]]:
        """Search for tweets with query"""
        logger.info(f"Searching for tweets with query: {query}")
        
        try:
            script = self._create_search_script(query, count)
            result = await self._run_node_script(script)
            
            if not result:
                logger.error("Search failed: No result from script")
                return []
            
            try:
                data = json.loads(result)
                if isinstance(data, list):
                    logger.info(f"Found {len(data)} tweets")
                    return data
                elif isinstance(data, dict) and data.get("tweets"):
                    logger.info(f"Found {len(data['tweets'])} tweets")
                    return data["tweets"]
                elif isinstance(data, dict) and data.get("error"):
                    logger.error(f"Search error: {data.get('error')}")
                    return []
                else:
                    logger.error(f"Unexpected search result format: {data}")
                    return []
            except json.JSONDecodeError:
                logger.error(f"Failed to parse search result: {result}")
                return []
                
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return []
    
    async def get_user_tweets(self, username: str, count: int = 5) -> List[Dict[str, Any]]:
        """Get tweets from a specific user"""
        logger.info(f"Getting tweets from user: {username}")
        
        try:
            script = self._create_user_tweets_script(username, count)
            result = await self._run_node_script(script)
            
            if not result:
                logger.error("Get user tweets failed: No result from script")
                return []
            
            try:
                data = json.loads(result)
                if isinstance(data, list):
                    logger.info(f"Found {len(data)} tweets from {username}")
                    return data
                elif isinstance(data, dict) and data.get("tweets"):
                    logger.info(f"Found {len(data['tweets'])} tweets from {username}")
                    return data["tweets"]
                elif isinstance(data, dict) and data.get("error"):
                    logger.error(f"Get user tweets error: {data.get('error')}")
                    return []
                else:
                    logger.error(f"Unexpected user tweets result format: {data}")
                    return []
            except json.JSONDecodeError:
                logger.error(f"Failed to parse user tweets result: {result}")
                return []
                
        except Exception as e:
            logger.error(f"Get user tweets error: {str(e)}")
            return []
    
    def _create_auth_script(self) -> str:
        """Create Node.js script for authentication"""
        return f"""
        const {{ Scraper }} = require('agent-twitter-client');

        (async () => {{
            try {{
                const scraper = new Scraper();
                
                // Try authenticating with auth token first
                if ('{self.auth_token}') {{
                    const success = await scraper.loginWithAuthToken('{self.auth_token}');
                    if (success) {{
                        const token = scraper.getGuestToken();
                        console.log(JSON.stringify({{ success: true, method: 'auth_token', token }}));
                        return;
                    }}
                }}
                
                // Fall back to username/password if auth token fails
                if ('{self.username}' && '{self.password}') {{
                    const success = await scraper.login('{self.username}', '{self.password}');
                    if (success) {{
                        const token = scraper.getGuestToken();
                        console.log(JSON.stringify({{ success: true, method: 'credentials', token }}));
                        return;
                    }}
                }}
                
                console.log(JSON.stringify({{ success: false, error: 'Authentication failed with all methods' }}));
            }} catch (error) {{
                console.log(JSON.stringify({{ success: false, error: error.message }}));
            }}
        }})();
        """
    
    def _create_search_script(self, query: str, count: int) -> str:
        """Create Node.js script for searching tweets"""
        return f"""
        const {{ Scraper }} = require('agent-twitter-client');

        (async () => {{
            try {{
                const scraper = new Scraper();
                
                // Authenticate first
                let authenticated = false;
                
                if ('{self.auth_token}') {{
                    authenticated = await scraper.loginWithAuthToken('{self.auth_token}');
                }}
                
                if (!authenticated && '{self.username}' && '{self.password}') {{
                    authenticated = await scraper.login('{self.username}', '{self.password}');
                }}
                
                if (!authenticated) {{
                    console.log(JSON.stringify({{ error: 'Authentication failed' }}));
                    return;
                }}
                
                // Search tweets
                const tweets = await scraper.searchTweets('{query}', {count}, 'Latest');
                console.log(JSON.stringify(tweets));
            }} catch (error) {{
                console.log(JSON.stringify({{ error: error.message }}));
            }}
        }})();
        """
    
    def _create_user_tweets_script(self, username: str, count: int) -> str:
        """Create Node.js script for getting user tweets"""
        return f"""
        const {{ Scraper }} = require('agent-twitter-client');

        (async () => {{
            try {{
                const scraper = new Scraper();
                
                // Authenticate first
                let authenticated = false;
                
                if ('{self.auth_token}') {{
                    authenticated = await scraper.loginWithAuthToken('{self.auth_token}');
                }}
                
                if (!authenticated && '{self.username}' && '{self.password}') {{
                    authenticated = await scraper.login('{self.username}', '{self.password}');
                }}
                
                if (!authenticated) {{
                    console.log(JSON.stringify({{ error: 'Authentication failed' }}));
                    return;
                }}
                
                // Get user tweets
                const tweets = await scraper.getUserTweets('{username}', {count});
                console.log(JSON.stringify(tweets));
            }} catch (error) {{
                console.log(JSON.stringify({{ error: error.message }}));
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
        with tempfile.NamedTemporaryFile(suffix=".js", delete=False) as f:
            script_path = f.name
            f.write(script.encode('utf-8'))
        
        try:
            process = await asyncio.create_subprocess_exec(
                "node", script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if stderr:
                error_message = stderr.decode('utf-8').strip()
                if error_message:
                    logger.error(f"Script error: {error_message}")
            
            if process.returncode != 0:
                logger.error(f"Script exited with non-zero code: {process.returncode}")
                return None
            
            output = stdout.decode('utf-8').strip()
            return output
            
        except Exception as e:
            logger.error(f"Error running Node.js script: {str(e)}")
            return None
        finally:
            try:
                os.unlink(script_path)
            except:
                pass


async def run_test():
    """Run the complete standalone test"""
    client = StandaloneTwitterClient()
    
    # Test authentication
    logger.info("Starting authentication test")
    auth_success = await client.authenticate()
    logger.info(f"Authentication test result: {auth_success}")
    
    if not auth_success:
        logger.error("Authentication failed, cannot continue with other tests")
        return
    
    # Test search tweets
    logger.info("Starting search tweets test")
    search_results = await client.search_tweets("cryptocurrency", 5)
    logger.info(f"Search test found {len(search_results)} tweets")
    
    if search_results:
        logger.info("First search result preview:")
        for i, tweet in enumerate(search_results[:1]):
            logger.info(f"Tweet {i+1}:")
            if isinstance(tweet, dict):
                for key in ['id', 'text', 'username', 'name']:
                    if key in tweet:
                        logger.info(f"  {key}: {tweet[key]}")
    
    # Test user tweets
    logger.info("Starting user tweets test")
    user_results = await client.get_user_tweets("AndreCronjeTech", 5)
    logger.info(f"User tweets test found {len(user_results)} tweets")
    
    if user_results:
        logger.info("First user tweet preview:")
        for i, tweet in enumerate(user_results[:1]):
            logger.info(f"Tweet {i+1}:")
            if isinstance(tweet, dict):
                for key in ['id', 'text', 'username', 'name']:
                    if key in tweet:
                        logger.info(f"  {key}: {tweet[key]}")


async def main():
    """Main entry point"""
    logger.info("Starting Twitter API test")
    await run_test()
    logger.info("Twitter API test completed")


if __name__ == "__main__":
    asyncio.run(main())