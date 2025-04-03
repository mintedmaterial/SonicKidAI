"""PaintSwap API connection handler"""
import logging
import aiohttp
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class PaintSwapConnection:
    """Connection handler for PaintSwap API"""
    def __init__(self, config: Dict[str, Any]):
        """Initialize PaintSwap connection"""
        self.base_url = "https://api.paintswap.finance"  # Core API URL
        self._session: Optional[aiohttp.ClientSession] = None
        self.config = config
        self._retry_count = 3
        self._retry_delay = 1  # seconds
        self._rate_limit_delay = 0.5  # 500ms between requests
        self._last_request_time = 0
        self._headers = {
            'Accept': 'application/json',
            'User-Agent': 'SonicKid/1.0 (NFT Monitor)',
            'Content-Type': 'application/json',
            'X-Chain-ID': '250'  # Fantom chain ID
        }
        logger.info("Initialized PaintSwap connection")

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make API request with retries and rate limiting"""
        for attempt in range(self._retry_count):
            try:
                # Apply rate limiting
                now = datetime.now().timestamp()
                if self._last_request_time > 0:
                    time_since_last = now - self._last_request_time
                    if time_since_last < self._rate_limit_delay:
                        await asyncio.sleep(self._rate_limit_delay - time_since_last)

                if not self._session:
                    self._session = aiohttp.ClientSession()

                # Update request time
                self._last_request_time = datetime.now().timestamp()

                url = f"{self.base_url}/{endpoint.lstrip('/')}"
                logger.debug(f"Making request to: {url}")

                # Ensure headers are properly set
                if 'headers' not in kwargs:
                    kwargs['headers'] = {}
                kwargs['headers'].update(self._headers)

                # Encode parameters properly
                if 'params' in kwargs:
                    params = kwargs['params']
                    for key, value in params.items():
                        if isinstance(value, bool):
                            params[key] = str(value).lower()
                        elif isinstance(value, (int, float)):
                            params[key] = str(value)

                async with self._session.request(method, url, **kwargs) as response:
                    logger.debug(f"Response status: {response.status}")
                    logger.debug(f"Response headers: {dict(response.headers)}")

                    # Handle successful response
                    if response.status == 200:
                        try:
                            data = await response.json()
                            logger.debug(f"Successful response from {endpoint}")
                            return data
                        except Exception as e:
                            text = await response.text()
                            logger.error(f"Failed to parse JSON response: {text[:200]}")
                            logger.error(f"Parse error: {str(e)}")
                    else:
                        text = await response.text()
                        logger.error(f"Error response from {url}: {text[:200]}")
                        logger.error(f"Status code: {response.status}")

                        # Only retry on specific status codes
                        if response.status in [429, 500, 502, 503, 504]:
                            if attempt < self._retry_count - 1:
                                delay = self._retry_delay * (2 ** attempt)  # Exponential backoff
                                logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {delay}s...")
                                await asyncio.sleep(delay)
                                continue
                    return None

            except Exception as e:
                logger.error(f"Request error (attempt {attempt + 1}): {str(e)}")
                if attempt < self._retry_count - 1:
                    delay = self._retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                return None

        return None

    async def connect(self) -> bool:
        """Establish connection and verify API access"""
        try:
            # Test connection with sales endpoint
            result = await self._make_request('GET', 'v2/sales', params={'limit': '1'})
            if result is not None:
                logger.info("✅ Successfully connected to PaintSwap API")
                return True

            logger.error("❌ Failed to connect to PaintSwap API")
            return False

        except Exception as e:
            logger.error(f"Error connecting to PaintSwap: {str(e)}")
            if self._session:
                await self._session.close()
                self._session = None
            return False

    async def get_sales(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent sales data"""
        try:
            # Get recent sales with minimal params
            params = {
                'limit': str(limit)
            }

            result = await self._make_request('GET', 'v2/sales', params=params)
            if result and isinstance(result, dict):
                sales = result.get('sales', [])
                if sales:
                    sample = sales[0]
                    logger.debug(f"Sample sale: Collection: {sample.get('collection', {}).get('name')}, "
                               f"Price: {sample.get('priceUsd')}, Token: {sample.get('token', {}).get('symbol')}")
                logger.info(f"Retrieved {len(sales)} sales")
                return sales

            logger.warning("No sales data returned from API")
            return []

        except Exception as e:
            logger.error(f"Error fetching sales: {str(e)}")
            return []

    async def close(self):
        """Close service connections"""
        try:
            if self._session:
                await self._session.close()
                self._session = None
                logger.info("Closed PaintSwap connection")
        except Exception as e:
            logger.error(f"Error closing connection: {str(e)}")