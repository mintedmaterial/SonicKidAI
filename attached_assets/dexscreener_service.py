import asyncio
import time
import logging
from typing import Dict, Any, Optional, List, TypedDict
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TokenInfo(TypedDict):
    address: str
    name: str
    symbol: str

class LiquidityInfo(TypedDict):
    usd: float
    base: float
    quote: float

class PairInfo(TypedDict):
    pairAddress: str
    chainId: str
    dexId: str
    baseToken: TokenInfo
    quoteToken: TokenInfo
    priceUsd: float
    volume24h: float
    liquidity: LiquidityInfo

class DexScreenerService:
    API_BASE_URL = "https://api.dexscreener.com"
    RATE_LIMIT_CALLS = 300  # Max calls per minute
    RATE_LIMIT_PERIOD = 60  # Period in seconds

    def __init__(self):
        self._cache: Dict[str, tuple[float, Any]] = {}
        self.cache_duration = 120  # 2 minute default cache
        self._retry_count = 3
        self._base_delay = 1  # Base delay for exponential backoff
        self._last_call_time = 0
        self._call_count = 0

    async def _make_request(self, endpoint: str, params: Optional[Dict] = None, retry_count: int = 0) -> Optional[Dict]:
        current_time = time.time()
        if current_time - self._last_call_time >= self.RATE_LIMIT_PERIOD:
            self._call_count = 0
            self._last_call_time = current_time

        if self._call_count >= self.RATE_LIMIT_CALLS:
            sleep_time = self.RATE_LIMIT_PERIOD - (current_time - self._last_call_time)
            if sleep_time > 0:
                logger.info(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
            self._call_count = 0
            self._last_call_time = time.time()

        self._call_count += 1

        try:
            url = f"{self.API_BASE_URL}{endpoint}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        if retry_count < self._retry_count:
                            delay = self._base_delay * (2 ** retry_count)
                            logger.warning(f"Rate limit hit, retrying in {delay} seconds...")
                            await asyncio.sleep(delay)
                            return await self._make_request(endpoint, params, retry_count + 1)
                        raise Exception("Rate limit exceeded after retries")
                    elif response.status == 404:
                        logger.debug(f"Resource not found: {url}")
                        return None
                    else:
                        logger.error(f"DexScreener API error: {response.status} - {await response.text()}")
                        return None

        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            if retry_count < self._retry_count:
                delay = self._base_delay * (2 ** retry_count)
                logger.warning(f"Request failed, retrying in {delay} seconds...")
                await asyncio.sleep(delay)
                return await self._make_request(endpoint, params, retry_count + 1)
            return None

    def _get_cached(self, key: str) -> Optional[Any]:
        if key in self._cache:
            timestamp, data = self._cache[key]
            if time.time() - timestamp < self.cache_duration:
                logger.debug(f"Cache hit for key: {key}")
                return data
        return None

    def _cache_response(self, key: str, data: Any):
        self._cache[key] = (time.time(), data)
        logger.debug(f"Cached response for key: {key}")

    def _format_pair_data(self, pair: Dict[str, Any]) -> PairInfo:
        return {
            'pairAddress': pair.get('pairAddress', ''),
            'chainId': pair.get('chainId', ''),
            'dexId': pair.get('dexId', ''),
            'baseToken': {
                'address': pair.get('baseToken', {}).get('address', ''),
                'name': pair.get('baseToken', {}).get('name', ''),
                'symbol': pair.get('baseToken', {}).get('symbol', '')
            },
            'quoteToken': {
                'address': pair.get('quoteToken', {}).get('address', ''),
                'name': pair.get('quoteToken', {}).get('name', ''),
                'symbol': pair.get('quoteToken', {}).get('symbol', '')
            },
            'priceUsd': float(pair.get('priceUsd', 0)),
            'volume24h': float(pair.get('volume', {}).get('h24', 0)),
            'liquidity': {
                'usd': float(pair.get('liquidity', {}).get('usd', 0)),
                'base': float(pair.get('liquidity', {}).get('base', 0)),
                'quote': float(pair.get('liquidity', {}).get('quote', 0))
            }
        }

    async def search_pairs(self, query: str) -> List[PairInfo]:
        cache_key = f"search_{query}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        data = await self._make_request("/latest/dex/search", params={"q": query})
        if data and isinstance(data.get('pairs'), list):
            pairs = [self._format_pair_data(pair) for pair in data['pairs']]
            self._cache_response(cache_key, pairs)
            return pairs
        return []

    async def get_token_profiles(self):
        cache_key = "token_profiles"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        data = await self._make_request("/token-profiles/latest/v1")
        if data:
            self._cache_response(cache_key, data)
            return data
        return None

    async def get_token_boosts(self):
        cache_key = "token_boosts"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        data = await self._make_request("/token-boosts/latest/v1")
        if data:
            self._cache_response(cache_key, data)
            return data
        return None

ALLOWED_CHAINS = {
    '146': 'Sonic',
    '1': 'Ethereum',
    '42161': 'Arbitrum',
    '10': 'Optimism'
}

async def main():
    service = DexScreenerService()

    # Search for pairs
    query = "Sonic/USDC"
    print(f"Searching for pairs matching: {query}")
    pairs = await service.search_pairs(query)
    filtered_pairs = [pair for pair in pairs if pair['chainId'] in ALLOWED_CHAINS]
    
    print(f"Found {len(filtered_pairs)} pairs in allowed chains")
    for pair in filtered_pairs:
        print("\nPair Details:")
        print(f"Chain: {ALLOWED_CHAINS[pair['chainId']]} (ID: {pair['chainId']})")
        print(f"DEX ID: {pair['dexId']}")
        print(f"Pair Address: {pair['pairAddress']}")
        print(f"Base Token: {pair['baseToken']['symbol']}")
        print(f"Quote Token: {pair['quoteToken']['symbol']}")
        print(f"Price USD: ${pair['priceUsd']}")
        print(f"Volume 24h: ${pair['volume24h']}")
        print(f"Liquidity USD: ${pair['liquidity']['usd']}")
        print("-" * 50)

    # Fetch token profiles
    print("\nFetching token profiles:")
    token_profiles = await service.get_token_profiles()
    if token_profiles:
        print(f"Received {len(token_profiles)} token profiles")
    else:
        print("No token profile data found")

    # Fetch token boosts
    print("\nFetching token boosts:")
    token_boosts = await service.get_token_boosts()
    if token_boosts:
        print(f"Received token boost data for {len(token_boosts)} tokens")
    else:
        print("No token boost data found")

if __name__ == "__main__":
    asyncio.run(main())