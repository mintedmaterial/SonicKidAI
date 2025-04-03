"""DeFi Llama API connection for TVL and chain data"""
import logging
import json
import aiohttp
import time
from typing import Dict, Any, Optional, List, TypedDict, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class ChainTVL(TypedDict):
    """Chain TVL data structure"""
    chainId: str
    name: str
    tokenSymbol: Optional[str]
    tvl: float
    chainTvls: Dict[str, float]
    change_1d: float
    change_7d: float
    change_1m: float

class TokenPrice(TypedDict):
    """Token price data structure"""
    price: float
    timestamp: int
    confidence: float

class DefiLlamaConnection:
    """DeFi Llama API connection handler"""

    def __init__(self):
        """Initialize DeFi Llama connection"""
        self.base_url = "https://api.llama.fi"
        self.coins_url = "https://coins.llama.fi"
        self._session: Optional[aiohttp.ClientSession] = None

        # Cache settings
        self.cache: Dict[str, tuple[float, Any]] = {}
        self.cache_duration = 300  # 5 minutes
        logger.info("DeFi Llama connection initialized")

    async def connect(self):
        """Initialize aiohttp session"""
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()
            logger.info("DeFi Llama connection established")

    async def close(self):
        """Close aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            logger.info("DeFi Llama connection closed")

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached data if valid"""
        if key in self.cache:
            timestamp, data = self.cache[key]
            if time.time() - timestamp < self.cache_duration:
                return data
        return None

    def _cache_response(self, key: str, data: Any):
        """Cache API response"""
        self.cache[key] = (time.time(), data)

    async def _ensure_connection(self):
        """Ensure connection is active"""
        if not self._session or self._session.closed:
            await self.connect()

    async def get_token_price(self, chain: str, token_address: str, search_width: str = "4h") -> Optional[TokenPrice]:
        """Get current token price from DeFi Llama Coins API"""
        try:
            cache_key = f"price_{chain}_{token_address}"
            if cached := self._get_cached(cache_key):
                logger.debug(f"Using cached price for {token_address}")
                return cached

            await self._ensure_connection()

            # Format: chain:token_address
            token_id = f"{chain}:{token_address}"
            logger.debug(f"Fetching price for token ID: {token_id}")

            url = f"{self.coins_url}/prices/current/{token_id}"
            async with self._session.get(url, params={"searchWidth": search_width}) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Raw price response: {data}")

                    if not data or "coins" not in data:
                        logger.warning(f"No price data found for {token_id}")
                        return None

                    price_data = data["coins"].get(token_id)
                    if not price_data:
                        logger.warning(f"No price entry for {token_id}")
                        return None

                    token_price: TokenPrice = {
                        "price": float(price_data.get("price", 0)),
                        "timestamp": int(price_data.get("timestamp", 0)),
                        "confidence": float(price_data.get("confidence", 0))
                    }

                    self._cache_response(cache_key, token_price)
                    logger.info(f"Retrieved price for {token_id}: ${token_price['price']:.4f}")
                    return token_price

                logger.error(f"Error fetching price data: {response.status}")
                return None

        except Exception as e:
            logger.error(f"Error in get_token_price: {str(e)}")
            return None

    async def get_all_chains_tvl(self) -> Optional[List[ChainTVL]]:
        """Get TVL data for all chains"""
        try:
            cache_key = "all_chains_tvl"
            if cached := self._get_cached(cache_key):
                logger.debug("Using cached TVL data")
                return cached

            await self._ensure_connection()
            logger.debug("Fetching TVL data from DeFi Llama")

            async with self._session.get(f"{self.base_url}/v2/chains") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Raw TVL response received for {len(data)} chains")

                    # Format chain data
                    chains_data = []
                    for chain in data:
                        try:
                            chain_data: ChainTVL = {
                                'chainId': chain.get('chainId', ''),
                                'name': chain.get('name', ''),
                                'tokenSymbol': chain.get('tokenSymbol'),
                                'tvl': float(chain.get('tvl', 0)),
                                'chainTvls': chain.get('chainTvls', {}),
                                'change_1d': float(chain.get('change_1d', 0)),
                                'change_7d': float(chain.get('change_7d', 0)),
                                'change_1m': float(chain.get('change_1m', 0))
                            }
                            chains_data.append(chain_data)
                            logger.debug(f"Processed TVL data for {chain_data['name']}")
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Error processing chain data: {str(e)}")
                            continue

                    self._cache_response(cache_key, chains_data)
                    logger.info(f"Successfully retrieved TVL data for {len(chains_data)} chains")
                    return chains_data

                logger.error(f"Error fetching chain TVL: {response.status}")
                return None

        except Exception as e:
            logger.error(f"Error in get_all_chains_tvl: {str(e)}")
            return None

    async def get_sonic_tvl(self) -> Optional[ChainTVL]:
        """Get TVL data specifically for Sonic chain"""
        try:
            all_chains = await self.get_all_chains_tvl()
            if not all_chains:
                logger.warning("Failed to fetch chain TVL data")
                return None

            # Find Sonic chain data (checking for both "Sonic" and "Sonic-3")
            sonic_data = next(
                (chain for chain in all_chains 
                 if chain['name'].lower() in ['sonic', 'sonic-3']),
                None
            )

            if not sonic_data:
                logger.warning("Sonic chain data not found in TVL response")
                return None

            logger.info(f"Found Sonic TVL: ${sonic_data['tvl']:,.2f}")
            return sonic_data

        except Exception as e:
            logger.error(f"Error in get_sonic_tvl: {str(e)}")
            return None

    async def get_chain_comparison(self, chains: List[str]) -> Optional[Dict[str, ChainTVL]]:
        """Compare TVL and metrics across specified chains"""
        try:
            all_chains = await self.get_all_chains_tvl()
            if not all_chains:
                return None

            comparison = {}
            for chain_name in chains:
                chain_data = next(
                    (chain for chain in all_chains 
                     if chain['name'].lower() == chain_name.lower()),
                    None
                )
                if chain_data:
                    comparison[chain_name] = chain_data
                    logger.debug(f"Added {chain_name} to comparison data")

            return comparison if comparison else None

        except Exception as e:
            logger.error(f"Error in get_chain_comparison: {str(e)}")
            return None

    def format_tvl_response(self, tvl_data: ChainTVL) -> str:
        """Format TVL data for display"""
        try:
            return (
                f"📊 {tvl_data['name']} Chain Stats\n"
                f"💰 TVL: ${tvl_data['tvl']:,.2f}\n"
                f"📈 24h Change: {tvl_data['change_1d']:+.2f}%\n"
                f"📊 7d Change: {tvl_data['change_7d']:+.2f}%\n"
                f"📈 30d Change: {tvl_data['change_1m']:+.2f}%"
            )
        except Exception as e:
            logger.error(f"Error formatting TVL response: {str(e)}")
            return "Error formatting TVL data"

if __name__ == "__main__":
    async def test_defillama():
        """Test DeFi Llama connection"""
        connection = DefiLlamaConnection()
        await connection.connect()

        try:
            # Test TVL fetching
            tvl = await connection.get_sonic_tvl()
            print(f"Sonic TVL: {connection.format_tvl_response(tvl)}")

            # Test chain comparison
            comparison = await connection.get_chain_comparison(['Sonic', 'Ethereum', 'Arbitrum'])
            print(f"Chain comparison: {comparison}")

            # Test all chains TVL
            all_chains_tvl = await connection.get_all_chains_tvl()
            print(f"All chains TVL: {all_chains_tvl}")

            #Test token price
            price = await connection.get_token_price("ethereum", "0x7Fc66500c84A76Ad7e9c93437bFc5Ac35E9d0A11") #Test with a known token address
            print(f"Token price: {price}")

        finally:
            await connection.close()

    import asyncio
    asyncio.run(test_defillama())