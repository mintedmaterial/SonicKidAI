"""
Twitter Client Factory

This module provides a factory function for creating Twitter client connections.
"""

from typing import Dict, Any, Optional
from src.connections.base_connection import BaseConnection
from src.connections.twitter_client import TwitterClient
from src.connection_manager import register_connection_factory

@register_connection_factory("twitter_client")
def create_twitter_client(config: Dict[str, Any]) -> Optional[BaseConnection]:
    """Create a Twitter client connection"""
    try:
        return TwitterClient(config)
    except Exception as e:
        # Log error and return None to indicate failure
        print(f"Failed to create Twitter client: {str(e)}")
        return None