"""
Twitter Client Factory

This module provides a factory for creating Twitter clients.
"""

import logging
from typing import Optional

from src.connections.twitter_client import TwitterClient

logger = logging.getLogger(__name__)

class TwitterClientFactory:
    """Factory for creating Twitter clients"""
    
    @staticmethod
    async def create_client() -> TwitterClient:
        """
        Create and return a Twitter client
        
        Returns:
            Initialized TwitterClient instance
        """
        logger.info("Creating Twitter client")
        client = TwitterClient()
        return client