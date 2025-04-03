"""
Cache Service for Dashboard API endpoints

This service provides a centralized caching mechanism for all dashboard endpoints,
with configurable refresh intervals for different content types to respect API rate limits
while keeping data fresh.
"""
import time
import logging
import asyncio
import json
from typing import Dict, Any, Optional, Callable, Awaitable, Tuple
from datetime import datetime, timedelta
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CacheItem:
    """Cache item with value and metadata"""
    def __init__(self, value: Any, refresh_interval: int = 60):
        self.value = value
        self.last_updated = time.time()
        self.refresh_interval = refresh_interval  # seconds
        self.is_updating = False
        self.update_lock = asyncio.Lock()
    
    def is_stale(self) -> bool:
        """Check if the cache item is stale and needs refreshing"""
        return time.time() - self.last_updated > self.refresh_interval
    
    def update(self, value: Any):
        """Update the cache value and timestamp"""
        self.value = value
        self.last_updated = time.time()
    
    def time_since_update(self) -> float:
        """Get seconds since last update"""
        return time.time() - self.last_updated
    
    def time_until_refresh(self) -> float:
        """Get seconds until next refresh is due"""
        return max(0, self.refresh_interval - self.time_since_update())

class DashboardCacheService:
    """
    Service for caching dashboard API responses with different refresh intervals
    to balance freshness with rate limit compliance.
    """
    # Default refresh intervals in seconds for different content types
    DEFAULT_REFRESH_INTERVALS = {
        "price": 60,             # Price data - refresh every minute
        "sonic-price": 20,       # Sonic price data - refresh every 20 seconds (3x per minute)
        "sentiment": 120,        # Sentiment data - refresh every 2 minutes
        "news": 300,             # News data - refresh every 5 minutes
        "fear-greed": 1800,      # Fear & Greed index - refresh every 30 minutes
        "trending": 600,         # Trending tokens - refresh every 10 minutes
        "dex-volume": 300,       # DEX volume data - refresh every 5 minutes
        "sonic-pairs": 120,      # Sonic pairs data - refresh every 2 minutes
        "sales": 600,            # Sales data - refresh every 10 minutes
        "default": 300,          # Default for unlisted data types - 5 minutes
    }
    
    def __init__(self, custom_intervals: Optional[Dict[str, int]] = None):
        """
        Initialize the cache service with optional custom refresh intervals
        
        Args:
            custom_intervals: Optional dictionary mapping data types to refresh intervals in seconds
        """
        self._cache: Dict[str, CacheItem] = {}
        self._refresh_intervals = self.DEFAULT_REFRESH_INTERVALS.copy()
        if custom_intervals:
            self._refresh_intervals.update(custom_intervals)
        
        # Refresh callbacks - mapping of cache_key to refresh function
        self._refresh_callbacks: Dict[str, Callable[[], Awaitable[Any]]] = {}
        
        # Background refresh task
        self._stop_event = threading.Event()
        self._refresh_task = None
        self._stats: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Dashboard cache service initialized with refresh intervals:")
        for data_type, interval in self._refresh_intervals.items():
            logger.info(f"  - {data_type}: {interval}s")
    
    def get_refresh_interval(self, data_type: str) -> int:
        """Get the refresh interval for a specific data type"""
        return self._refresh_intervals.get(data_type, self._refresh_intervals["default"])
    
    def set_refresh_interval(self, data_type: str, interval: int):
        """Set a custom refresh interval for a data type"""
        self._refresh_intervals[data_type] = interval
        logger.info(f"Set refresh interval for {data_type} to {interval}s")
        
        # Update existing cache item if it exists
        for key, item in self._cache.items():
            if key.startswith(f"{data_type}:") or key == data_type:
                item.refresh_interval = interval
    
    async def get(self, 
                 cache_key: str, 
                 data_type: str, 
                 refresh_callback: Optional[Callable[[], Awaitable[Any]]] = None) -> Tuple[Any, bool]:
        """
        Get a value from cache, refreshing if stale
        
        Args:
            cache_key: Unique cache key
            data_type: Type of data (price, news, etc.)
            refresh_callback: Optional async function to refresh data if stale
        
        Returns:
            Tuple of (cached_value, is_fresh)
            - cached_value: The cached value (or None if not in cache)
            - is_fresh: True if data was fresh or just refreshed, False if stale and no refresh was possible
        """
        full_key = f"{data_type}:{cache_key}"
        is_fresh = True
        
        # Store refresh callback for background updates
        if refresh_callback:
            self._refresh_callbacks[full_key] = refresh_callback
        
        # Get from cache or create new entry
        if full_key not in self._cache:
            if refresh_callback:
                # Create new entry with the specified refresh interval
                refresh_interval = self.get_refresh_interval(data_type)
                logger.info(f"Cache miss for {full_key}. Creating new entry with {refresh_interval}s refresh.")
                
                try:
                    # Initial fetch
                    cache_item = CacheItem(None, refresh_interval)
                    self._cache[full_key] = cache_item
                    
                    # Run initial update under the lock
                    async with cache_item.update_lock:
                        cache_item.is_updating = True
                        start_time = time.time()
                        value = await refresh_callback()
                        elapsed = time.time() - start_time
                        
                        # Update cache with fresh value
                        cache_item.update(value)
                        cache_item.is_updating = False
                        
                        # Update stats
                        self._update_stats(full_key, True, elapsed)
                        
                        logger.info(f"Initial fetch for {full_key} completed in {elapsed:.2f}s")
                        return value, True
                except Exception as e:
                    logger.error(f"Error in initial fetch for {full_key}: {str(e)}")
                    # Remove the entry so we can try again later
                    if full_key in self._cache:
                        del self._cache[full_key]
                    return None, False
            else:
                # No callback provided and item not in cache
                return None, False
        
        # Get the cached item
        cache_item = self._cache[full_key]
        
        # Check if we need to refresh
        if cache_item.is_stale() and refresh_callback:
            # Only refresh if not already being updated
            if not cache_item.is_updating:
                try:
                    # Update asynchronously without blocking if lock is taken
                    if cache_item.update_lock.locked():
                        logger.debug(f"Update for {full_key} already in progress, using existing value")
                    else:
                        # Try to acquire lock for update, but don't block if can't get it
                        if await asyncio.wait_for(asyncio.shield(
                            cache_item.update_lock.acquire()
                        ), timeout=0.1):
                            try:
                                cache_item.is_updating = True
                                # Schedule the refresh without awaiting it
                                asyncio.create_task(self._refresh_cache_item(full_key, cache_item, refresh_callback))
                            except Exception as e:
                                logger.error(f"Error scheduling refresh for {full_key}: {str(e)}")
                                cache_item.is_updating = False
                                cache_item.update_lock.release()
                except asyncio.TimeoutError:
                    # Couldn't get lock quickly, so just use cached value
                    pass
                except Exception as e:
                    logger.error(f"Unexpected error checking lock for {full_key}: {str(e)}")
            
            # Mark as slightly stale if we didn't just update it
            is_fresh = not cache_item.is_stale()
        
        # Return current value (either fresh or slightly stale)
        return cache_item.value, is_fresh
    
    async def _refresh_cache_item(self, 
                                full_key: str, 
                                cache_item: CacheItem, 
                                refresh_callback: Callable[[], Awaitable[Any]]):
        """Refresh a single cache item using its callback"""
        start_time = time.time()  # Initialize start_time at the beginning
        try:
            value = await refresh_callback()
            elapsed = time.time() - start_time
            
            # Update the cache
            cache_item.update(value)
            
            # Update stats
            self._update_stats(full_key, True, elapsed)
            
            logger.debug(f"Refreshed {full_key} in {elapsed:.2f}s")
        except Exception as e:
            logger.error(f"Error refreshing {full_key}: {str(e)}")
            elapsed = time.time() - start_time
            self._update_stats(full_key, False, elapsed)
        finally:
            cache_item.is_updating = False
            cache_item.update_lock.release()
    
    def _update_stats(self, key: str, success: bool, elapsed: float):
        """Update statistics for a cache item"""
        if key not in self._stats:
            self._stats[key] = {
                "updates": 0,
                "failures": 0,
                "last_update": None,
                "avg_time": 0,
            }
        
        stats = self._stats[key]
        stats["updates"] += 1
        if not success:
            stats["failures"] += 1
        
        # Update average time with exponential moving average (EMA)
        if stats["updates"] == 1:
            stats["avg_time"] = elapsed
        else:
            # Use a weight of 0.3 for the new value
            stats["avg_time"] = (0.3 * elapsed) + (0.7 * stats["avg_time"])
        
        stats["last_update"] = datetime.now().isoformat()
    
    async def set(self, cache_key: str, data_type: str, value: Any) -> None:
        """
        Manually set a cache value
        
        Args:
            cache_key: Unique cache key
            data_type: Type of data (price, news, etc.)
            value: Value to cache
        """
        full_key = f"{data_type}:{cache_key}"
        refresh_interval = self.get_refresh_interval(data_type)
        
        if full_key in self._cache:
            self._cache[full_key].update(value)
        else:
            self._cache[full_key] = CacheItem(value, refresh_interval)
    
    async def invalidate(self, cache_key: str, data_type: str) -> None:
        """
        Invalidate a cache entry, forcing refresh on next access
        
        Args:
            cache_key: Unique cache key
            data_type: Type of data (price, news, etc.)
        """
        full_key = f"{data_type}:{cache_key}"
        if full_key in self._cache:
            # Set last_updated to 0 to force refresh
            self._cache[full_key].last_updated = 0
            logger.info(f"Invalidated cache for {full_key}")
    
    async def clear(self, data_type: Optional[str] = None) -> None:
        """
        Clear cache entries
        
        Args:
            data_type: Optional data type to clear (if None, clears all)
        """
        if data_type:
            # Clear specific data type
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{data_type}:")]
            for key in keys_to_remove:
                del self._cache[key]
            logger.info(f"Cleared {len(keys_to_remove)} cache entries for {data_type}")
        else:
            # Clear all
            self._cache.clear()
            logger.info("Cleared all cache entries")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        result = {
            "items": len(self._cache),
            "refresh_intervals": self._refresh_intervals,
            "details": {}
        }
        
        # Add details for each cache item
        for key, item in self._cache.items():
            data_type = key.split(":", 1)[0] if ":" in key else "unknown"
            cache_key = key.split(":", 1)[1] if ":" in key else key
            
            result["details"][key] = {
                "last_updated": datetime.fromtimestamp(item.last_updated).isoformat(),
                "refresh_interval": item.refresh_interval,
                "is_stale": item.is_stale(),
                "is_updating": item.is_updating,
                "time_since_update": item.time_since_update(),
                "time_until_refresh": item.time_until_refresh(),
                "data_type": data_type,
                "cache_key": cache_key,
            }
            
            # Add stats if available
            if key in self._stats:
                result["details"][key].update(self._stats[key])
        
        return result
    
    async def start_background_refresh(self):
        """Start background refresh task"""
        if self._refresh_task is not None:
            logger.warning("Background refresh already running")
            return
        
        self._stop_event.clear()
        self._refresh_task = asyncio.create_task(self._background_refresh_loop())
        logger.info("Started background refresh task")
    
    async def stop_background_refresh(self):
        """Stop background refresh task"""
        if self._refresh_task is None:
            logger.warning("No background refresh task running")
            return
        
        self._stop_event.set()
        try:
            await asyncio.wait_for(self._refresh_task, timeout=5.0)
            logger.info("Background refresh task stopped")
        except asyncio.TimeoutError:
            logger.warning("Background refresh task did not stop gracefully, cancelling")
            self._refresh_task.cancel()
        
        self._refresh_task = None
    
    async def _background_refresh_loop(self):
        """Background loop to refresh cache items before they go stale"""
        try:
            logger.info("Background refresh loop started")
            while not self._stop_event.is_set():
                # Find items that are due for refresh soon (within 10% of their refresh interval)
                now = time.time()
                items_to_refresh = []
                
                for key, item in self._cache.items():
                    # Skip items that are already being updated
                    if item.is_updating:
                        continue
                    
                    # Check if item is due for refresh soon
                    time_since_update = now - item.last_updated
                    refresh_soon_threshold = item.refresh_interval * 0.9
                    
                    if time_since_update >= refresh_soon_threshold:
                        items_to_refresh.append((key, item))
                
                # Refresh items that are due
                for key, item in items_to_refresh:
                    if key in self._refresh_callbacks:
                        # Only refresh if lock can be acquired immediately
                        if not item.update_lock.locked():
                            try:
                                await item.update_lock.acquire()
                                item.is_updating = True
                                # Schedule the refresh without awaiting it
                                asyncio.create_task(
                                    self._refresh_cache_item(key, item, self._refresh_callbacks[key])
                                )
                                logger.debug(f"Scheduled background refresh for {key}")
                            except Exception as e:
                                logger.error(f"Error scheduling background refresh for {key}: {str(e)}")
                                item.is_updating = False
                                item.update_lock.release()
                
                # Sleep for a short time before checking again
                await asyncio.sleep(1.0)
                
        except asyncio.CancelledError:
            logger.info("Background refresh loop cancelled")
        except Exception as e:
            logger.error(f"Error in background refresh loop: {str(e)}")

# Global instance for use throughout the application
cache_service = DashboardCacheService()