"""Database connection and storage module for Python services"""
import os
import logging
import asyncpg
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class Storage:
    """Storage class for database operations"""
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
        self._database_url = os.environ.get('DATABASE_URL')
        if not self._database_url:
            raise ValueError("DATABASE_URL environment variable is required")

    async def connect(self) -> None:
        """Initialize database connection pool"""
        try:
            self._pool = await asyncpg.create_pool(self._database_url)
            logger.info("✅ Successfully connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            raise

    async def close(self) -> None:
        """Close database connection pool"""
        if self._pool:
            await self._pool.close()
            logger.info("Closed PostgreSQL connection pool")

    async def create_historical_price(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new historical price record

        Args:
            data: Dictionary containing price data
                Required keys: symbol, price, timestamp, source

        Returns:
            Created price record
        """
        if not self._pool:
            raise RuntimeError("Database connection not initialized")

        query = """
            INSERT INTO historical_prices (symbol, price, timestamp, source)
            VALUES ($1, $2, $3, $4)
            RETURNING *
        """
        try:
            async with self._pool.acquire() as conn:
                record = await conn.fetchrow(
                    query,
                    data['symbol'],
                    data['price'],
                    data['timestamp'],
                    data['source']
                )
                return dict(record)
        except Exception as e:
            logger.error(f"Error creating historical price: {str(e)}")
            raise

    async def get_historical_prices(
        self,
        symbol: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get historical prices for a symbol

        Args:
            symbol: Cryptocurrency symbol
            limit: Maximum number of records to return

        Returns:
            List of historical price records
        """
        if not self._pool:
            raise RuntimeError("Database connection not initialized")

        query = """
            SELECT * FROM historical_prices
            WHERE symbol = $1
            ORDER BY timestamp DESC
            LIMIT $2
        """
        try:
            async with self._pool.acquire() as conn:
                records = await conn.fetch(query, symbol, limit)
                return [dict(record) for record in records]
        except Exception as e:
            logger.error(f"Error fetching historical prices: {str(e)}")
            raise

storage = Storage()
