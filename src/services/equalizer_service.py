"""Equalizer API Service"""
import logging
import time
from typing import Dict, Any, Optional
import requests
from .abstract_service import AbstractService

logger = logging.getLogger(__name__)

class EqualizerService(AbstractService):
    """Service for Equalizer API interactions"""

    def __init__(self):
        super().__init__()
        # Use working Equalizer API endpoint
        self.API_BASE_URL = "https://eqapi-sonic-prod-ltanm.ondigitalocean.app/sonic"
        self._cache: Dict[str, tuple[float, Any]] = {}
        self.cache_duration = 60  # 1 minute default cache

    async def fetch_global_stats(self) -> Optional[Dict]:
        """Fetch global statistics from Equalizer API"""
        try:
            current_time = time.time()
            cache_key = 'global_stats'

            # Check cache first
            if cache_key in self._cache:
                timestamp, data = self._cache[cache_key]
                if current_time - timestamp < self.cache_duration:
                    return data

            response = requests.get(f"{self.API_BASE_URL}/stats/equalizer", timeout=10)
            response.raise_for_status()
            data = response.json()

            # Cache the results
            self._cache[cache_key] = (current_time, data)
            return data

        except Exception as e:
            self.log_error(e, "Failed to fetch Equalizer global stats")
            return None

    async def fetch_pair_data(self, pair_address: str) -> Optional[Dict]:
        """Fetch specific pair data"""
        try:
            current_time = time.time()
            cache_key = f'pair_{pair_address}'

            if cache_key in self._cache:
                timestamp, data = self._cache[cache_key]
                if current_time - timestamp < self.cache_duration:
                    return data

            response = requests.get(
                f"{self.API_BASE_URL}/v4/pairs/{pair_address}",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            self._cache[cache_key] = (current_time, data)
            return data

        except Exception as e:
            self.log_error(e, "Failed to fetch pair data")
            return None

    async def fetch_trades(self, address: str, limit: int = 100) -> Optional[Dict]:
        """Fetch recent trades for an address"""
        try:
            current_time = time.time()
            cache_key = f'trades_{address}_{limit}'

            if cache_key in self._cache:
                timestamp, data = self._cache[cache_key]
                if current_time - timestamp < self.cache_duration:
                    return data

            # Use the stats endpoint for trades since v4/trades is not available
            response = requests.get(
                f"{self.API_BASE_URL}/stats/equalizer",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            # Filter trades from the stats data if available
            if 'trades' in data:
                trades = data['trades']
                if address:
                    trades = [t for t in trades if t.get('address', '').lower() == address.lower()]
                trades = trades[:limit]  # Limit the number of trades
                return {'trades': trades}
            return {'trades': []}

        except Exception as e:
            self.log_error(e, "Failed to fetch trades")
            return None

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