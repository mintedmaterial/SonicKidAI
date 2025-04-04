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
        "            const andre_tweets = await scraper.getTweets('AndreCronjeTech', 2);",
        "            console.log('Andre Cronje tweets test result:', JSON.stringify(andre_tweets));",
        "        } catch (e) {",
        "            console.log('Andre Cronje tweets error:', e.message);",
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
        search_terms = ["SonicLabs", "fantom", "defi", "crypto"]
        for term in search_terms:
            logger.info(f"Searching for tweets about '{term}'...")
            result = await run_search(term, 5)
            
            if result:
                logger.info(f"Successfully searched for '{term}'")
                
                # Parse and analyze all the different result formats from the output
                try:
                    # Look for specific results sections
                    result_sections = {
                        "Andre Cronje tweets": result.find("Andre Cronje tweets test result:"),
                        "LATEST RESULTS": result.find("LATEST RESULTS:"),
                        "TOP RESULTS": result.find("TOP RESULTS:"),
                        "PHOTO RESULTS": result.find("PHOTO RESULTS:"),
                        "FETCH RESULTS": result.find("FETCH RESULTS:")
                    }
                    
                    logger.info(f"Analysis of search results for '{term}':")
                    
                    for section_name, section_start in result_sections.items():
                        if section_start < 0:
                            logger.info(f"  - {section_name}: Section not found in output")
                            continue
                            
                        # Find the JSON part after this section marker
                        # First, get the text from the section marker to the end
                        section_text = result[section_start:]
                        
                        # Find the first '{' or '[' after the section marker
                        json_start_char = None
                        for char_idx, char in enumerate(section_text):
                            if char in ['{', '[']:
                                json_start_char = char
                                json_start = section_start + char_idx
                                break
                        
                        if not json_start_char:
                            logger.info(f"  - {section_name}: No JSON object found")
                            continue
                            
                        # Find the matching closing bracket
                        json_end_char = ']' if json_start_char == '[' else '}'
                        json_end = result.find(json_end_char, json_start)
                        
                        if json_end < 0:
                            logger.info(f"  - {section_name}: Incomplete JSON object")
                            continue
                            
                        # For proper JSON, include the closing bracket
                        json_end += 1
                        
                        # Extract and parse the JSON
                        try:
                            json_part = result[json_start:json_end]
                            data = json.loads(json_part)
                            
                            if isinstance(data, list):
                                logger.info(f"  - {section_name}: Found array with {len(data)} items")
                                for i, item in enumerate(data[:2], 1):  # Show first 2 items max
                                    if isinstance(item, dict):
                                        # Extract useful info based on the data structure
                                        if 'text' in item:
                                            text = item.get('text', '')[:50] + '...'
                                            logger.info(f"      {i}. Text: {text}")
                                        elif 'full_text' in item:
                                            text = item.get('full_text', '')[:50] + '...'
                                            logger.info(f"      {i}. Full text: {text}")
                                        
                                        # Add any other useful properties like username, date, etc.
                                        if 'user' in item and isinstance(item['user'], dict):
                                            username = item['user'].get('screen_name', 'unknown')
                                            logger.info(f"         User: @{username}")
                                    else:
                                        logger.info(f"      {i}. Item type: {type(item)}")
                            elif isinstance(data, dict):
                                logger.info(f"  - {section_name}: Found object with {len(data)} properties")
                                # Show top-level keys
                                logger.info(f"      Keys: {', '.join(list(data.keys())[:5])}" + 
                                          f"{' and more' if len(data) > 5 else ''}")
                            else:
                                logger.info(f"  - {section_name}: Found data of type {type(data)}")
                        except json.JSONDecodeError:
                            logger.info(f"  - {section_name}: Invalid JSON: {json_part[:50]}...")
                except Exception as e:
                    logger.error(f"Error analyzing results for '{term}': {str(e)}", exc_info=True)
            else:
                logger.error(f"Failed to search for '{term}'")
        
        logger.info("Twitter search test completed")
    except Exception as e:
        logger.error(f"Error in Twitter search test: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())