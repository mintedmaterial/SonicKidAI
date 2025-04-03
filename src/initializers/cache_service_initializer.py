"""
Cache Service Initializer

This module initializes the cache service for API endpoints
to ensure optimal refresh rates while respecting rate limits.
"""
import logging
import asyncio
from typing import Dict, Any, Optional
import json
import os

from src.services.cache_service import cache_service
from src.services.api_cache_wrapper import initialize_cache_service, shutdown_cache_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default refresh intervals (seconds) for different data types
DEFAULT_REFRESH_INTERVALS = {
    "price": 60,             # Price data - refresh every minute
    "sentiment": 120,        # Sentiment data - refresh every 2 minutes
    "news": 300,             # News data - refresh every 5 minutes
    "fear-greed": 1800,      # Fear & Greed index - refresh every 30 minutes
    "trending": 600,         # Trending tokens - refresh every 10 minutes
    "dex-volume": 300,       # DEX volume data - refresh every 5 minutes
    "sonic-pairs": 120,      # Sonic pairs data - refresh every 2 minutes
    "sales": 600,            # Sales data - refresh every 10 minutes
}

async def initialize(custom_intervals: Optional[Dict[str, int]] = None):
    """
    Initialize the cache service with optimal refresh intervals
    
    Args:
        custom_intervals: Optional dictionary with custom refresh intervals
    """
    logger.info("Starting cache service initializer...")
    
    # Merge default intervals with custom intervals
    refresh_intervals = DEFAULT_REFRESH_INTERVALS.copy()
    if custom_intervals:
        refresh_intervals.update(custom_intervals)
    
    # Configure refresh intervals for different data types
    for data_type, interval in refresh_intervals.items():
        cache_service.set_refresh_interval(data_type, interval)
        logger.info(f"Set refresh interval for {data_type} to {interval}s")
    
    # Initialize cache service with background refresh
    success = await initialize_cache_service()
    
    if success:
        logger.info("✅ Cache service initialized successfully with background refresh")
    else:
        logger.error("❌ Cache service initialization failed")
    
    return success

async def shutdown():
    """Stop the cache service properly"""
    logger.info("Shutting down cache service...")
    await shutdown_cache_service()
    logger.info("✅ Cache service shutdown complete")