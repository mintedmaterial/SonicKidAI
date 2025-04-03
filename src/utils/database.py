"""
Database Connector for Discord integrations and tweet handling

This module provides async database functionality specifically for the Discord
tweet handling system to store and retrieve tweets from the database.
"""

import os
import json
import logging
import asyncpg
from typing import Dict, Any, List, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseConnector:
    """Database connection handler for Discord tweet processing"""
    
    def __init__(
        self, 
        database_url: Optional[str] = None
    ):
        """
        Initialize the database connector
        
        Args:
            database_url: PostgreSQL connection string, defaults to DATABASE_URL env var
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.connection = None
        self.is_connected = False
        
        if not self.database_url:
            logger.warning("No DATABASE_URL provided for DatabaseConnector")
    
    async def connect(self) -> bool:
        """
        Connect to PostgreSQL database
        
        Returns:
            bool: Whether the connection was successful
        """
        try:
            if not self.database_url:
                logger.error("Cannot connect: No DATABASE_URL provided")
                return False
                
            if self.connection and not self.connection.is_closed():
                logger.info("Already connected to database")
                return True
                
            logger.info("Connecting to PostgreSQL database...")
            self.connection = await asyncpg.connect(self.database_url)
            self.is_connected = True
            
            # Ensure the necessary tables exist
            await self._ensure_tables()
            
            logger.info("Successfully connected to PostgreSQL database")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to database: {str(e)}")
            self.is_connected = False
            return False
    
    async def close(self) -> None:
        """Close the database connection"""
        try:
            if self.connection:
                await self.connection.close()
                self.connection = None
                self.is_connected = False
                logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {str(e)}")
    
    async def _ensure_tables(self) -> None:
        """Ensure all required tables exist in the database"""
        try:
            # Create discord_tweets table if it doesn't exist
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS discord_tweets (
                    id SERIAL PRIMARY KEY,
                    message_id TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    author TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Create index on channel_id for faster lookups
            await self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_discord_tweets_channel_id 
                ON discord_tweets(channel_id)
            """)
            
            logger.info("Database tables verified")
        except Exception as e:
            logger.error(f"Error ensuring database tables: {str(e)}")
            raise
    
    async def store_tweet(
        self,
        content: str,
        channel_id: str,
        message_id: str,
        author: str,
        timestamp: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store a tweet from Discord in the database
        
        Args:
            content: The tweet content
            channel_id: Discord channel ID
            message_id: Discord message ID
            author: Author of the tweet
            timestamp: When the tweet was posted
            metadata: Optional metadata about the tweet
            
        Returns:
            bool: Whether the tweet was stored successfully
        """
        try:
            if not self.is_connected:
                logger.warning("Cannot store tweet: Not connected to database")
                if not await self.connect():
                    return False
            
            # Store the tweet in the discord_tweets table
            await self.connection.execute("""
                INSERT INTO discord_tweets (
                    message_id, channel_id, author, content, timestamp, metadata, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
            """, 
                message_id, 
                channel_id, 
                author, 
                content, 
                timestamp,
                json.dumps(metadata) if metadata else None
            )
            
            # Use the same values to also insert into twitter_scrape_data table
            # This keeps backward compatibility with existing Twitter data storage
            metadata_with_source = metadata or {}
            metadata_with_source["source"] = "discord_tweet_handler"
            metadata_with_source["channelId"] = channel_id
            metadata_with_source["authorName"] = author
            
            await self.connection.execute("""
                INSERT INTO twitter_scrape_data (
                    tweetId, username, content, timestamp, metadata, contractAddresses
                ) VALUES ($1, $2, $3, $4, $5, $6)
            """, 
                message_id,
                author.lower().replace(" ", "_"),  # Convert to username format
                content,
                timestamp,
                json.dumps(metadata_with_source),
                []  # Empty contractAddresses array
            )
            
            logger.info(f"Successfully stored tweet ID {message_id} in database")
            return True
            
        except Exception as e:
            logger.error(f"Error storing tweet in database: {str(e)}")
            return False
    
    async def get_recent_tweets(
        self, 
        channel_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent tweets from the database
        
        Args:
            channel_id: Optional channel ID to filter by
            limit: Maximum number of tweets to return
            
        Returns:
            List of tweet dictionaries
        """
        try:
            if not self.is_connected:
                logger.warning("Cannot get tweets: Not connected to database")
                if not await self.connect():
                    return []
            
            # Build the query based on whether channel_id is provided
            query = """
                SELECT 
                    id, message_id, channel_id, author, content, 
                    timestamp, metadata, created_at
                FROM discord_tweets
            """
            
            params = []
            if channel_id:
                query += " WHERE channel_id = $1"
                params.append(channel_id)
                
            # Add order and limit
            query += " ORDER BY timestamp DESC LIMIT $" + str(len(params) + 1)
            params.append(limit)
            
            # Execute the query
            rows = await self.connection.fetch(query, *params)
            
            # Convert to a list of dictionaries
            tweets = []
            for row in rows:
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
                tweets.append({
                    'id': row['id'],
                    'message_id': row['message_id'],
                    'channel_id': row['channel_id'],
                    'author': row['author'],
                    'content': row['content'],
                    'timestamp': row['timestamp'].isoformat(),
                    'metadata': metadata,
                    'created_at': row['created_at'].isoformat()
                })
                
            logger.info(f"Retrieved {len(tweets)} tweets from database")
            return tweets
            
        except Exception as e:
            logger.error(f"Error retrieving tweets from database: {str(e)}")
            return []
            
    async def get_tweet_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific tweet by its message ID
        
        Args:
            message_id: Discord message ID
            
        Returns:
            Tweet dictionary or None if not found
        """
        try:
            if not self.is_connected:
                logger.warning("Cannot get tweet: Not connected to database")
                if not await self.connect():
                    return None
            
            # Query the database
            row = await self.connection.fetchrow("""
                SELECT 
                    id, message_id, channel_id, author, content, 
                    timestamp, metadata, created_at
                FROM discord_tweets
                WHERE message_id = $1
            """, message_id)
            
            if not row:
                logger.warning(f"No tweet found with message ID: {message_id}")
                return None
                
            # Convert to dictionary
            metadata = json.loads(row['metadata']) if row['metadata'] else {}
            tweet = {
                'id': row['id'],
                'message_id': row['message_id'],
                'channel_id': row['channel_id'],
                'author': row['author'],
                'content': row['content'],
                'timestamp': row['timestamp'].isoformat(),
                'metadata': metadata,
                'created_at': row['created_at'].isoformat()
            }
                
            logger.info(f"Retrieved tweet with message ID: {message_id}")
            return tweet
            
        except Exception as e:
            logger.error(f"Error retrieving tweet from database: {str(e)}")
            return None
            
    async def get_tweet_count(self, channel_id: Optional[str] = None) -> int:
        """
        Get count of tweets in the database
        
        Args:
            channel_id: Optional channel ID to filter by
            
        Returns:
            Count of tweets
        """
        try:
            if not self.is_connected:
                logger.warning("Cannot get tweet count: Not connected to database")
                if not await self.connect():
                    return 0
            
            # Build the query based on whether channel_id is provided
            query = "SELECT COUNT(*) FROM discord_tweets"
            params = []
            
            if channel_id:
                query += " WHERE channel_id = $1"
                params.append(channel_id)
                
            # Execute the query
            count = await self.connection.fetchval(query, *params)
            logger.info(f"Tweet count: {count}")
            return count
            
        except Exception as e:
            logger.error(f"Error getting tweet count from database: {str(e)}")
            return 0