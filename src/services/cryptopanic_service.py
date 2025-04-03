import logging
import os
import time
from typing import Dict, Any, Optional
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class CryptoPanicService:
    """Service for fetching and analyzing crypto news from CryptoPanic"""

    def __init__(self):
        self.api_key = os.getenv("CRYPTOPANIC_API_KEY")
        self.base_url = "https://cryptopanic.com/api/v1/posts/"
        self._cache = {}
        self.cache_duration = 300  # 5 minutes cache
        self._request_timestamps = []
        self.rate_limit = 5  # Strict limit: 5 requests per second
        self.rate_window = 1  # 1 second window

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits (5 req/sec)"""
        current_time = time.time()

        # Remove timestamps older than our window
        self._request_timestamps = [ts for ts in self._request_timestamps 
                                   if current_time - ts < self.rate_window]

        if len(self._request_timestamps) >= self.rate_limit:
            logger.warning(f"Rate limit exceeded ({self.rate_limit} req/{self.rate_window}s)")
            # Add backoff delay if needed
            if len(self._request_timestamps) > 0:
                time_to_wait = self.rate_window - (current_time - min(self._request_timestamps))
                if time_to_wait > 0:
                    logger.info(f"Rate limit reached, waiting {time_to_wait:.2f}s")
                    time.sleep(time_to_wait)
            return False

        self._request_timestamps.append(current_time)
        return True

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached response if valid"""
        if key in self._cache:
            timestamp, data = self._cache[key]
            if time.time() - timestamp < self.cache_duration:
                return data
        return None

    def _cache_response(self, key: str, data: Any):
        """Cache API response"""
        self._cache[key] = (time.time(), data)

    async def get_latest_news(self, currencies: Optional[str] = None, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get latest news from CryptoPanic"""
        try:
            cache_key = f'latest_news_{currencies}' if currencies else 'latest_news'

            # Check cache first
            if not force_refresh:
                cached_data = self._get_cached(cache_key)
                if cached_data:
                    logger.debug("Returning cached news data")
                    return cached_data

            # Rate limiting check
            self._check_rate_limit()

            # Fetch fresh data with pro features
            params = {
                'auth_token': self.api_key,
                'metadata': 'true',  # Include PRO metadata
                'approved': 'true',
                'kind': 'news',
                'filter': 'hot',
                'limit': 10
            }
            if currencies:
                params['currencies'] = currencies

            logger.info(f"Fetching latest news from CryptoPanic for currencies: {currencies}")
            try:
                response = requests.get(
                    self.base_url,
                    params=params,
                    timeout=10,
                    verify=True,
                    headers={'Accept': 'application/json'}
                )
                response.raise_for_status()
                data = response.json()

                # Cache successful response
                self._cache_response(cache_key, data)
                return data

            except requests.exceptions.RequestException as e:
                logger.error(f"CryptoPanic API request failed: {str(e)}")
                return self._get_cached(cache_key) or self._get_fallback_news()

        except Exception as e:
            logger.error(f"Error in get_latest_news: {str(e)}")
            return self._get_fallback_news()

    # Other methods like get_trending_topics and get_market_sentiment remain unchanged