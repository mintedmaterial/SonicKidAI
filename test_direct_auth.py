"""
Test Twitter Authentication with direct auth token
"""

import os
import json
import asyncio
import logging
import subprocess

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Hardcoded token for testing (in a real app, this would come from environment)
AUTH_TOKEN = "30a88ac3c27a5a2b88742e38d6cbe71cf3663cb3"

async def test_auth_token():
    """Test authentication with token"""
    logger.info("Testing authentication with token...")
    
    script = """
    const twitterClient = require('agent-twitter-client');
    const Scraper = twitterClient.Scraper;
    
    async function authenticateWithToken() {
        try {
            console.log('Creating Twitter scraper...');
            const scraper = new Scraper({ debug: true });
            
            // Create the auth token cookie
            console.log('Creating cookie from auth token...');
            const cookie = {
                name: 'auth_token',
                value: '30a88ac3c27a5a2b88742e38d6cbe71cf3663cb3',
                domain: '.twitter.com',
                path: '/',
                expires: -1,
                httpOnly: true,
                secure: true
            };
            
            // Set the cookie
            console.log('Setting cookie...');
            await scraper.setCookies([cookie]);
            
            // Check if logged in
            console.log('Checking authentication status...');
            const isLoggedIn = await scraper.isLoggedIn();
            console.log('AUTH_RESULT:', JSON.stringify({ success: isLoggedIn }));
            
            if (isLoggedIn) {
                // Try to get current user info
                try {
                    console.log('Getting current user info...');
                    const userInfo = await scraper.me();
                    console.log('USER_INFO:', JSON.stringify(userInfo));
                } catch (e) {
                    console.error('Error getting user info:', e.message);
                }
                
                // Try to get tweets from a user
                try {
                    console.log('Getting tweets from AndreCronjeTech...');
                    const tweets = await scraper.getTweets('AndreCronjeTech', 2);
                    console.log('TWEETS:', JSON.stringify(tweets));
                } catch (e) {
                    console.error('Error getting tweets:', e.message);
                }
            }
        } catch (error) {
            console.error('Authentication error:', error.message);
            process.exit(1);
        }
    }
    
    authenticateWithToken().catch(console.error);
    """
    
    # Save script to temp file
    temp_file = "temp_auth_test.cjs"
    with open(temp_file, "w") as f:
        f.write(script)
    
    try:
        # Run the Node.js script
        logger.info("Running authentication test script...")
        result = subprocess.run(["node", temp_file], capture_output=True, text=True)
        
        # Print output
        if result.stdout:
            logger.info("Script output:")
            for line in result.stdout.split("\n"):
                logger.info(f"  {line}")
        
        # Check for errors
        if result.stderr:
            logger.error("Script errors:")
            for line in result.stderr.split("\n"):
                if line.strip():
                    logger.error(f"  {line}")
        
        # Check exit code
        if result.returncode != 0:
            logger.error(f"Script failed with exit code {result.returncode}")
            return False
        
        # Check if authentication was successful
        if "AUTH_RESULT:" in result.stdout:
            # Extract auth result
            auth_result_line = [line for line in result.stdout.split("\n") if "AUTH_RESULT:" in line][0]
            auth_result_json = auth_result_line.split("AUTH_RESULT:", 1)[1].strip()
            
            try:
                auth_result = json.loads(auth_result_json)
                if auth_result.get("success", False):
                    logger.info("Authentication successful!")
                    return True
                else:
                    logger.error("Authentication failed")
                    return False
            except json.JSONDecodeError:
                logger.error(f"Failed to parse auth result: {auth_result_json}")
                return False
        
        logger.error("Failed to find authentication result in output")
        return False
    except Exception as e:
        logger.error(f"Error running authentication test: {str(e)}")
        return False
    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.remove(temp_file)

async def test_search_functionality():
    """Test search functionality without auth"""
    logger.info("Testing search functionality without auth...")
    
    script = """
    const twitterClient = require('agent-twitter-client');
    const Scraper = twitterClient.Scraper;
    const SearchMode = twitterClient.SearchMode;
    
    async function searchTweets() {
        try {
            console.log('Creating Twitter scraper...');
            const scraper = new Scraper({ debug: true });
            
            // Try to get trends (doesn't require auth)
            try {
                console.log('Getting trends...');
                const trends = await scraper.getTrends();
                console.log('TRENDS:', JSON.stringify(trends));
            } catch (e) {
                console.error('Error getting trends:', e.message);
            }
            
            // Try to search tweets
            try {
                console.log('Searching for tweets about SonicLabs...');
                const tweets = await scraper.searchTweets('SonicLabs', 5, SearchMode.Latest);
                console.log('SEARCH_RESULTS:', JSON.stringify(tweets));
            } catch (e) {
                console.error('Error searching tweets:', e.message);
            }
        } catch (error) {
            console.error('Script error:', error.message);
            process.exit(1);
        }
    }
    
    searchTweets().catch(console.error);
    """
    
    # Save script to temp file
    temp_file = "temp_search_test.cjs"
    with open(temp_file, "w") as f:
        f.write(script)
    
    try:
        # Run the Node.js script
        logger.info("Running search test script...")
        result = subprocess.run(["node", temp_file], capture_output=True, text=True)
        
        # Print output
        if result.stdout:
            logger.info("Script output:")
            for line in result.stdout.split("\n"):
                logger.info(f"  {line}")
        
        # Check for errors
        if result.stderr:
            logger.error("Script errors:")
            for line in result.stderr.split("\n"):
                if line.strip():
                    logger.error(f"  {line}")
        
        # Check exit code
        if result.returncode != 0:
            logger.error(f"Script failed with exit code {result.returncode}")
            return False
        
        # Check if trends were retrieved
        if "TRENDS:" in result.stdout:
            logger.info("Search functionality test successful")
            return True
        
        logger.error("Failed to get trends")
        return False
    except Exception as e:
        logger.error(f"Error running search test: {str(e)}")
        return False
    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.remove(temp_file)

async def main():
    """Main test function"""
    logger.info("Starting Twitter client tests...")
    
    # Test authentication with token
    auth_result = await test_auth_token()
    logger.info(f"Authentication test {'PASSED' if auth_result else 'FAILED'}")
    
    # Test search functionality
    search_result = await test_search_functionality()
    logger.info(f"Search functionality test {'PASSED' if search_result else 'FAILED'}")
    
    # Overall result
    if auth_result and search_result:
        logger.info("All tests PASSED")
    else:
        logger.warning("Some tests FAILED")

if __name__ == "__main__":
    asyncio.run(main())