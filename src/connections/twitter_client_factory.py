"""
Twitter Client Factory

This module provides a factory function for creating Twitter client instances.
"""

import logging
from typing import Optional

from src.connections.twitter_client import TwitterClient

logger = logging.getLogger(__name__)

async def create_twitter_client() -> Optional[TwitterClient]:
    """
    Create and authenticate a Twitter client
    
    Returns:
        An authenticated TwitterClient instance or None if authentication failed
    """
    try:
        # Create the client
        client = TwitterClient()
        logger.info("Created Twitter client")
        
        # Authenticate
        authentication_successful = await client.authenticate()
        if authentication_successful:
            logger.info("Twitter client authenticated successfully")
            return client
        else:
            logger.error("Twitter client authentication failed")
            return None
    except Exception as e:
        logger.exception(f"Error creating Twitter client: {e}")
        return None