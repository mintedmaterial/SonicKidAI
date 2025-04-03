import asyncio
import logging
import aiohttp
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
import websockets
import ssl
import urllib.parse
import struct

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedMarketDataService:
    def __init__(self):
        self.session = None
        self.cache = {}
        self.last_update = {}
        self.update_interval = 3600  # 1 hour in seconds
        self.pair_cache: Dict[str, Dict[str, Any]] = {}
        self.price_cache: Dict[str, Dict[str, Any]] = {}

        # Load environment variables
        load_dotenv()
        self.dune_api_key = os.getenv('DUNE_API_KEY')
        self.sonic_labs_api_key = os.getenv('SONIC_LABS_API_KEY', 'default_key')
        self.alchemy_api_key = os.getenv('ALCHEMY_API_KEY', 'default_key')
        self.db_url = os.getenv('DATABASE_URL')

        # Initialize database
        self._init_db()

        # Chain mappings
        self.chain_mappings = {
            'S': {'id': '146', 'name': 'Sonic'},
            'eth': {'id': '1', 'name': 'Ethereum'},
            'arb': {'id': '42161', 'name': 'Arbitrum'},
            'op': {'id': '10', 'name': 'Optimism'}
        }

    def _init_db(self):
        """Initialize database tables"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    # Create tables for token pairs and price history
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS token_pairs (
                            id SERIAL PRIMARY KEY,
                            pair_address TEXT UNIQUE NOT NULL,
                            base_token_address TEXT NOT NULL,
                            quote_token_address TEXT NOT NULL,
                            base_token_symbol TEXT,
                            quote_token_symbol TEXT,
                            dex_id TEXT,
                            chain_id TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS price_history (
                            id SERIAL PRIMARY KEY,
                            pair_id INTEGER REFERENCES token_pairs(id),
                            price_usd NUMERIC,
                            volume_24h NUMERIC,
                            liquidity_usd NUMERIC,
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(pair_id, timestamp)
                        )
                    """)
                    conn.commit()
                    logger.info("Database tables initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise

    async def initialize(self):
        """Initialize the service and start background updates"""
        self.session = aiohttp.ClientSession()
        # Start background update task
        asyncio.create_task(self._periodic_update())
        # Start DexScreener WebSocket connection
        asyncio.create_task(self._dexscreener_websocket())
        logger.info("Enhanced Market Data Service initialized")

    async def close(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()

    async def _periodic_update(self):
        """Periodically update market data"""
        while True:
            try:
                await self._update_all_data()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in periodic update: {str(e)}")
                await asyncio.sleep(60)  # Wait before retry

    async def _update_all_data(self):
        """Update data from all sources"""
        try:
            defi_data = await self.get_defi_data()
            self.cache['defillama'] = defi_data 
            self.last_update['defillama'] = datetime.now()

            sonic_price = await self._fetch_sonic_price()
            self.cache['sonic_price'] = sonic_price
            self.last_update['sonic_price'] = datetime.now()

            eq_stats = await self._fetch_equalizer_stats()
            self.cache['equalizer'] = eq_stats
            self.last_update['equalizer'] = datetime.now()

            eq_pairs = await self._fetch_equalizer_pairs()
            self.cache['equalizer_pairs'] = eq_pairs
            self.last_update['equalizer_pairs'] = datetime.now()

            token_data = await self._fetch_alchemy_token_data()
            self.cache['alchemy_tokens'] = token_data
            self.last_update['alchemy_tokens'] = datetime.now()

            await self._aggregate_prices()

            logger.info("Successfully updated all market data")
        except Exception as e:
            logger.error(f"Error updating market data: {str(e)}")

    async def _dexscreener_websocket(self):
        """Establish and maintain WebSocket connection to DexScreener"""
        base_uri = "wss://io.dexscreener.com/dex/screener/v4/pairs/h24/1"
        params = {
            "rankBy[key]": "trendingScoreH6",
            "rankBy[order]": "desc",
            "filters[chainIds][0]": "Sonic"
        }
        uri = f"{base_uri}?{urllib.parse.urlencode(params)}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-WebSocket-Version': '13',
            'Origin': 'https://dexscreener.com',
            'Connection': 'Upgrade',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'Upgrade': 'websocket',
        }

        ssl_context = ssl.create_default_context()

        while True:
            try:
                async with websockets.connect(uri, extra_headers=headers, ssl=ssl_context, max_size=None) as websocket:
                    while True:
                        try:
                            message = await websocket.recv()
                            if message == "ping":
                                await websocket.send("pong")
                                continue
                            if isinstance(message, bytes):
                                pairs = self._process_dexscreener_message(message)
                                if pairs:
                                    await self._update_pair_data(pairs)
                        except websockets.exceptions.ConnectionClosed:
                            break
                        except Exception as e:
                            logger.error(f"Error processing DexScreener message: {str(e)}")
            except Exception as e:
                logger.error(f"DexScreener WebSocket connection error: {str(e)}")
                await asyncio.sleep(5)  # Wait before reconnecting

    def _process_dexscreener_message(self, message: bytes) -> List[Dict[str, Any]]:
        """Process binary message from DexScreener WebSocket"""
        if not message.startswith(b'\x00\n1.3.0\n'):
            return []

        pairs_start = message.find(b'pairs')
        if pairs_start == -1:
            return []

        pairs = []
        pos = pairs_start + 5
        while pos < len(message):
            pair = self._decode_pair(message[pos:pos+512])
            if pair:
                pairs.append(pair)
            pos += 512

        return pairs

    def _decode_pair(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Decode a single trading pair from binary data"""
        # Implementation of decode_pair function goes here
        # This should be adapted from the second script's decode_pair function
        pass

    async def _update_pair_data(self, pairs: List[Dict[str, Any]]):
        """Update pair data in the database"""
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    # Update token_pairs table
                    pair_data = [
                        (
                            pair['pairAddress'],
                            pair['baseTokenAddress'],
                            pair.get('quoteTokenAddress', ''),
                            pair['baseTokenSymbol'],
                            pair.get('quoteTokenSymbol', ''),
                            pair.get('protocol', ''),
                            pair['chain']
                        )
                        for pair in pairs
                    ]
                    execute_values(
                        cur,
                        """
                        INSERT INTO token_pairs 
                        (pair_address, base_token_address, quote_token_address, 
                         base_token_symbol, quote_token_symbol, dex_id, chain_id)
                        VALUES %s
                        ON CONFLICT (pair_address) DO UPDATE SET
                            base_token_symbol = EXCLUDED.base_token_symbol,
                            quote_token_symbol = EXCLUDED.quote_token_symbol
                        RETURNING id, pair_address
                        """,
                        pair_data
                    )

                    # Get pair IDs for price history
                    cur.execute("SELECT id, pair_address FROM token_pairs")
                    pair_id_map = {row[1]: row[0] for row in cur.fetchall()}

                    # Update price_history table
                    price_data = [
                        (
                            pair_id_map[pair['pairAddress']],
                            float(pair['priceUsd']),
                            float(pair['volume']['h24']),
                            float(pair['liquidity']['usd']),
                            datetime.now()
                        )
                        for pair in pairs
                        if pair['pairAddress'] in pair_id_map
                    ]
                    execute_values(
                        cur,
                        """
                        INSERT INTO price_history 
                        (pair_id, price_usd, volume_24h, liquidity_usd, timestamp)
                        VALUES %s
                        ON CONFLICT (pair_id, timestamp) DO UPDATE SET
                            price_usd = EXCLUDED.price_usd,
                            volume_24h = EXCLUDED.volume_24h,
                            liquidity_usd = EXCLUDED.liquidity_usd
                        """,
                        price_data
                    )

                    conn.commit()
                    logger.info(f"Updated {len(pairs)} pairs in the database")
        except Exception as e:
            logger.error(f"Error updating pair data: {str(e)}")

    # Implement other methods (e.g., _fetch_defillama_data, _fetch_sonic_price, etc.) here

    async def get_token_data(self, token_address: str, chain_id: str = "sonic") -> Optional[Dict[str, Any]]:
        """Get comprehensive token data including price and market metrics"""
        try:
            cache_key = f"token_{chain_id}_{token_address}"
            cached = self._get_cached_data(cache_key)
            if cached:
                return cached

            # Fetch the latest data from the database
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT tp.*, ph.price_usd, ph.volume_24h, ph.liquidity_usd, ph.timestamp
                        FROM token_pairs tp
                        JOIN price_history ph ON tp.id = ph.pair_id
                        WHERE tp.base_token_address = %s AND tp.chain_id = %s
                        ORDER BY ph.timestamp DESC
                        LIMIT 1
                    """, (token_address, chain_id))
                    result = cur.fetchone()

                    if result:
                        token_data = {
                            'address': token_address,
                            'chain_id': chain_id,
                            'pair_address': result[1],
                            'base_token_symbol': result[4],
                            'quote_token_symbol': result[5],
                            'dex_id': result[6],
                            'price': result[8],
                            'volume_24h': result[9],
                            'liquidity': result[10],
                            'updated_at': result[11].isoformat()
                        }
                        self._cache_data(cache_key, token_data)
                        return token_data

            return None
        except Exception as e:
            logger.error(f"Error fetching token data: {str(e)}")
            return None

    def _get_cached_data(self, key: str) -> Optional[Dict]:
        """Get cached data if valid"""
        if key in self.cache:
            timestamp, data = self.cache[key]
            if (datetime.now() - timestamp).total_seconds() < self.update_interval:
                return data
        return None

    def _cache_data(self, key: str, data: Any):
        """Cache data with timestamp"""
        self.cache[key] = (datetime.now(), data)

# Example usage
async def main():
    service = EnhancedMarketDataService()
    await service.initialize()
    
    # Example: Get token data
    token_data = await service.get_token_data("0x123456789abcdef", "sonic")
    print(json.dumps(token_data, indent=2))

    await service.close()

if __name__ == "__main__":
    asyncio.run(main())