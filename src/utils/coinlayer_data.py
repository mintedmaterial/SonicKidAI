"""
Utility module for fetching cryptocurrency data from coinlayer API with rate limiting
"""
import logging
import requests
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CoinlayerAPI:
    """
    CoinlayerAPI client with rate limiting to stay within free tier limits
    Free tier: 100 requests per month
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = 'http://api.coinlayer.com'
        self.monthly_limit = 100  # Free tier limit
        self.requests_made = 0
        self.last_reset = datetime.now()
        self.last_request = 0
        self.min_interval = 5  # Minimum 5 seconds between requests

    def _check_rate_limit(self) -> bool:
        """Check if we can make another request"""
        current_time = time.time()

        # Reset counter on new month
        current_month = datetime.now().month
        if current_month != self.last_reset.month:
            self.requests_made = 0
            self.last_reset = datetime.now()

        # Check monthly limit
        if self.requests_made >= self.monthly_limit:
            logger.warning("Monthly API request limit reached")
            return False

        # Ensure minimum interval between requests
        if current_time - self.last_request < self.min_interval:
            time_to_wait = self.min_interval - (current_time - self.last_request)
            logger.debug(f"Rate limiting: waiting {time_to_wait:.2f}s for next request window")
            time.sleep(time_to_wait)

        return True

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make a rate-limited API request"""
        if not self._check_rate_limit():
            logger.warning("Rate limit exceeded, skipping request")
            return None

        try:
            params = params or {}
            params['access_key'] = self.api_key

            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if not data:
                    logger.error("Empty response from API")
                    return None

                # Update rate limit tracking
                self.requests_made += 1
                self.last_request = time.time()

                if 'success' in data:
                    if not data['success']:
                        error_info = data.get('error', {}).get('info', 'Unknown error')
                        logger.error(f"API error: {error_info}")
                        return None

                if 'rates' not in data and endpoint != 'live':
                    logger.error("No rates data in response")
                    return None

                return data

            logger.error(f"HTTP error {response.status_code}: {response.text}")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error making coinlayer request: {str(e)}")
            return None

    def get_live_rates(self, symbols: Optional[str] = None) -> Optional[Dict]:
        """Get live cryptocurrency rates"""
        params = {}
        if symbols:
            params['symbols'] = symbols.upper()
            params['target'] = 'USD'  # Always get USD prices

        return self._make_request('live', params)

    def get_historical_timeframe(
        self, 
        start_date: str, 
        end_date: str, 
        symbols: Optional[str] = None,
        max_points: int = 12
    ) -> List[Dict]:
        """
        Get historical rates for a timeframe with appropriate intervals
        Parameters:
        - start_date: Start date in YYYY-MM-DD format
        - end_date: End date in YYYY-MM-DD format
        - symbols: Comma-separated list of cryptocurrency symbols
        - max_points: Maximum number of data points to return
        Returns list of {date, rates} dictionaries
        """
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            date_range = (end - start).days

            if date_range <= 0:
                logger.error("End date must be after start date")
                return []

            # Calculate appropriate interval
            if date_range <= 7:  # 1 week or less
                interval = timedelta(days=1)  # Daily data for a week
                points = min(max_points, date_range)
            else:
                interval = timedelta(days=max(1, date_range // max_points))
                points = min(max_points, date_range // interval.days)

            # Check if we have enough API requests available
            points = min(points, self.monthly_limit - self.requests_made)
            if points <= 0:
                logger.warning("Not enough API requests remaining for historical data")
                return []

            historical_data = []
            current_date = start

            while current_date <= end and len(historical_data) < points:
                date_str = current_date.strftime('%Y-%m-%d')
                params = {
                    'symbols': symbols.upper() if symbols else None,
                    'target': 'USD'
                }

                # Make the API request for this date
                data = self._make_request(date_str, params)
                if data and 'rates' in data:
                    historical_data.append({
                        'date': date_str,
                        'rates': data['rates']
                    })

                current_date += interval

            return historical_data

        except ValueError as e:
            logger.error(f"Date format error: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error fetching historical timeframe: {str(e)}")
            return []

    def format_timeframe_message(self, 
        historical_data: List[Dict], 
        symbols: Optional[str] = None
    ) -> str:
        """Format timeframe rates data into a concise message"""
        try:
            if not historical_data:
                return "Unable to fetch historical cryptocurrency rates"

            # Format the message
            message = f"📈 Historical {symbols if symbols else 'Crypto'} Rates:\n"

            # Add each timepoint (limited to keep response concise)
            for point in historical_data[:12]:  # Limit to 12 points max
                rates = point['rates']
                if symbols and symbols in rates:
                    message += f"{point['date']}: ${format_number(rates[symbols])}\n"
                elif not symbols:
                    # Show top 3 coins by value if no specific symbol requested
                    top_coins = sorted(rates.items(), key=lambda x: x[1], reverse=True)[:3]
                    coins_str = ", ".join(f"{symbol}: ${format_number(rate)}" 
                                        for symbol, rate in top_coins)
                    message += f"{point['date']}: {coins_str}\n"

            return message.strip()

        except Exception as e:
            logger.error(f"Error formatting timeframe message: {str(e)}")
            return "Error formatting historical rates data"

    def format_rates_message(self, rates_data: Dict, is_historical: bool = False) -> str:
        """Format rates data into a concise message"""
        try:
            if not rates_data or 'rates' not in rates_data:
                return "Unable to fetch cryptocurrency rates"

            # Format header based on query type
            if is_historical:
                header = f"💰 {rates_data.get('date', 'Historical')} Rates"
            else:
                header = "💰 Current Rates"

            # Format only the requested or top currencies
            message = f"{header} (USD):\n"
            rates = rates_data['rates']

            # Sort by value and take top 5
            top_rates = sorted(rates.items(), key=lambda x: x[1], reverse=True)[:5]
            for symbol, rate in top_rates:
                message += f"{symbol}: ${format_number(rate)}\n"

            return message.strip()

        except Exception as e:
            logger.error(f"Error formatting rates message: {str(e)}")
            return "Error formatting cryptocurrency rates"

def format_number(num: float) -> str:
    """Format number with commas and appropriate precision"""
    try:
        if num >= 1_000_000:
            return f"{num/1_000_000:.2f}M"
        elif num >= 1_000:
            return f"{num/1_000:.2f}K"
        return f"{num:.2f}"
    except:
        return str(num)