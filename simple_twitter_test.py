"""
Simple Twitter Search Test

This script tests only the search functionality of the Twitter client, which
doesn't require authentication. It demonstrates how to use the Twitter client
to search for tweets, which is what most of our application will need.
"""

import os
import json
import asyncio
import logging
import subprocess
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def run_search(query, count=10):
    """Run a Twitter search operation using Node.js"""
    script_parts = [
        "// Use CommonJS syntax for requiring the module",
        "const twitterClient = require('agent-twitter-client');",
        "const Scraper = twitterClient.Scraper;",
        "const SearchMode = twitterClient.SearchMode;",
        "",
        "async function runTwitterSearch() {",
        "    try {",
        "        // Initialize the scraper with debug option",
        "        console.log('Creating Twitter scraper...');",
        "        const scraper = new Scraper({ debug: true });",
        "        ",
        "        // First try to get recent tweets to see if basic API works",
        "        console.log('Testing basic functionality with getTweets...');",
        "        try {",
        "            const elon_tweets = await scraper.getTweets('elonmusk', 2);",
        "            console.log('Elon tweets test result:', JSON.stringify(elon_tweets));",
        "        } catch (e) {",
        "            console.log('Elon tweets error:', e.message);",
        "        }",
        "        ",
        "        // Try various search modes",
        "        console.log('Executing search operation with Latest mode...');",
        f"        const latest_tweets = await scraper.searchTweets('{query}', {count}, SearchMode.Latest);",
        "        console.log('LATEST RESULTS:', JSON.stringify(latest_tweets));",
        "        ",
        "        console.log('Executing search operation with Top mode...');",
        f"        const top_tweets = await scraper.searchTweets('{query}', {count}, SearchMode.Top);",
        "        console.log('TOP RESULTS:', JSON.stringify(top_tweets));",
        "        ",
        "        console.log('Executing search operation with Photos mode...');",
        f"        const photo_tweets = await scraper.searchTweets('{query}', {count}, SearchMode.Photos);",
        "        console.log('PHOTO RESULTS:', JSON.stringify(photo_tweets));",
        "        ",
        "        // Try fetchSearchTweets (alternative method)",
        "        console.log('Trying alternative fetchSearchTweets method...');",
        f"        const fetch_results = await scraper.fetchSearchTweets('{query}', {count}, SearchMode.Latest);",
        "        console.log('FETCH RESULTS:', JSON.stringify(fetch_results));",
        "        ",
        "        console.log('Search operations completed successfully');",
        "    } catch (error) {",
        "        console.error('Error message:', error.message);",
        "        process.exit(1);",
        "    }",
        "}",
        "",
        "runTwitterSearch();"
    ]
    
    script = "\n".join(script_parts)
    
    # Create a temporary JS file with a .cjs extension for CommonJS
    temp_script_path = "temp_twitter_search.cjs"
    with open(temp_script_path, "w") as f:
        f.write(script)
    
    logger.debug(f"Generated script:\n{script}")
    
    try:
        # Run the Node.js script
        logger.debug("Executing Node.js script...")
        result = subprocess.run(
            ["node", temp_script_path],
            capture_output=True,
            text=True,
            check=False  # Don't raise exception on non-zero exit
        )
        
        # Log output regardless of success
        if result.stdout:
            logger.debug(f"Script stdout: {result.stdout}")
        
        # Check for errors
        if result.returncode != 0:
            logger.error(f"Script failed with exit code {result.returncode}")
            if result.stderr:
                logger.error(f"Script stderr: {result.stderr}")
            return None
        
        return result.stdout.strip()
    except Exception as e:
        logger.error(f"Error running Twitter search: {str(e)}", exc_info=True)
        return None
    finally:
        # Clean up temporary file
        if os.path.exists(temp_script_path):
            os.remove(temp_script_path)

async def main():
    """Main entry point"""
    try:
        logger.info("Testing Twitter search functionality...")
        
        # Test different search terms
        search_terms = ["bitcoin", "ethereum", "crypto", "nft"]
        for term in search_terms:
            logger.info(f"Searching for tweets about '{term}'...")
            result = await run_search(term, 5)
            
            if result:
                logger.info(f"Successfully searched for '{term}'")
                
                # Try to parse JSON from the response
                try:
                    # Find the JSON part of the output (there might be other console.log statements)
                    json_start = result.find('[')
                    json_end = result.rfind(']') + 1
                    
                    if json_start >= 0 and json_end > json_start:
                        json_part = result[json_start:json_end]
                        tweets_data = json.loads(json_part)
                        
                        logger.info(f"Found {len(tweets_data)} tweets for '{term}'")
                        for i, tweet in enumerate(tweets_data[:3], 1):
                            if isinstance(tweet, dict) and 'text' in tweet:
                                logger.info(f"  {i}. {tweet.get('text', 'No text')[:50]}...")
                            else:
                                logger.info(f"  {i}. Unexpected tweet format: {type(tweet)}")
                    else:
                        logger.error(f"Could not find JSON array in result for '{term}'")
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing JSON for '{term}': {str(e)}")
                except Exception as e:
                    logger.error(f"Error processing results for '{term}': {str(e)}")
            else:
                logger.error(f"Failed to search for '{term}'")
        
        logger.info("Twitter search test completed")
    except Exception as e:
        logger.error(f"Error in Twitter search test: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())