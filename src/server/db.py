#!/usr/bin/env python3
"""
Database interface class for storing and retrieving data
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any, Union

import asyncpg

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class Database:
    """Database interface class for storing scraped data"""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize the database connection with a URL"""
        self.database_url = database_url or os.environ.get("DATABASE_URL")
        if not self.database_url:
            raise ValueError("No database URL provided")
        
        logger.info(f"Database initialized with URL: {self.database_url[:10]}...")
        self.pool = None
    
    async def connect(self) -> bool:
        """Connect to the database and create a connection pool"""
        try:
            self.pool = await asyncpg.create_pool(self.database_url)
            logger.info("Connected to database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    async def create_tables(self) -> bool:
        """Create tables for storing scraped data if they don't exist"""
        if not self.pool:
            logger.error("Database not connected")
            return False
        
        try:
            # Create Twitter data table
            await self.pool.execute('''
                CREATE TABLE IF NOT EXISTS twitter_data (
                    id SERIAL PRIMARY KEY,
                    tweet_id TEXT UNIQUE,
                    content TEXT,
                    author TEXT,
                    sentiment TEXT,
                    category TEXT,
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            logger.info("Twitter data table created/verified")
            
            # Create website content data table
            await self.pool.execute('''
                CREATE TABLE IF NOT EXISTS website_content_data (
                    id SERIAL PRIMARY KEY,
                    metadata JSONB,
                    content TEXT,
                    markdown_content TEXT,
                    source_type TEXT,
                    url TEXT,
                    title TEXT,
                    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            logger.info("Website content data table created/verified")
            
            return True
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            return False
    
    async def store_tweets(self, tweets: List[Dict[str, Any]]) -> int:
        """Store tweets in the database
        
        This handles both formats:
        1. Original Twitter API format with id, text, author fields
        2. Apify dataset format with type, id, text fields
        """
        if not self.pool:
            logger.error("Database not connected")
            return 0
        
        if not tweets:
            logger.warning("No tweets to store")
            return 0
        
        try:
            count = 0
            for tweet in tweets:
                # Check data format and extract fields accordingly
                if "type" in tweet and tweet.get("type") == "tweet":
                    # This is Apify dataset format
                    tweet_id = tweet.get("id", "unknown")
                    content = tweet.get("text", "") or tweet.get("fullText", "")
                    author_obj = tweet.get("author", {})
                    author = author_obj.get("username", "unknown") if isinstance(author_obj, dict) else "unknown"
                    # Use author name if username is not available
                    if author == "unknown" and isinstance(author_obj, dict) and "name" in author_obj:
                        author = author_obj.get("name", "unknown")
                else:
                    # Try original format
                    tweet_id = tweet.get("tweetId", tweet.get("id", "unknown"))
                    content = tweet.get("text", "")
                    author = tweet.get("username", tweet.get("author", "unknown"))
                
                # Default values
                sentiment = "0.0"  # Default neutral sentiment as string
                category = "general"  # Default category
                
                # Store the entire tweet as metadata
                metadata = json.dumps(tweet)
                
                # Check if tweet already exists
                existing = await self.pool.fetchval(
                    "SELECT id FROM twitter_data WHERE tweet_id = $1",
                    str(tweet_id)  # Ensure tweet_id is a string
                )
                
                if existing:
                    # Update existing tweet
                    await self.pool.execute('''
                        UPDATE twitter_data 
                        SET 
                            content = $1,
                            author = $2,
                            sentiment = $3,
                            category = $4,
                            metadata = $5
                        WHERE tweet_id = $6
                    ''', content, author, sentiment, category, metadata, str(tweet_id))
                else:
                    # Insert new tweet
                    await self.pool.execute('''
                        INSERT INTO twitter_data 
                        (tweet_id, content, author, sentiment, category, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    ''', str(tweet_id), content, author, sentiment, category, metadata)
                
                count += 1
            
            logger.info(f"Stored {count} tweets in database")
            return count
        except Exception as e:
            logger.error(f"Failed to store tweets: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return 0
    
    async def store_website_content(self, content_items: List[Dict[str, Any]], source_type: str = "general") -> int:
        """Store website content in the database
        
        This handles multiple formats:
        1. Original website content format
        2. Apify website-content-crawler dataset format with url, text, markdown fields
        3. Tweet dataset format with tweet details (for Twitter content)
        """
        if not self.pool:
            logger.error("Database not connected")
            return 0
        
        if not content_items:
            logger.warning("No content items to store")
            return 0
        
        try:
            count = 0
            for item in content_items:
                # Extract content data based on format
                url = item.get("url", "")
                
                # Title extraction handling different formats
                if "metadata" in item and isinstance(item["metadata"], dict) and "title" in item["metadata"]:
                    # Nested in metadata field
                    title = item["metadata"].get("title", "")
                elif "title" in item:
                    # Direct title field
                    title = item.get("title", "")
                elif "type" in item and item.get("type") == "tweet":
                    # Tweet format - use author's username as title
                    author_obj = item.get("author", {})
                    if isinstance(author_obj, dict):
                        title = f"Tweet from @{author_obj.get('username', 'unknown')}"
                    else:
                        title = "Tweet"
                else:
                    title = ""
                
                # Content extraction handling different formats
                if "text" in item:
                    # Apify crawler or tweet format
                    content = item.get("text", "")
                elif "content" in item:
                    # Original format
                    content = item.get("content", "")
                else:
                    content = ""
                
                # Markdown content extraction
                if "markdown" in item:
                    markdown_content = item.get("markdown", "")
                elif "fullText" in item and "text" in item:
                    # Tweet format - use fullText as markdown
                    markdown_content = item.get("fullText", item.get("text", ""))
                else:
                    markdown_content = ""
                
                # Store the entire item as metadata
                metadata = json.dumps(item)
                
                if not url:
                    logger.warning(f"Skipping item with no URL: {title[:30]}...")
                    continue
                
                # Check if content already exists for this URL
                existing = await self.pool.fetchval(
                    "SELECT id FROM website_content_data WHERE url = $1",
                    url
                )
                
                if existing:
                    # Update existing content
                    await self.pool.execute('''
                        UPDATE website_content_data 
                        SET 
                            metadata = $1,
                            content = $2,
                            markdown_content = $3,
                            title = $4,
                            source_type = $5,
                            scraped_at = NOW()
                        WHERE url = $6
                    ''', metadata, content, markdown_content, title, source_type, url)
                else:
                    # Insert new content
                    await self.pool.execute('''
                        INSERT INTO website_content_data 
                        (metadata, content, markdown_content, source_type, url, title)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    ''', metadata, content, markdown_content, source_type, url, title)
                
                count += 1
            
            logger.info(f"Stored {count} content items in database")
            return count
        except Exception as e:
            logger.error(f"Failed to store website content: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return 0
    
    async def query_tweets(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Query tweets by content match"""
        if not self.pool:
            logger.error("Database not connected")
            return []
        
        try:
            # Simple text search query
            rows = await self.pool.fetch('''
                SELECT * FROM twitter_data
                WHERE content ILIKE $1
                ORDER BY created_at DESC
                LIMIT $2
            ''', f'%{query}%', limit)
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to query tweets: {e}")
            return []
    
    async def query_website_content(self, query: str, source_type: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Query website content by content match and optional source type"""
        if not self.pool:
            logger.error("Database not connected")
            return []
        
        try:
            if source_type:
                # Search by content and source type
                rows = await self.pool.fetch('''
                    SELECT * FROM website_content_data
                    WHERE 
                        (content ILIKE $1 OR markdown_content ILIKE $1)
                        AND source_type = $2
                    ORDER BY scraped_at DESC
                    LIMIT $3
                ''', f'%{query}%', source_type, limit)
            else:
                # Search by content only
                rows = await self.pool.fetch('''
                    SELECT * FROM website_content_data
                    WHERE content ILIKE $1 OR markdown_content ILIKE $1
                    ORDER BY scraped_at DESC
                    LIMIT $2
                ''', f'%{query}%', limit)
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to query website content: {e}")
            return []
    
    async def get_recent_tweets(self, author: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent tweets, optionally filtered by author"""
        if not self.pool:
            logger.error("Database not connected")
            return []
        
        try:
            if author:
                # Filter by author
                rows = await self.pool.fetch('''
                    SELECT * FROM twitter_data
                    WHERE author = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                ''', author, limit)
            else:
                # Get all recent tweets
                rows = await self.pool.fetch('''
                    SELECT * FROM twitter_data
                    ORDER BY created_at DESC
                    LIMIT $1
                ''', limit)
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get recent tweets: {e}")
            return []
    
    async def get_recent_content(self, source_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent website content, optionally filtered by source type"""
        if not self.pool:
            logger.error("Database not connected")
            return []
        
        try:
            if source_type:
                # Filter by source type
                rows = await self.pool.fetch('''
                    SELECT * FROM website_content_data
                    WHERE source_type = $1
                    ORDER BY scraped_at DESC
                    LIMIT $2
                ''', source_type, limit)
            else:
                # Get all recent content
                rows = await self.pool.fetch('''
                    SELECT * FROM website_content_data
                    ORDER BY scraped_at DESC
                    LIMIT $1
                ''', limit)
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get recent content: {e}")
            return []
    
    async def close(self):
        """Close the database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection closed")