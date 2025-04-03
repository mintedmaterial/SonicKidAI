"""
Content scheduler service for regularly updating social media and website content
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from src.actions.apify_actions import ApifyActions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class ContentScheduler:
    """Service for scheduling regular content scraping and updates
    
    This service handles regular scheduled updates of Twitter and website content
    from configured sources, storing the data in the database for later use.
    """
    def __init__(
        self,
        apify_actions: ApifyActions,
        twitter_handles: Optional[List[str]] = None,
        website_urls: Optional[List[str]] = None,
        twitter_update_interval: timedelta = timedelta(hours=4),  # Default: every 4 hours
        website_update_interval: timedelta = timedelta(days=1),   # Default: daily
    ):
        """Initialize the content scheduler service
        
        Args:
            apify_actions: Actions for interacting with Apify API
            twitter_handles: List of Twitter handles to scrape
            website_urls: List of website URLs to scrape
            twitter_update_interval: Time between Twitter updates
            website_update_interval: Time between website content updates
        """
        self.apify_actions = apify_actions
        self.twitter_handles = twitter_handles or [
            "SonicLabs",
            "FutureIsFantom", 
            "AndreCronjeTech",
            "FantomFDN",
            "0xDT",
            "DeFiDad",
            "0xLegatez",
            "chain_crack",
        ]
        self.website_urls = website_urls or [
            "https://www.shadow.so/liquidity",
            "https://beets.fi/pools?networks=SONIC",
            "https://app.pendle.finance/trade/markets",
            "https://paintswap.io/sonic/stats/global",
        ]
        self.twitter_update_interval = twitter_update_interval
        self.website_update_interval = website_update_interval
        
        self.twitter_task = None
        self.website_task = None
        self.is_running = False
        
        logger.info(f"Content scheduler initialized with {len(self.twitter_handles)} Twitter handles and {len(self.website_urls)} website URLs")
    
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
    
    async def _twitter_update_loop(self):
        """Background loop for regular Twitter updates"""
        while self.is_running:
            try:
                await self._run_twitter_scraper()
                logger.info(f"Waiting {self.twitter_update_interval} until next Twitter update")
                await asyncio.sleep(self.twitter_update_interval.total_seconds())
            except asyncio.CancelledError:
                logger.info("Twitter update task cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in Twitter update loop: {e}")
                # Wait a short time before retrying after error
                await asyncio.sleep(60)
    
    async def _website_update_loop(self):
        """Background loop for regular website content updates"""
        while self.is_running:
            try:
                await self._run_website_scraper()
                logger.info(f"Waiting {self.website_update_interval} until next website content update")
                await asyncio.sleep(self.website_update_interval.total_seconds())
            except asyncio.CancelledError:
                logger.info("Website update task cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in website update loop: {e}")
                # Wait a short time before retrying after error
                await asyncio.sleep(60)
    
    async def start(self):
        """Start the scheduled content updates"""
        if self.is_running:
            logger.warning("Content scheduler is already running")
            return
        
        self.is_running = True
        logger.info("Starting content scheduler service")
        
        # Create tasks for regular updates
        self.twitter_task = asyncio.create_task(self._twitter_update_loop())
        self.website_task = asyncio.create_task(self._website_update_loop())
        
        logger.info("Content scheduler service started")
    
    async def stop(self):
        """Stop the scheduled content updates"""
        if not self.is_running:
            logger.warning("Content scheduler is not running")
            return
        
        self.is_running = False
        logger.info("Stopping content scheduler service")
        
        # Cancel the update tasks
        if self.twitter_task:
            self.twitter_task.cancel()
            try:
                await self.twitter_task
            except asyncio.CancelledError:
                pass
            self.twitter_task = None
        
        if self.website_task:
            self.website_task.cancel()
            try:
                await self.website_task
            except asyncio.CancelledError:
                pass
            self.website_task = None
        
        logger.info("Content scheduler service stopped")