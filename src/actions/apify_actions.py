#!/usr/bin/env python3
"""
Apify actions class for handling business logic
between API connection and database
"""
import logging
from typing import Dict, List, Optional, Any, Union

from src.connections.apify_connection import ApifyConnection
from src.server.db import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class ApifyActions:
    """Actions class for handling business logic"""
    
    def __init__(self, api_token: Optional[str] = None, database: Optional[Database] = None):
        """Initialize actions with connection and database"""
        self.connection = ApifyConnection(api_token)
        self.database = database
    
    async def verify_connection(self) -> bool:
        """Verify connection to Apify API"""
        return await self.connection.verify_connection()
    
    async def fetch_twitter_data(self, handles: List[str], max_tweets: int = 10) -> List[Dict[str, Any]]:
        """Fetch Twitter data for specified handles and store in database"""
        if not handles:
            logger.warning("No Twitter handles provided")
            return []
        
        logger.info(f"Fetching Twitter data for {len(handles)} handles")
        
        try:
            # Fetch tweets using the synchronized API endpoint
            tweets = await self.connection.run_twitter_scraper_sync(handles, max_tweets)
            
            if not tweets:
                logger.error("No tweets returned from scraper")
                return []
            
            logger.info(f"Retrieved {len(tweets)} tweets")
            
            # Store tweets in database if available
            if self.database:
                stored_count = await self.database.store_tweets(tweets)
                logger.info(f"Stored {stored_count} tweets in database")
            else:
                logger.warning("Database not provided, tweets not stored")
            
            return tweets
        except Exception as e:
            logger.error(f"Error fetching Twitter data: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    async def fetch_website_content(self, urls: List[str], max_depth: int = 1, source_type: str = "general") -> List[Dict[str, Any]]:
        """Fetch website content for specified URLs and store in database"""
        if not urls:
            logger.warning("No URLs provided")
            return []
        
        logger.info(f"Fetching website content for {len(urls)} URLs")
        
        try:
            # Fetch content using the synchronized API endpoint
            content_items = await self.connection.run_website_scraper_sync(urls, max_depth)
            
            if not content_items:
                logger.error("No content items returned from scraper")
                return []
            
            logger.info(f"Retrieved {len(content_items)} content items")
            
            # Store content in database if available
            if self.database:
                stored_count = await self.database.store_website_content(content_items, source_type)
                logger.info(f"Stored {stored_count} content items in database")
            else:
                logger.warning("Database not provided, content not stored")
            
            return content_items
        except Exception as e:
            logger.error(f"Error fetching website content: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    async def query_tweets(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Query tweets by content"""
        if not self.database:
            logger.error("Database not provided")
            return []
        
        return await self.database.query_tweets(query, limit)
    
    async def query_website_content(self, query: str, source_type: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Query website content by content and optional source type"""
        if not self.database:
            logger.error("Database not provided")
            return []
        
        return await self.database.query_website_content(query, source_type, limit)
    
    async def get_recent_tweets(self, author: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent tweets, optionally filtered by author"""
        if not self.database:
            logger.error("Database not provided")
            return []
        
        return await self.database.get_recent_tweets(author, limit)
    
    async def get_recent_content(self, source_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent website content, optionally filtered by source type"""
        if not self.database:
            logger.error("Database not provided")
            return []
        
        return await self.database.get_recent_content(source_type, limit)
    
    async def close(self):
        """Close connections"""
        if self.connection:
            await self.connection.close()
        
        if self.database:
            await self.database.close()