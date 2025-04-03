"""CoinLayer API connection handler"""
import logging
import aiohttp
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

class CoinLayerConnection:
    """Connection handler for CoinLayer API"""
    def __init__(self, config: Dict[str, Any]):
        """Initialize CoinLayer connection

        Args:
            config: Configuration dictionary containing API settings
        """
        self.api_key = config.get('coinlayer_api_key')
        if not self.api_key:
            logger.error("CoinLayer API key not found in config")
            raise ValueError("CoinLayer API key is required")

        logger.info(f"Initializing CoinLayer connection (API key length: {len(self.api_key)})")
        self.base_url = "http://api.coinlayer.com"
        self._session: Optional[aiohttp.ClientSession] = None
        self.rate_limit = 100  # Free tier limit per month
        self._last_request = 0
        logger.info("Initialized CoinLayer connection")

    async def connect(self) -> bool:
        """Establish connection and verify API access"""
        try:
            self._session = aiohttp.ClientSession()
            # Test connection with a basic endpoint
            async with self._session.get(
                f"{self.base_url}/live",
                params={'access_key': self.api_key, 'symbols': 'Sonic'}
            ) as response:
                if response.status == 200:
                    logger.info("✅ Successfully connected to CoinLayer API")
                    return True
                else:
                    logger.error(f"Failed to connect to CoinLayer API: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Error connecting to CoinLayer: {str(e)}")
            return False

    async def get_live_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get live rate for a specific symbol

        Args:
            symbol: Cryptocurrency symbol (e.g., 'Sonic')

        Returns:
            Dictionary containing rate information or None on error
        """
        try:
            if not self._session:
                logger.error("No active session")
                return None

            # Basic rate limiting
            current_time = time.time()
            if current_time - self._last_request < 1:  # 1 second delay between requests
                await asyncio.sleep(1)
            self._last_request = current_time

            params = {
                'access_key': self.api_key,
                'symbols': symbol.upper(),
            }

            logger.debug(f"Making request to CoinLayer for symbol {symbol}")
            async with self._session.get(
                f"{self.base_url}/live",
                params=params
            ) as response:
                data = await response.json()
                if response.status == 200 and data.get('success', False):
                    return data
                else:
                    error_info = data.get('error', {}).get('info', 'Unknown error')
                    logger.error(f"CoinLayer API error: {response.status}, Info: {error_info}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching live rate: {str(e)}")
            return None

    async def get_historical_data(self, date: datetime, symbol: str = 'BTC') -> Optional[Dict[str, Any]]:
        """Get historical data for a specific date

        Args:
            date: Date to fetch historical data for
            symbol: Cryptocurrency symbol (default: 'BTC')

        Returns:
            Dictionary containing historical price data or None on error
        """
        try:
            if not self._session:
                logger.error("No active session")
                return None

            # Basic rate limiting
            current_time = time.time()
            if current_time - self._last_request < 1:  # 1 second delay between requests
                await asyncio.sleep(1)
            self._last_request = current_time

            date_str = date.strftime('%Y-%m-%d')
            url = f"{self.base_url}/{date_str}"

            params = {
                'access_key': self.api_key,
                'symbols': symbol
            }

            logger.info(f"Fetching historical data for {symbol} on {date_str}")
            async with self._session.get(url, params=params) as response:
                data = await response.json()
                if response.status == 200 and data.get('success', False):
                    return data
                else:
                    error_info = data.get('error', {}).get('info', 'Unknown error')
                    logger.error(f"CoinLayer API error: {response.status}, Info: {error_info}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching historical data: {str(e)}")
            return None

    async def get_last_6_months_data(self, symbol: str = 'BTC') -> Optional[Dict[str, Any]]:
        """Get historical data for the last 6 months

        Args:
            symbol: Cryptocurrency symbol (default: 'BTC')

        Returns:
            Dictionary containing historical price data or None on error
        """
        end_date = datetime.now() - timedelta(days=1)  # Start from yesterday
        start_date = end_date - timedelta(days=180)  # Last 6 months

        result = {
            'success': True,
            'rates': {}
        }

        current_date = end_date
        while current_date >= start_date:
            data = await self.get_historical_data(current_date, symbol)
            if data and data.get('success', False):
                result['rates'][current_date.strftime('%Y-%m-%d')] = data.get('rates', {})
                logger.info(f"Successfully fetched data for {current_date.strftime('%Y-%m-%d')}")
            else:
                logger.error(f"Failed to fetch data for {current_date.strftime('%Y-%m-%d')}")

            # Add delay between requests
            await asyncio.sleep(1.5)  # 1.5 seconds delay to stay well within rate limits
            current_date -= timedelta(days=1)  # Go backwards in time

        return result if result['rates'] else None

    async def close(self) -> None:
        """Close the connection and cleanup resources"""
        if self._session:
            await self._session.close()
            logger.info("Closed CoinLayer connection")