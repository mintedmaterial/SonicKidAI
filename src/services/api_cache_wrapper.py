"""
API Cache Wrapper Service for Dashboard Endpoints

This module provides wrapper functions for API endpoints that uses the
cache service to prevent excessive API calls and respect rate limits
while keeping data fresh for users.
"""
import logging
import asyncio
import json
from typing import Dict, Any, Optional, Callable, Awaitable, List, Tuple, Union
from functools import wraps
import time

from .cache_service import cache_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def cached_endpoint(data_type: str, cache_key_func: Optional[Callable] = None):
    """
    Decorator for API endpoint handlers to enable caching
    
    Args:
        data_type: The type of data (used for setting refresh intervals)
        cache_key_func: Optional function to extract cache key from request args/kwargs
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from args/kwargs
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                # Default: use function name + args + sorted kwargs as cache key
                key_parts = [func.__name__]
                if args:
                    key_parts.extend([str(arg) for arg in args])
                if kwargs:
                    # Sort kwargs for consistent ordering
                    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
                cache_key = ":".join(key_parts)
            
            # Define refresh callback that will execute the actual function
            async def refresh_data():
                start = time.time()
                result = await func(*args, **kwargs)
                elapsed = time.time() - start
                logger.debug(f"Fetched fresh data for {data_type}:{cache_key} in {elapsed:.2f}s")
                return result
            
            # Get from cache or refresh
            result, is_fresh = await cache_service.get(
                cache_key=cache_key,
                data_type=data_type,
                refresh_callback=refresh_data
            )
            
            # On first run or if we have no data, this might still be None
            if result is None:
                result = await refresh_data()
                await cache_service.set(cache_key, data_type, result)
            
            return result
        return wrapper
    return decorator

# Pre-configured wrappers for common endpoint types
def cached_price_endpoint(cache_key_func=None):
    """Cache wrapper for price endpoints (refresh every 60s)"""
    return cached_endpoint("price", cache_key_func)

def cached_sonic_price_endpoint(cache_key_func=None):
    """Cache wrapper for Sonic price endpoints (refresh every 20s - 3x per minute)"""
    return cached_endpoint("sonic-price", cache_key_func)

def cached_sentiment_endpoint(cache_key_func=None):
    """Cache wrapper for sentiment endpoints (refresh every 120s)"""
    return cached_endpoint("sentiment", cache_key_func)

def cached_news_endpoint(cache_key_func=None):
    """Cache wrapper for news endpoints (refresh every 300s)"""
    return cached_endpoint("news", cache_key_func)

def cached_fear_greed_endpoint(cache_key_func=None):
    """Cache wrapper for fear-greed endpoints (refresh every 1800s)"""
    return cached_endpoint("fear-greed", cache_key_func)

def cached_trending_endpoint(cache_key_func=None):
    """Cache wrapper for trending endpoints (refresh every 600s)"""
    return cached_endpoint("trending", cache_key_func)

def cached_dex_volume_endpoint(cache_key_func=None):
    """Cache wrapper for dex-volume endpoints (refresh every 300s)"""
    return cached_endpoint("dex-volume", cache_key_func)

def cached_sonic_pairs_endpoint(cache_key_func=None):
    """Cache wrapper for sonic-pairs endpoints (refresh every 120s)"""
    return cached_endpoint("sonic-pairs", cache_key_func)

def cached_sales_endpoint(cache_key_func=None):
    """Cache wrapper for sales endpoints (refresh every 600s)"""
    return cached_endpoint("sales", cache_key_func)

async def get_cache_stats():
    """Get statistics about the cache"""
    return await cache_service.get_stats()

async def invalidate_cache(data_type: Optional[str] = None, cache_key: Optional[str] = None):
    """
    Invalidate cache entries
    
    Args:
        data_type: Optional data type to invalidate
        cache_key: Optional specific cache key to invalidate
    
    Returns:
        Dict with invalidation status
    """
    if data_type and cache_key:
        # Invalidate specific entry
        await cache_service.invalidate(cache_key, data_type)
        return {"status": "ok", "message": f"Invalidated cache for {data_type}:{cache_key}"}
    elif data_type:
        # Invalidate all entries of a type
        await cache_service.clear(data_type)
        return {"status": "ok", "message": f"Invalidated all {data_type} cache entries"}
    else:
        # Invalidate everything
        await cache_service.clear()
        return {"status": "ok", "message": "Invalidated all cache entries"}

async def initialize_cache_service():
    """Initialize the cache service and start background refresh"""
    try:
        await cache_service.start_background_refresh()
        logger.info("✅ API cache service initialized with background refresh")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize API cache service: {str(e)}")
        return False

async def shutdown_cache_service():
    """Shutdown the cache service"""
    try:
        await cache_service.stop_background_refresh()
        logger.info("✅ API cache service shut down")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to shut down API cache service: {str(e)}")
        return False