"""DeFi Llama service for fetching price and TVL data"""
import logging
import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from src.server.db import db
except ImportError:
    # For tests when running directly
    from server.db import db

logger = logging.getLogger(__name__)

class DeFiLlamaService:
    """Service to fetch and store data from DeFiLlama API"""

    DEFILLAMA_API = "https://api.llama.fi"
    COINS_API = "https://coins.llama.fi"
    DEFAULT_TIMEOUT = 10

    def __init__(self):
        """Initialize service"""
        self.session = None
        self._timeout = aiohttp.ClientTimeout(total=self.DEFAULT_TIMEOUT)
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize service and create session if needed"""
        try:
            if not self._initialized or not self.session or self.session.closed:
                self.session = aiohttp.ClientSession(timeout=self._timeout)
                self._initialized = True
                logger.info("DeFiLlama service initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize DeFiLlama service: {str(e)}")
            return False

    async def close(self):
        """Close service connections"""
        if self.session and not self.session.closed:
            try:
                await self.session.close()
                self._initialized = False
                logger.info("DeFiLlama service session closed")
            except Exception as e:
                logger.error(f"Error closing DeFiLlama session: {str(e)}")

    async def _store_price_data(self, token_address: str, data: Dict[str, Any]):
        """Store price data in database"""
        try:
            # Convert metadata dict to JSON string
            metadata_json = json.dumps(data)

            query = """
                INSERT INTO price_feed_data (symbol, price, source, volume_24h, price_change_24h, timestamp, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """
            await db.execute(
                query,
                token_address,
                float(data.get('price', 0)),
                'defillama',
                float(data.get('volume24h', 0)),
                float(data.get('change_24h', 0)),
                datetime.now(),
                metadata_json  # Store as JSON string
            )
            logger.info(f"Stored DeFiLlama data for {token_address}")
        except Exception as e:
            logger.error(f"Error storing DeFiLlama data: {str(e)}")

    async def get_token_data(self, token_address: str) -> Dict[str, Any]:
        """Fetch token price and TVL data"""
        try:
            # Ensure session is initialized
            if not await self.initialize():
                raise Exception("Failed to initialize DeFiLlama service")

            # Format coin ID for DeFiLlama API
            coin_id = f"coingecko:{token_address}"  # Default to coingecko format
            if ':' not in token_address:  # If no prefix provided
                if token_address.lower() in ['btc', 'bitcoin']:
                    coin_id = "coingecko:bitcoin"
                elif token_address.lower() in ['eth', 'ethereum']:
                    coin_id = "coingecko:ethereum"
                elif token_address.lower() in ['sonic']:
                    coin_id = "sonic:0x039e2fB66102314Ce7b64Ce5ce3E5183bc94aD38"

            # First try coins API for current price
            price_data = {}
            price_url = f"{self.COINS_API}/prices/current/{coin_id}"
            logger.info(f"Fetching price data from: {price_url}")
            try:
                async with self.session.get(price_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and "coins" in data:
                            price_data = data["coins"].get(coin_id, {})
                            logger.info(f"Received price data: {json.dumps(price_data)}")
                    else:
                        logger.warning(f"DeFiLlama price API error: Status {response.status}")
                        error_text = await response.text()
                        logger.warning(f"Error response: {error_text}")
            except Exception as e:
                logger.error(f"Error fetching price data: {str(e)}")

            # Fetch TVL and volume data
            tvl_data = {}
            try:
                if token_address.lower() in ['sonic']:
                    # For Sonic, fetch DEX volume data
                    dex_url = f"{self.DEFILLAMA_API}/overview/dexs/Sonic?excludeTotalDataChart=false&excludeTotalDataChartBreakdown=false&dataType=dailyVolume"
                    logger.info(f"Fetching Sonic DEX data from: {dex_url}")
                    async with self.session.get(dex_url) as response:
                        if response.status == 200:
                            dex_data = await response.json()
                            tvl_data = {
                                'total24h': dex_data.get('total24h', 0),
                                'change_1d': dex_data.get('change_1d', 0),
                                'change_7d': dex_data.get('change_7d', 0),
                                'change_1m': dex_data.get('change_1m', 0),
                                'totalVolume': dex_data.get('totalVolume', 0),
                            }
                            logger.info(f"Received Sonic DEX data: {json.dumps(tvl_data)}")
                        else:
                            logger.warning(f"DeFiLlama DEX API error: Status {response.status}")
                            error_text = await response.text()
                            logger.warning(f"Error response: {error_text}")

                elif token_address.lower() in ['btc', 'bitcoin', 'eth', 'ethereum']:
                    # For major chains, use chain data
                    chain_name = 'Bitcoin' if token_address.lower() in ['btc', 'bitcoin'] else 'Ethereum'

                    # Get chain volume
                    volume_url = f"{self.DEFILLAMA_API}/summary/chains/{chain_name}?dataType=dailyVolume"
                    logger.info(f"Fetching chain volume from: {volume_url}")
                    async with self.session.get(volume_url) as response:
                        if response.status == 200:
                            volume_data = await response.json()
                            tvl_data['volume24h'] = volume_data.get('total24h', 0)
                            tvl_data['change_24h'] = volume_data.get('change_1d', 0)
                            logger.info(f"Received chain volume data: {json.dumps(volume_data)}")
                        else:
                            logger.warning(f"DeFiLlama volume API error: Status {response.status}")
                            error_text = await response.text()
                            logger.warning(f"Error response: {error_text}")

                    # Get chain TVL
                    tvl_url = f"{self.DEFILLAMA_API}/v2/chains/{chain_name}"
                    logger.info(f"Fetching chain TVL from: {tvl_url}")
                    async with self.session.get(tvl_url) as response:
                        if response.status == 200:
                            chain_data = await response.json()
                            tvl_data['totalLiquidityUSD'] = chain_data[0].get('tvl', 0) if chain_data else 0
                            logger.info(f"Received chain TVL data: {json.dumps(chain_data)}")
                        else:
                            logger.warning(f"DeFiLlama TVL API error: Status {response.status}")
                            error_text = await response.text()
                            logger.warning(f"Error response: {error_text}")
                else:
                    # For other tokens, try protocol endpoint
                    protocol_url = f"{self.DEFILLAMA_API}/protocol/{coin_id}"
                    logger.info(f"Fetching protocol data from: {protocol_url}")
                    async with self.session.get(protocol_url) as response:
                        if response.status == 200:
                            tvl_data = await response.json()
                            logger.info(f"Received protocol data: {json.dumps(tvl_data)}")
                        else:
                            logger.warning(f"DeFiLlama protocol API error: Status {response.status}")
                            error_text = await response.text()
                            logger.warning(f"Error response: {error_text}")

            except Exception as e:
                logger.error(f"Error fetching TVL data: {str(e)}")

            # Combine data
            result = {
                'price': float(price_data.get('price', 0)),
                'confidence': float(price_data.get('confidence', 0)),
                'timestamp': price_data.get('timestamp', datetime.now().timestamp()),
                'volume24h': float(tvl_data.get('total24h', tvl_data.get('volume24h', 0))),
                'change_24h': float(tvl_data.get('change_1d', tvl_data.get('change_24h', 0))),
                'totalLiquidity': float(tvl_data.get('totalLiquidityUSD', tvl_data.get('totalVolume', 0))),
                'source': 'defillama'
            }

            # Store in database if we have valid price data
            if result['price'] > 0:
                await self._store_price_data(token_address, result)

            logger.info(f"Final combined data for {token_address}: {json.dumps(result)}")
            return result

        except Exception as e:
            logger.error(f"Error fetching DeFiLlama data: {str(e)}")
            return {
                'price': 0.0,
                'totalLiquidity': 0.0,
                'volume24h': 0.0,
                'change_24h': 0.0,
                'timestamp': datetime.now().timestamp(),
                'source': 'defillama_error'
            }