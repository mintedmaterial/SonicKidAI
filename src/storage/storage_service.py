"""Storage service implementation for market data"""
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import asyncpg
import os

logger = logging.getLogger(__name__)

class StorageService:
    """Service for storing and retrieving market data"""
    def __init__(self):
        self.pool = None
        self.database_url = os.getenv('DATABASE_URL')
        
    async def connect(self):
        """Initialize database connection pool"""
        if not self.pool:
            try:
                self.pool = await asyncpg.create_pool(self.database_url)
                logger.info("Database connection pool initialized")
                return True
            except Exception as e:
                logger.error(f"Failed to initialize database pool: {str(e)}")
                return False
        return True

    async def savePriceFeed(self, data: Dict[str, Any]) -> bool:
        """Save price feed data to database"""
        try:
            if not self.pool:
                await self.connect()
                
            query = """
            INSERT INTO sonic_price_feed 
            (pair_address, pair_symbol, base_token, quote_token, price, price_usd, 
             price_change_24h, volume_24h, liquidity, chain, metadata, timestamp)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """
            
            async with self.pool.acquire() as conn:
                await conn.execute(
                    query,
                    data['pairAddress'],
                    data['pairSymbol'],
                    data['baseToken'],
                    data['quoteToken'],
                    float(data['price']),
                    float(data['priceUsd']),
                    float(data.get('priceChange24h', 0)),
                    float(data.get('volume24h', 0)),
                    float(data.get('liquidity', 0)),
                    data['chain'],
                    json.dumps(data.get('metadata', {})),
                    datetime.now()
                )
                logger.debug(f"Saved price feed for {data['pairSymbol']}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving price feed: {str(e)}")
            return False

    async def getLatestPrices(self, chain: str) -> List[Dict[str, Any]]:
        """Get latest prices for specified chain"""
        try:
            if not self.pool:
                await self.connect()
                
            query = """
            SELECT DISTINCT ON (pair_symbol) 
                pair_address, pair_symbol, base_token, quote_token,
                price, price_usd, price_change_24h, volume_24h, liquidity,
                chain, metadata, timestamp
            FROM sonic_price_feed
            WHERE chain = $1
            ORDER BY pair_symbol, timestamp DESC
            LIMIT 10
            """
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, chain)
                return [
                    {
                        'pairAddress': row['pair_address'],
                        'pairSymbol': row['pair_symbol'],
                        'baseToken': row['base_token'],
                        'quoteToken': row['quote_token'],
                        'price': float(row['price']),
                        'priceUsd': float(row['price_usd']),
                        'priceChange24h': float(row['price_change_24h']),
                        'volume24h': float(row['volume_24h']),
                        'liquidity': float(row['liquidity']),
                        'chain': row['chain'],
                        'metadata': row['metadata'],
                        'timestamp': row['timestamp']
                    }
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Error getting latest prices: {str(e)}")
            return []

    async def logMarketUpdate(self, data: Dict[str, Any]) -> bool:
        """Log market data update status"""
        try:
            if not self.pool:
                await self.connect()
                
            query = """
            INSERT INTO market_updates
            (update_type, status, details, last_updated)
            VALUES ($1, $2, $3, $4)
            """
            
            async with self.pool.acquire() as conn:
                await conn.execute(
                    query,
                    data['updateType'],
                    data['status'],
                    json.dumps(data.get('details', {})),
                    datetime.now()
                )
                logger.debug(f"Logged market update: {data['updateType']}")
                return True
                
        except Exception as e:
            logger.error(f"Error logging market update: {str(e)}")
            return False
            
    async def getLatestTokenData(self, symbol: str, chain: str = 'sonic') -> Optional[Dict[str, Any]]:
        """Get latest token data for the specified symbol
        
        Args:
            symbol: Token symbol (e.g., 'SONIC', 'ETH')
            chain: Blockchain network (default: 'sonic')
            
        Returns:
            Token data including price, price change, and other metrics or None if not found
        """
        try:
            if not self.pool:
                await self.connect()
                
            logger.info(f"Fetching latest data for token: {symbol} on chain: {chain}")
            
            # Special case for SONIC token on Sonic chain
            if symbol.upper() == 'SONIC' and chain.lower() == 'sonic':
                logger.info("Using special SONIC token query")
                query = """
                SELECT 
                    price_usd as price, 
                    price_change_24h, 
                    volume_24h, 
                    liquidity,
                    base_token,
                    metadata,
                    timestamp
                FROM sonic_price_feed
                WHERE base_token = 'OS' OR base_token = 'SONIC'
                ORDER BY timestamp DESC
                LIMIT 1
                """
                
                async with self.pool.acquire() as conn:
                    row = await conn.fetchrow(query)
                    
                    if row:
                        # Get TVL data
                        tvl_query = """
                        SELECT details->>'tvl' as tvl
                        FROM market_updates
                        WHERE update_type = 'sonic_tvl' AND status = 'success'
                        ORDER BY last_updated DESC
                        LIMIT 1
                        """
                        tvl_row = await conn.fetchrow(tvl_query)
                        tvl = float(tvl_row['tvl']) if tvl_row and tvl_row['tvl'] else 0
                        
                        # Try to extract additional data from metadata JSON
                        metadata = row['metadata'] if row['metadata'] else {}
                        if isinstance(metadata, str):
                            try:
                                metadata = json.loads(metadata)
                            except:
                                metadata = {}
                                
                        # Extract market cap if available
                        market_cap = 0
                        if isinstance(metadata, dict):
                            if 'marketCap' in metadata:
                                market_cap = float(metadata['marketCap'])
                            elif 'fdv' in metadata:
                                market_cap = float(metadata['fdv'])
                        
                        return {
                            'symbol': 'SONIC',
                            'price': float(row['price']),
                            'price_change_24h': float(row['price_change_24h']),
                            'volume_24h': float(row['volume_24h']),
                            'liquidity': float(row['liquidity']),
                            'tvl': tvl,
                            'market_cap': market_cap,
                            'timestamp': row['timestamp'],
                            'source': 'database'
                        }
            
            # Generic token lookup by symbol
            query = """
            SELECT 
                pair_symbol,
                base_token,
                price_usd as price, 
                price_change_24h, 
                volume_24h, 
                liquidity,
                chain,
                metadata,
                timestamp
            FROM sonic_price_feed
            WHERE LOWER(base_token) = LOWER($1) AND LOWER(chain) = LOWER($2)
            ORDER BY timestamp DESC
            LIMIT 1
            """
            
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, symbol, chain)
                
                if row:
                    return {
                        'symbol': row['base_token'],
                        'price': float(row['price']),
                        'price_change_24h': float(row['price_change_24h']),
                        'volume_24h': float(row['volume_24h']),
                        'liquidity': float(row['liquidity']),
                        'pair': row['pair_symbol'],
                        'chain': row['chain'],
                        'timestamp': row['timestamp'],
                        'source': 'database'
                    }
                    
                return None
                
        except Exception as e:
            logger.error(f"Error getting latest token data for {symbol}: {str(e)}")
            return None
