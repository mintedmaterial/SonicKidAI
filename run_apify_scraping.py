"""
Apify scraping workflow for both Twitter and website content
"""
import os
import sys
import asyncio
import logging
import signal
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from dotenv import load_dotenv
import httpx

from src.server.db import Database
from src.connections.apify_connection import ApifyConnection
from src.actions.apify_actions import ApifyActions
from src.services.content_scheduler import ContentScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Flag for shutdown signaling
shutdown_flag = False

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global shutdown_flag
    logger.info(f"Received signal {signum}. Starting graceful shutdown...")
    shutdown_flag = True

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def shutdown():
    """Perform graceful shutdown"""
    logger.info("Performing graceful shutdown...")
    # Any cleanup code would go here

async def run_twitter_scraper_direct(api_token: str, handles: List[str], max_tweets: int = 10) -> List[Dict[str, Any]]:
    """Run Twitter scraper directly with the API token"""
    logger.info(f"Running Twitter scraper for {len(handles)} handles")
    
    # Configuration for the scraper
    input_data = {
        "sourceType": "userHandle",
        "userHandles": handles,
        "maxItems": max_tweets,
        "tweetsDesired": "latest", 
        "includeReplies": False,
        "onlyVerifiedUsers": False,
    }
    
    try:
        # Direct API call to the actor
        async with httpx.AsyncClient(timeout=300) as client:  # 5 minute timeout
            response = await client.post(
                "https://api.apify.com/v2/acts/apidojo~twitter-scraper-lite/run-sync-get-dataset-items",
                params={"token": api_token},
                json=input_data,
            )
            
            if response.status_code != 201:
                logger.error(f"Twitter scraper API error: {response.status_code} - {response.text}")
                return []
            
            tweets = response.json()
            logger.info(f"Retrieved {len(tweets)} tweets from Twitter scraper")
            return tweets
            
    except Exception as e:
        logger.error(f"Error in Twitter scraper direct call: {e}")
        return []

async def run_twitter_scraper_fallback(api_token: str, handles: List[str], max_tweets: int = 10) -> List[Dict[str, Any]]:
    """Fallback method to run Twitter scraper by creating a run and polling for results"""
    logger.info(f"Running Twitter scraper (fallback) for {len(handles)} handles")
    
    # Configuration for the scraper
    input_data = {
        "sourceType": "userHandle",
        "userHandles": handles,
        "maxItems": max_tweets,
        "tweetsDesired": "latest", 
        "includeReplies": False,
        "onlyVerifiedUsers": False,
    }
    
    try:
        # Start a task and wait for it to complete
        async with httpx.AsyncClient(timeout=60) as client:
            # Start the task
            response = await client.post(
                "https://api.apify.com/v2/acts/apidojo~twitter-scraper-lite/runs",
                params={"token": api_token},
                json=input_data,
            )
            
            if response.status_code != 201:
                logger.error(f"Twitter scraper run start error: {response.status_code} - {response.text}")
                return []
            
            run_data = response.json()
            run_id = run_data.get("data", {}).get("id")
            
            if not run_id:
                logger.error(f"Failed to get run ID from response: {run_data}")
                return []
            
            logger.info(f"Started Twitter scraper run with ID: {run_id}")
            
            # Poll for task completion
            max_polls = 60  # 5 minutes with 5-second interval
            for _ in range(max_polls):
                await asyncio.sleep(5)  # Check every 5 seconds
                
                status_response = await client.get(
                    f"https://api.apify.com/v2/actor-runs/{run_id}",
                    params={"token": api_token},
                )
                
                if status_response.status_code != 200:
                    logger.error(f"Error checking run status: {status_response.status_code} - {status_response.text}")
                    continue
                
                status_data = status_response.json()
                status = status_data.get("data", {}).get("status")
                
                if status == "SUCCEEDED":
                    logger.info(f"Twitter scraper run completed successfully")
                    break
                
                if status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    logger.error(f"Twitter scraper run failed with status: {status}")
                    return []
                
                logger.info(f"Twitter scraper run status: {status}, waiting...")
            
            # Get the dataset items
            dataset_response = await client.get(
                f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items",
                params={"token": api_token},
            )
            
            if dataset_response.status_code != 200:
                logger.error(f"Error getting dataset items: {dataset_response.status_code} - {dataset_response.text}")
                return []
            
            tweets = dataset_response.json()
            logger.info(f"Retrieved {len(tweets)} tweets from Twitter scraper (fallback)")
            return tweets
            
    except Exception as e:
        logger.error(f"Error in Twitter scraper fallback: {e}")
        return []

async def run_website_scraper_direct(api_token: str, urls: List[str], max_depth: int = 1) -> List[Dict[str, Any]]:
    """Run website scraper directly with the API token"""
    logger.info(f"Running website scraper for {len(urls)} URLs")
    
    # Configuration for the website scraper
    input_data = {
        "startUrls": [{"url": url} for url in urls],
        "maxCrawlDepth": max_depth,
        "maxCrawlPages": 10 * len(urls),  # Limit pages per site
        "maxPagesPerCrawl": 50,  # Total max pages
        "includeUrlGlobs": [],
        "excludeUrlGlobs": [],
        "additionalMimeTypes": ["application/json"],
        "scenarioDebugMode": False,
    }
    
    try:
        # Direct API call to the actor
        async with httpx.AsyncClient(timeout=600) as client:  # 10 minute timeout
            response = await client.post(
                "https://api.apify.com/v2/acts/apify~website-content-crawler/run-sync-get-dataset-items",
                params={"token": api_token},
                json=input_data,
            )
            
            if response.status_code != 201:
                logger.error(f"Website scraper API error: {response.status_code} - {response.text}")
                return []
            
            content_items = response.json()
            logger.info(f"Retrieved {len(content_items)} content items from website scraper")
            return content_items
            
    except Exception as e:
        logger.error(f"Error in website scraper direct call: {e}")
        return []

async def run_website_scraper_fallback(api_token: str, urls: List[str], max_depth: int = 1) -> List[Dict[str, Any]]:
    """Fallback method to run website scraper by creating a run and polling for results"""
    logger.info(f"Running website scraper (fallback) for {len(urls)} URLs")
    
    # Configuration for the website scraper
    input_data = {
        "startUrls": [{"url": url} for url in urls],
        "maxCrawlDepth": max_depth,
        "maxCrawlPages": 10 * len(urls),  # Limit pages per site
        "maxPagesPerCrawl": 50,  # Total max pages
        "includeUrlGlobs": [],
        "excludeUrlGlobs": [],
        "additionalMimeTypes": ["application/json"],
        "scenarioDebugMode": False,
    }
    
    try:
        # Start a task and wait for it to complete
        async with httpx.AsyncClient(timeout=60) as client:
            # Start the task
            response = await client.post(
                "https://api.apify.com/v2/acts/apify~website-content-crawler/runs",
                params={"token": api_token},
                json=input_data,
            )
            
            if response.status_code != 201:
                logger.error(f"Website scraper run start error: {response.status_code} - {response.text}")
                return []
            
            run_data = response.json()
            run_id = run_data.get("data", {}).get("id")
            
            if not run_id:
                logger.error(f"Failed to get run ID from response: {run_data}")
                return []
            
            logger.info(f"Started website scraper run with ID: {run_id}")
            
            # Poll for task completion
            max_polls = 120  # 10 minutes with 5-second interval
            for _ in range(max_polls):
                await asyncio.sleep(5)  # Check every 5 seconds
                
                status_response = await client.get(
                    f"https://api.apify.com/v2/actor-runs/{run_id}",
                    params={"token": api_token},
                )
                
                if status_response.status_code != 200:
                    logger.error(f"Error checking run status: {status_response.status_code} - {status_response.text}")
                    continue
                
                status_data = status_response.json()
                status = status_data.get("data", {}).get("status")
                
                if status == "SUCCEEDED":
                    logger.info(f"Website scraper run completed successfully")
                    break
                
                if status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    logger.error(f"Website scraper run failed with status: {status}")
                    return []
                
                logger.info(f"Website scraper run status: {status}, waiting...")
            
            # Get the dataset items
            dataset_response = await client.get(
                f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items",
                params={"token": api_token},
            )
            
            if dataset_response.status_code != 200:
                logger.error(f"Error getting dataset items: {dataset_response.status_code} - {dataset_response.text}")
                return []
            
            content_items = dataset_response.json()
            logger.info(f"Retrieved {len(content_items)} content items from website scraper (fallback)")
            return content_items
            
    except Exception as e:
        logger.error(f"Error in website scraper fallback: {e}")
        return []

async def run_twitter_scraper(db: Database, api_token: str, handles: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Run Twitter scraper for specified handles and store in database"""
    # Default handles if none provided
    handles = handles or [
        "SonicLabs",
        "FutureIsFantom", 
        "AndreCronjeTech",
        "FantomFDN",
        "0xDT",
        "DeFiDad",
        "0xLegatez",
        "chain_crack",
    ]
    
    logger.info(f"Fetching tweets for handles: {handles}")
    
    # Initialize ApifyActions with the connection and database
    apify_connection = ApifyConnection(api_token)
    apify_actions = ApifyActions(apify_connection, db)
    
    # Use the unified method to fetch and store tweets
    result = await apify_actions.scrape_twitter_handles(handles)
    
    if result:
        logger.info(f"Successfully stored {result} tweets in database")
    else:
        logger.warning("No tweets were stored")
        
    return await db.query_tweets(query="", limit=10)

async def run_website_scraper(db: Database, api_token: str, urls: Optional[List[str]] = None, 
                             source_type: str = "defi_platforms") -> List[Dict[str, Any]]:
    """Run website content scraper for specified URLs and store in database"""
    # Default URLs if none provided
    urls = urls or [
        "https://www.shadow.so/liquidity",
        "https://beets.fi/pools?networks=SONIC",
        "https://app.pendle.finance/trade/markets",
        "https://paintswap.io/sonic/stats/global",
    ]
    
    logger.info(f"Fetching content for URLs: {urls}")
    
    # Initialize ApifyActions with the connection and database
    apify_connection = ApifyConnection(api_token)
    apify_actions = ApifyActions(apify_connection, db)
    
    # Use the unified method to fetch and store website content
    result = await apify_actions.scrape_website_urls(urls, source_type)
    
    if result:
        logger.info(f"Successfully stored {result} content items in database")
    else:
        logger.warning("No content items were stored")
        
    return await db.query_website_content(query="", limit=10)

async def run_both_scrapers():
    """Run both Twitter and website scrapers concurrently"""
    # Load environment variables
    load_dotenv()
    
    # Get API token and database URL
    api_token = os.getenv("APIFY_API_TOKEN")
    database_url = os.getenv("DATABASE_URL")
    
    if not api_token:
        logger.error("No Apify API token found. Please set the APIFY_API_TOKEN environment variable.")
        return
        
    if not database_url:
        logger.error("No database URL found. Please set the DATABASE_URL environment variable.")
        return
    
    # Initialize database
    db = Database(database_url)
    await db.connect()
    
    try:
        # Create tables if they don't exist
        await db.create_tables()
        
        # Run both scrapers concurrently
        twitter_task = asyncio.create_task(run_twitter_scraper(db, api_token))
        website_task = asyncio.create_task(run_website_scraper(db, api_token))
        
        # Wait for both to complete
        await asyncio.gather(twitter_task, website_task)
        
        logger.info("Both scrapers completed successfully")
        
    except Exception as e:
        logger.error(f"Error in scraper execution: {e}")
    finally:
        # Close database connection
        await db.close()

async def run_scheduler():
    """Run the content scheduler as a background service"""
    # Load environment variables
    load_dotenv()
    
    # Get API token and database URL
    api_token = os.getenv("APIFY_API_TOKEN")
    database_url = os.getenv("DATABASE_URL")
    
    if not api_token:
        logger.error("No Apify API token found. Please set the APIFY_API_TOKEN environment variable.")
        return
        
    if not database_url:
        logger.error("No database URL found. Please set the DATABASE_URL environment variable.")
        return
    
    # Initialize database
    db = Database(database_url)
    await db.connect()
    
    try:
        # Create tables if they don't exist
        await db.create_tables()
        
        # Initialize connections and actions
        apify_connection = ApifyConnection(api_token)
        apify_actions = ApifyActions(apify_connection, db)
        
        # Create custom scheduler for better logging
        class CustomContentScheduler(ContentScheduler):
            async def _run_twitter_scraper(self):
                """Run Twitter scraper task"""
                try:
                    logger.info(f"Running Twitter scraper for {len(self.twitter_handles)} handles")
                    result = await self.apify_actions.scrape_twitter_handles(self.twitter_handles)
                    if result:
                        logger.info(f"Twitter scraper completed successfully, stored {result} tweets")
                    else:
                        logger.warning("Twitter scraper completed but no tweets were stored")
                except Exception as e:
                    logger.error(f"Error in Twitter scraper task: {e}")
            
            async def _run_website_scraper(self):
                """Run website scraper task"""
                try:
                    logger.info(f"Running website scraper for {len(self.website_urls)} URLs")
                    result = await self.apify_actions.scrape_website_urls(self.website_urls, source_type="defi_platforms")
                    if result:
                        logger.info(f"Website scraper completed successfully, stored {result} content items")
                    else:
                        logger.warning("Website scraper completed but no content was stored")
                except Exception as e:
                    logger.error(f"Error in website scraper task: {e}")
        
        # Initialize and start scheduler
        scheduler = CustomContentScheduler(
            apify_actions=apify_actions,
            # Default intervals: Twitter every 4 hours, websites daily
        )
        
        await scheduler.start()
        
        logger.info("Content scheduler started. Press Ctrl+C to exit.")
        
        # Run until shutdown signal
        while not shutdown_flag:
            await asyncio.sleep(1)
            
        # Shutdown gracefully
        await scheduler.stop()
        logger.info("Content scheduler stopped")
        
    except Exception as e:
        logger.error(f"Error in scheduler execution: {e}")
    finally:
        # Close database connection
        await db.close()
        logger.info("Database connection closed")

async def main():
    """Main entry point"""
    # Load environment variables
    load_dotenv()
    
    # Check command line arguments for specific mode
    mode = None
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    
    # Default to running both scrapers once if no mode specified
    if mode == "scheduler":
        logger.info("Starting content scheduler service")
        await run_scheduler()
    elif mode == "twitter":
        logger.info("Running Twitter scraper only")
        # Get API token and database URL
        api_token = os.getenv("APIFY_API_TOKEN")
        database_url = os.getenv("DATABASE_URL")
        db = Database(database_url)
        await db.connect()
        try:
            await db.create_tables()
            await run_twitter_scraper(db, api_token)
        finally:
            await db.close()
    elif mode == "website":
        logger.info("Running website scraper only")
        # Get API token and database URL
        api_token = os.getenv("APIFY_API_TOKEN")
        database_url = os.getenv("DATABASE_URL")
        db = Database(database_url)
        await db.connect()
        try:
            await db.create_tables()
            await run_website_scraper(db, api_token)
        finally:
            await db.close()
    else:
        logger.info("Running both Twitter and website scrapers")
        await run_both_scrapers()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        import traceback
        logger.error(traceback.format_exc())