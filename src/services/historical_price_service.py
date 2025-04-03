"""Service for fetching and storing historical price data"""
import logging
import asyncpg
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

class HistoricalPriceService:
    """Service for managing historical price data"""

    def __init__(self):
        """Initialize the historical price service"""
        self.pool = None
        self._config = {}
        logger.info("Initialized HistoricalPriceService")

    async def connect(self) -> bool:
        """Connect to the database"""
        try:
            if not self.pool:
                database_url = os.getenv('DATABASE_URL')
                if not database_url:
                    logger.error("Database URL not found in environment")
                    return False

                self.pool = await asyncpg.create_pool(database_url)
                logger.info("Successfully connected to database")

            return True

        except Exception as e:
            logger.error(f"Error connecting to database: {str(e)}")
            return False

    async def close(self) -> None:
        """Close database connection"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Closed database connection")

    async def fetch_and_store_historical_prices(
        self,
        symbol: str,
        days: int = 7
    ) -> List[Tuple[datetime, float]]:
        """Fetch historical price data for given token

        Args:
            symbol: Token symbol (e.g. 'BTC')
            days: Number of days of history to fetch

        Returns:
            List of (datetime, price) tuples
        """
        try:
            if not self.pool:
                if not await self.connect():
                    return []

            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Fetch historical prices from database
            query = """
                SELECT timestamp, price::float
                FROM historical_prices
                WHERE symbol = $1
                  AND timestamp >= $2
                  AND timestamp <= $3
                ORDER BY timestamp DESC
            """

            async with self.pool.acquire() as conn:
                records = await conn.fetch(
                    query,
                    symbol.upper(),
                    start_date,
                    end_date
                )

            # Convert records to list of tuples
            return [(record['timestamp'], record['price']) for record in records]

        except Exception as e:
            logger.error(f"Error fetching historical prices: {str(e)}")
            return []