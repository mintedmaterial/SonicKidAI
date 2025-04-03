#!/usr/bin/env python3
"""
Apify API Connection Class
Handles direct communication with the Apify API for web scraping tasks
"""
import os
import logging
import json
from typing import Dict, List, Optional, Any, Union

import httpx
from dotenv import load_dotenv
from apify_client import ApifyClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class ApifyConnection:
    """Connection class for Apify API integration"""
    
    def __init__(self, api_token: Optional[str] = None):
        """Initialize Apify connection with API token"""
        # Load environment variables if token not provided
        if not api_token:
            load_dotenv()
            api_token = os.environ.get("APIFY_API_TOKEN")
        
        self.api_token = api_token
        if not self.api_token:
            raise ValueError("Apify API token not provided")
        
        # Initialize HTTP client for direct API calls
        self.client = httpx.AsyncClient(timeout=120.0)  # 2-minute timeout
        
        # Initialize Apify SDK client
        self.apify_client = ApifyClient(self.api_token)
        self.initialized = False
        
    async def verify_connection(self) -> bool:
        """Verify API token and connection by fetching user data"""
        try:
            # Use direct HTTP request to get user info
            url = "https://api.apify.com/v2/users/me"
            headers = {"Authorization": f"Bearer {self.api_token}"}
            
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            
            user_data = response.json()
            username = user_data.get("data", {}).get("username", "unknown")
            
            logger.info(f"Connected to Apify as user: {username}")
            self.initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to verify Apify connection: {e}")
            return False
    
    async def run_twitter_scraper_sync(self, handles: List[str], max_tweets: int = 10) -> List[Dict[str, Any]]:
        """Run Twitter scraper with synchronized API endpoint"""
        if not self.initialized and not await self.verify_connection():
            raise ConnectionError("Failed to connect to Apify API")
        
        logger.info(f"Starting synchronous Twitter scraper for {len(handles)} handles")
        
        try:
            # Prepare Twitter scraper input
            input_data = {
                "usernames": handles,
                "tweetsDesired": max_tweets,
                "includeReplies": False,
                "skipTweetReplyBlocks": True,
                "includeRetweets": False,
                "includeLinkToProfile": True,
                "waitBetweenRequests": 5
            }
            
            # Build direct synchronous API URL
            base_url = "https://api.apify.com/v2/acts/apidojo~twitter-scraper-lite/run-sync-get-dataset-items"
            
            # Make synchronous API call
            response = await self.client.post(
                base_url,
                params={"token": self.api_token},
                json=input_data,
                timeout=300.0  # 5-minute timeout for sync request
            )
            
            response.raise_for_status()
            tweets = response.json()
            
            logger.info(f"Retrieved {len(tweets)} tweets from Twitter scraper")
            return tweets
        except Exception as e:
            logger.error(f"Error running Twitter scraper: {e}")
            return []
    
    async def run_website_scraper_sync(self, urls: List[str], max_depth: int = 1) -> List[Dict[str, Any]]:
        """Run website scraper with synchronized API endpoint"""
        if not self.initialized and not await self.verify_connection():
            raise ConnectionError("Failed to connect to Apify API")
        
        logger.info(f"Starting synchronous website scraper for {len(urls)} URLs")
        
        try:
            # Prepare website scraper input
            input_data = {
                "startUrls": [{"url": url} for url in urls],
                "maxCrawlDepth": max_depth,
                "maxCrawlPages": 10 * len(urls),  # Limit to 10 pages per URL
                "maxPagesPerCrawl": 10 * len(urls),
                "limitCrawlDepth": True,
                "saveContent": True,
                "saveContentAsMarkdown": True,
                "blockRequests": "font, media, image, stylesheet, script",
                "headless": True
            }
            
            # Build direct synchronous API URL
            base_url = "https://api.apify.com/v2/acts/apify~website-content-crawler/run-sync-get-dataset-items"
            
            # Make synchronous API call
            response = await self.client.post(
                base_url,
                params={"token": self.api_token},
                json=input_data,
                timeout=600.0  # 10-minute timeout for sync request
            )
            
            response.raise_for_status()
            content_items = response.json()
            
            logger.info(f"Retrieved {len(content_items)} content items from website scraper")
            return content_items
        except Exception as e:
            logger.error(f"Error running website scraper: {e}")
            return []
    
    async def close(self):
        """Close the HTTP client"""
        if self.client:
            await self.client.aclose()
            logger.info("Apify connection closed")