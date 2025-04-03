"""DexScreener service using TypeScript SDK with caching and specific pair tracking"""
import logging
import json
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
import subprocess
import os
from pathlib import Path
import time
import requests
import sys
from web3 import Web3
from datetime import datetime

# Handle both import styles (relative import from service module or direct import from test)
try:
    # When imported from within a module
    from ..constants.chain_config import SONIC_CHAIN_ID_STR
except (ImportError, ValueError):
    # When imported directly from file
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from src.constants.chain_config import SONIC_CHAIN_ID_STR

logger = logging.getLogger(__name__)

# Chain identifiers
SONIC = "sonic"
BASE = "base"
ETH = "ethereum"
CHAIN_IDS = [SONIC, BASE, ETH]

# Chain IDs
BASE_CHAIN_ID = "8453"  # Base chain ID in decimal format

# Specific Pair Addresses to track
SPECIFIC_PAIR_ADDRESSES = [
    "0xf316A1cB7376021ad52705c1403DF86C7A7A18d0",
    "0xe920d1DA9A4D59126dC35996Ea242d60EFca1304",
    "0xC046dCb16592FBb3F9fA0C629b8D93090dD4cB76",
    "0xf4F9C50455C698834Bb645089DbAa89093b93838",
    "0x690d956D97d3EEe18AB68ED1A28a89d531734F3d",
    "0x6fB9897896Fe5D05025Eb43306675727887D0B7c",
    "0x4EEC869d847A6d13b0F6D1733C5DEC0d1E741B4f",
    "0x79bbF4508B1391af3A0F4B30bb5FC4aa9ab0E07C",
    "0x71E99522EaD5E21CF57F1f542Dc4ad2E841F7321",
    "0x0e0Ce4D450c705F8a0B6Dd9d5123e3df2787D16B",
    "0xA04BC7140c26fc9BB1F36B1A604C7A5a88fb0E70",
    "0x59524D5667B299c0813Ba3c99a11C038a3908fBC",
    "0x3333b97138D4b086720b5aE8A7844b1345a33333"
]

# BeefyOracle contract details
BEEFY_ORACLE_ADDRESS = '0xBC4a342B0c057501E081484A2d24e576E854F823'
BEEFY_ORACLE_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "token", "type": "address"}],
        "name": "getPriceInUSD",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Initialize Web3 connection
web3_provider_url = "https://rpc.soniclabs.com"

class DexScreenerService:
    """Service for interacting with DexScreener API via TypeScript SDK"""
    def __init__(self, cache_duration: int = 120):  # 2 minutes default
        self._initialized = False
        self._ts_script_path = os.path.join(os.path.dirname(__file__), 'dexscreener.ts')
        self._cache = {}  # Store API responses
        self._last_update = 0  # Track last update time
        self.cache_duration = cache_duration
        self._update_running = False
        self._closing = False
        logger.info("DexScreener service initialized")
        logger.debug(f"TypeScript script path: {self._ts_script_path}")

    async def connect(self) -> bool:
        """Initialize service and verify SDK"""
        try:
            # Prevent recursive initialization
            if self._initialized:
                return True

            # Verify TypeScript script exists
            if not Path(self._ts_script_path).exists():
                logger.error(f"TypeScript script not found at {self._ts_script_path}")
                return False

            # Test SDK by making a direct call
            logger.info("Testing DexScreener SDK...")
            cmd = ['npx', 'tsx', self._ts_script_path, 'search_pairs', '--query', 'SONIC', '--chainId', 'sonic']

            try:
                async with asyncio.timeout(10):  # 10 second timeout
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()

                    # Log SDK output for debugging
                    if stderr:
                        error = stderr.decode()
                        logger.debug(f"SDK debug output: {error}")

                    if stdout:
                        output = stdout.decode()
                        try:
                            pairs = json.loads(output)
                            self._initialized = True
                            logger.info(f"✅ Successfully connected to DexScreener API, found {len(pairs)} pairs")
                            return True
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse SDK output: {e}")
                            return False
                    else:
                        logger.warning("No output from SDK test")
                        return False

            except asyncio.TimeoutError:
                logger.error("SDK initialization timed out")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize DexScreener service: {str(e)}")
            return False

    def _cache_data(self, key: str, data: Any) -> None:
        """Cache data with timestamp"""
        self._cache[key] = {
            'timestamp': time.time(),
            'data': data
        }
        self._last_update = time.time()

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached data if valid"""
        if key in self._cache:
            cache_entry = self._cache[key]
            if time.time() - cache_entry['timestamp'] < self.cache_duration:
                logger.debug(f"Using cached data for {key}")
                return cache_entry['data']
            else:
                logger.debug(f"Cache expired for {key}")
        return None

    async def search_pairs(self, query: str, chain_id: Optional[str] = SONIC_CHAIN_ID_STR, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Search for pairs using TypeScript SDK with caching"""
        try:
            if not self._initialized:
                logger.error("DexScreener service not initialized")
                return []

            # Generate cache key
            cache_key = f"pairs_{chain_id}_{query}"

            # Check cache first unless force refresh
            if not force_refresh:
                cached_data = self._get_cached(cache_key)
                if cached_data is not None:
                    logger.info(f"Using cached data for {query}")
                    return cached_data

            # If cache miss or force refresh, fetch new data
            cmd = [
                'npx', 'tsx', self._ts_script_path,
                'search_pairs',
                '--query', query.upper(),  # Use uppercase for consistency
                '--chainId', chain_id or SONIC
            ]
            logger.debug(f"Executing SDK command: {' '.join(cmd)}")

            try:
                async with asyncio.timeout(10):  # 10 second timeout
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()

                    # Log SDK output for debugging
                    if stderr:
                        sdk_logs = stderr.decode()
                        logger.debug(f"SDK debug output: {sdk_logs}")

                    if stdout:
                        output = stdout.decode()
                        try:
                            pairs = json.loads(output)
                            logger.info(f"Found {len(pairs)} pairs using SDK")

                            # Cache the results
                            self._cache_data(cache_key, pairs)
                            return pairs
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse SDK output: {e}")
                            return []
                    else:
                        logger.warning("No output from SDK")
                        return []

            except asyncio.TimeoutError:
                logger.error("SDK execution timed out")
                return []

        except Exception as e:
            logger.error(f"Error searching pairs: {str(e)}")
            return []

    async def get_pair_by_address(self, pair_address: str, chain_id: str = SONIC_CHAIN_ID_STR, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get a specific pair by its address using DexScreener API"""
        try:
            if not self._initialized:
                logger.error("DexScreener service not initialized")
                return None
                
            if not pair_address:
                logger.error("Missing pair address")
                return None
                
            # Check cache first unless force refresh
            cache_key = f"pair_{chain_id}_{pair_address.lower()}"
            if not force_refresh:
                cached_data = self._get_cached(cache_key)
                if cached_data is not None:
                    logger.info(f"Using cached data for pair {pair_address}")
                    return cached_data
                    
            # Make direct API request to DexScreener's pairs endpoint
            logger.info(f"Fetching pair data for {pair_address} on chain {chain_id}")
            
            async with aiohttp.ClientSession() as session:
                # Use DexScreener API directly
                url = f"https://api.dexscreener.com/latest/dex/pairs/{chain_id}/{pair_address}"
                logger.debug(f"API URL: {url}")
                
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"DexScreener API error: {response.status}")
                        return None
                        
                    data = await response.json()
                    
                    if not data or "pairs" not in data or not data["pairs"]:
                        logger.warning(f"No pair data found for {pair_address}")
                        return None
                        
                    # Get first pair (should only be one)
                    pair = data["pairs"][0]
                    
                    # Format the pair data to match our standard format
                    formatted_pair = {
                        "pair": f"{pair.get('baseToken', {}).get('symbol', '')}/{pair.get('quoteToken', {}).get('symbol', '')}",
                        "chain": pair.get("chainId", chain_id),
                        "chainId": pair.get("chainId", chain_id),
                        "baseToken": {
                            "symbol": pair.get("baseToken", {}).get("symbol", ""),
                            "address": pair.get("baseToken", {}).get("address", "")
                        },
                        "quoteToken": {
                            "symbol": pair.get("quoteToken", {}).get("symbol", ""),
                            "address": pair.get("quoteToken", {}).get("address", "")
                        },
                        "price": float(pair.get("priceNative", 0)),
                        "priceUsd": float(pair.get("priceUsd", 0)),
                        "priceChange24h": float(pair.get("priceChange", {}).get("h24", 0)),
                        "volume24h": float(pair.get("volume", {}).get("h24", 0)),
                        "liquidity": float(pair.get("liquidity", {}).get("usd", 0)),
                        "pairAddress": pair.get("pairAddress", ""),
                        "dexId": pair.get("dexId", "")
                    }
                    
                    # Cache the result
                    self._cache_data(cache_key, formatted_pair)
                    
                    logger.info(f"Successfully retrieved pair data for {pair_address}")
                    return formatted_pair
                    
        except Exception as e:
            logger.error(f"Error getting pair by address: {str(e)}")
            return None
    
    async def get_token_price(self, token_address: str, chain_id: str = SONIC_CHAIN_ID_STR, force_refresh: bool = False) -> float:
        """Get token price using TypeScript SDK with caching"""
        try:
            if not token_address or token_address == "0x0000000000000000000000000000000000000000":
                return 0.0

            # Check cache for price data
            cache_key = f"price_{chain_id}_{token_address}"
            if not force_refresh:
                cached_price = self._get_cached(cache_key)
                if cached_price is not None:
                    return cached_price

            pairs = await self.search_pairs(token_address, chain_id, force_refresh)
            if pairs:
                # Find pair with highest liquidity
                best_pair = max(pairs, key=lambda x: float(x.get('liquidity', 0) or 0))
                price = float(best_pair.get('priceUsd', 0))
                logger.info(f"Retrieved price from SDK: ${price:.8f}")

                # Cache the price
                self._cache_data(cache_key, price)
                return price

            logger.warning(f"No price data found for token {token_address}")
            return 0.0

        except Exception as e:
            logger.error(f"Error getting token price: {str(e)}")
            return 0.0
            
    async def get_pairs(self, token_symbol: str = 'SONIC', chain_id: str = SONIC_CHAIN_ID_STR) -> List[Dict[str, Any]]:
        """Get pairs for a token symbol - compatibility method for integrated bot"""
        try:
            if not token_symbol:
                logger.error("Token symbol is required")
                return []
                
            # Search for pairs with the token symbol
            pairs = await self.search_pairs(token_symbol, chain_id)
            
            # Filter for pairs on the specified chain
            if chain_id:
                pairs = [pair for pair in pairs if self.is_sonic_chain(pair.get('chain', ''))]
                
            logger.info(f"Found {len(pairs)} pairs for {token_symbol} on chain {chain_id}")
            return pairs
            
        except Exception as e:
            logger.error(f"Error getting pairs: {str(e)}")
            return []

    async def close(self) -> None:
        """Clean up resources"""
        self._initialized = False
        self._cache.clear()
        logger.info("✅ Successfully closed DexScreener service")
        
    # Alias methods to maintain compatibility with SonicConnection
    async def query_search_pairs(self, query: str, chain_id: Optional[str] = SONIC_CHAIN_ID_STR) -> List[Dict[str, Any]]:
        """Alias of search_pairs for SonicConnection compatibility"""
        return await self.search_pairs(query, chain_id)
        
    async def query_pair_data(self, chain_id: str, pair_address: str) -> Optional[Dict[str, Any]]:
        """Alias of get_pair_by_address for SonicConnection compatibility"""
        return await self.get_pair_by_address(pair_address, chain_id)

    def is_sonic_chain(self, chain_id: str) -> bool:
        """Validate if the chain ID matches Sonic chain"""
        if not chain_id:
            return False
        
        # Convert to string to handle both numeric and string IDs
        chain_id = str(chain_id).lower()
        
        # Check for both numeric (146) and string ("sonic") identifiers
        # Also check for previous incorrect ID (115) for backward compatibility
        return chain_id in [SONIC, "sonic", SONIC_CHAIN_ID_STR, "146"] or 'sonic' in chain_id

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the current cache state"""
        current_time = time.time()
        return {
            'last_update': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self._last_update)),
            'cache_duration': self.cache_duration,
            'entries': len(self._cache),
            'active_entries': sum(1 for entry in self._cache.values()
                                if current_time - entry['timestamp'] < self.cache_duration)
        }
    async def start_tophat_updates(self):
        """Start background TopHat price updates"""
        try:
            if not self._initialized:
                success = await self.connect()
                if not success:
                    logger.error("Failed to initialize DexScreener service")
                    return False

            self._update_running = True
            logger.info("Starting TopHat market data updates")

            # Monitor these tokens by default
            tokens_to_monitor = ["METRO", "ANON", "THC", "GOGLZ", "USDC"]

            while not self._closing:
                try:
                    update_start = time.time()
                    logger.info("Fetching TopHat market data...")

                    for token in tokens_to_monitor:
                        try:
                            pairs = await self.search_pairs(token, SONIC_CHAIN_ID_STR)
                            if pairs:
                                logger.info(f"Updated {len(pairs)} pairs for {token}")
                            else:
                                logger.warning(f"No pairs found for {token}")
                            await asyncio.sleep(1)  # Brief pause between tokens
                        except Exception as e:
                            logger.error(f"Error updating {token} pairs: {str(e)}")
                            continue

                    update_duration = time.time() - update_start
                    logger.info(f"TopHat update completed in {update_duration:.1f} seconds")

                    # Wait for next update cycle (2 hours)
                    two_hours_in_seconds = 7200  # 2 hours * 60 minutes * 60 seconds
                    logger.info(f"Waiting {two_hours_in_seconds/3600:.1f} hours until next TopHat knowledge update")
                    await asyncio.sleep(max(0, two_hours_in_seconds - update_duration))

                except Exception as e:
                    logger.error(f"Error in TopHat update cycle: {str(e)}")
                    await asyncio.sleep(60)  # Wait longer on error

            logger.info("TopHat updates stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to start TopHat updates: {str(e)}")
            return False

    async def stop_tophat_updates(self):
        """Stop background TopHat price updates"""
        self._closing = True
        self._update_running = False
        logger.info("Stopping TopHat updates...")
    
    async def fetch_token_price_from_oracle(self, token_address: str) -> Optional[float]:
        """Fetch token price from BeefyOracle contract"""
        try:
            web3 = Web3(Web3.HTTPProvider(web3_provider_url))
            oracle_contract = web3.eth.contract(
                address=Web3.to_checksum_address(BEEFY_ORACLE_ADDRESS),
                abi=BEEFY_ORACLE_ABI
            )
            price_wei = oracle_contract.functions.getPriceInUSD(
                Web3.to_checksum_address(token_address)
            ).call()
            price_usd = price_wei / 1e18
            logger.info(f"Price for token {token_address}: ${price_usd:.4f}")
            return price_usd
        except Exception as e:
            logger.error(f"Error fetching oracle price: {str(e)}")
            return None
    
    async def fetch_sonic_price(self) -> Optional[Dict[str, Any]]:
        """Fetch Sonic price from SonicScan API"""
        try:
            url = 'https://api.sonicscan.org/api?module=stats&action=ethprice&apikey=Q3UEUBJ5H26SM85B8VCAS28KPWBMS3AS6X'
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"SonicScan API error: {response.status}")
                        return None
                    
                    data = await response.json()
                    logger.info(f"Sonic price data fetched successfully")
                    return data
        except Exception as e:
            logger.error(f"Error fetching Sonic price data: {str(e)}")
            return None
    
    async def fetch_dexscreener_specific_pairs(self) -> Dict[str, Dict[str, Any]]:
        """Fetch data for specific DexScreener pairs"""
        specific_pairs_data = {}
        for address in SPECIFIC_PAIR_ADDRESSES:
            try:
                pair_data = await self.get_pair_by_address(address, SONIC, force_refresh=True)
                if pair_data:
                    specific_pairs_data[address] = pair_data
                await asyncio.sleep(0.5)  # Brief pause between requests to avoid rate limits
            except Exception as e:
                logger.error(f"Error fetching pair data for {address}: {str(e)}")
        
        logger.info(f"Fetched data for {len(specific_pairs_data)} specific pairs")
        return specific_pairs_data if specific_pairs_data else {}
    
    async def save_pair_data_to_database(self, pair_data: Dict[str, Any]) -> bool:
        """Save pair data to database"""
        try:
            import psycopg2
            import os
            import json
            from datetime import datetime
            
            # Database configuration
            db_url = os.environ.get('DATABASE_URL')
            if not db_url:
                logger.error("DATABASE_URL environment variable not found")
                return False
            
            # Format the data for our database schema
            pair_symbol = f"{pair_data.get('baseToken', {}).get('symbol', '')}/{pair_data.get('quoteToken', {}).get('symbol', '')}"
            base_token = pair_data.get('baseToken', {}).get('symbol', '')
            quote_token = pair_data.get('quoteToken', {}).get('symbol', '')
            
            # Create a database connection
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Format SQL query to insert data
            # Using jsonb_build_object for metadata to preserve proper JSON
            query = """
            INSERT INTO sonic_price_feed 
            (pair_address, pair_symbol, base_token, quote_token, price, price_usd, 
             price_change_24h, volume_24h, liquidity, chain, timestamp, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Extract values ensuring they are the correct types
            values = (
                pair_data.get('pairAddress', ''),
                pair_symbol,
                base_token,
                quote_token,
                float(pair_data.get('price', 0)),
                float(pair_data.get('priceUsd', 0)),
                float(pair_data.get('priceChange24h', 0)),
                float(pair_data.get('volume24h', 0)),
                float(pair_data.get('liquidity', 0)),
                pair_data.get('chain', 'sonic'),
                datetime.now(),
                json.dumps(pair_data)  # Convert to JSON string
            )
            
            # Execute the query
            cursor.execute(query, values)
            conn.commit()
            
            # Close the connection
            cursor.close()
            conn.close()
            
            logger.debug(f"Saved price feed for {pair_symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving pair data to database: {str(e)}")
            return False
    
    async def save_price_data_to_legacy_table(self, token: str, data: Dict[str, Any], source: str = 'dexscreener') -> bool:
        """Save price data to legacy price_feed_data table"""
        try:
            import psycopg2
            import os
            import json
            from datetime import datetime
            
            # Database configuration
            db_url = os.environ.get('DATABASE_URL')
            if not db_url:
                logger.error("DATABASE_URL environment variable not found")
                return False
            
            # Create a database connection
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Format SQL query to insert data
            query = """
            INSERT INTO price_feed_data 
            (symbol, price, source, chain_id, volume_24h, price_change_24h, timestamp, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Extract values ensuring they are the correct types
            values = (
                token,
                float(data.get('priceUsd', 0)),
                source,
                data.get('chain', 'sonic'),
                float(data.get('volume24h', 0)) if 'volume24h' in data else 0.0,
                float(data.get('priceChange24h', 0)) if 'priceChange24h' in data else 0.0,
                datetime.now(),
                json.dumps(data)  # Convert to JSON string
            )
            
            # Execute the query
            cursor.execute(query, values)
            conn.commit()
            
            # Close the connection
            cursor.close()
            conn.close()
            
            logger.debug(f"Stored price data for {token} from {source}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing price data: {str(e)}")
            return False
    
    async def log_market_update(self, update_type: str, status: str, details: Dict[str, Any] = None) -> bool:
        """Log market data update status"""
        try:
            import psycopg2
            import os
            import json
            from datetime import datetime
            
            # Database configuration
            db_url = os.environ.get('DATABASE_URL')
            if not db_url:
                logger.error("DATABASE_URL environment variable not found")
                return False
            
            # Create a database connection
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Format SQL query to insert data
            query = """
            INSERT INTO market_updates 
            (update_type, status, last_updated, details)
            VALUES (%s, %s, %s, %s)
            """
            
            # Extract values ensuring they are the correct types
            values = (
                update_type,
                status,
                datetime.now(),
                json.dumps(details or {})  # Convert to JSON string
            )
            
            # Execute the query
            cursor.execute(query, values)
            conn.commit()
            
            # Close the connection
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error logging market update: {str(e)}")
            return False
    
    async def fetch_pricing_data(self) -> Dict[str, Any]:
        """Main function to fetch all pricing data"""
        # Fetch Sonic price from SonicScan
        sonic_price = await self.fetch_sonic_price()
        
        # Fetch Wrapped Sonic price from BeefyOracle
        wrapped_sonic_address = "0x039e2fB66102314Ce7b64Ce5Ce3E5183bc94aD38"
        oracle_price = await self.fetch_token_price_from_oracle(wrapped_sonic_address)
        
        # Fetch DexScreener data for specific pairs
        dexscreener_data = await self.fetch_dexscreener_specific_pairs()
        
        return {
            'sonic_price': sonic_price,
            'oracle_price': oracle_price,
            'dexscreener_pairs': dexscreener_data
        }
    
    async def start_regular_price_updates(self, update_interval: int = 180):
        """Start background price updates at regular intervals (default: 3 minutes)"""
        try:
            if not self._initialized:
                success = await self.connect()
                if not success:
                    logger.error("Failed to initialize DexScreener service for price updates")
                    return False
            
            self._update_running = True
            logger.info(f"Starting regular price updates every {update_interval} seconds")
            
            while not self._closing:
                try:
                    update_start = time.time()
                    logger.info("Fetching comprehensive price data...")
                    
                    # Fetch all pricing data
                    pricing_data = await self.fetch_pricing_data()
                    
                    # Process Sonic price data from SonicScan
                    if pricing_data['sonic_price'] and pricing_data['sonic_price'].get('result', {}).get('ethusd'):
                        sonic_price_usd = float(pricing_data['sonic_price']['result']['ethusd'])
                        logger.info(f"Sonic Price (SonicScan): ${sonic_price_usd:.4f}")
                        
                        # Store in price_feed_data table
                        await self.save_price_data_to_legacy_table('SONIC', {
                            'priceUsd': sonic_price_usd,
                            'chain': 'sonic',
                            'source': 'sonicscan'
                        }, 'sonicscan')
                    
                    # Process oracle price for Wrapped Sonic
                    if pricing_data['oracle_price']:
                        logger.info(f"Wrapped Sonic Price (Oracle): ${pricing_data['oracle_price']:.4f}")
                        
                        # Store in price_feed_data table
                        await self.save_price_data_to_legacy_table('wSONIC', {
                            'priceUsd': pricing_data['oracle_price'],
                            'chain': 'sonic',
                            'source': 'beefy_oracle'
                        }, 'beefy_oracle')
                    
                    # Process DexScreener pair data
                    dexscreener_pairs = pricing_data.get('dexscreener_pairs', {})
                    
                    # Check if we got any specific pairs
                    if not dexscreener_pairs:
                        logger.info("No specific pairs found, using fallback search method for SONIC/USDC pairs")
                        
                        # Try direct search for Sonic/USDC pairs
                        sonic_usdc_pairs = await self.search_pairs("SONIC/USDC", SONIC_CHAIN_ID_STR, force_refresh=True)
                        
                        # Filter for Sonic chain only
                        sonic_usdc_pairs = [pair for pair in sonic_usdc_pairs if self.is_sonic_chain(pair.get('chain', ''))]
                        
                        if sonic_usdc_pairs:
                            logger.info(f"Found {len(sonic_usdc_pairs)} SONIC/USDC pairs")
                            # Convert to same format as specific pairs
                            dexscreener_pairs = {pair.get('pairAddress', f'fallback_{i}'): pair for i, pair in enumerate(sonic_usdc_pairs)}
                        else:
                            # If still no pairs, try with just "SONIC"
                            logger.info("No SONIC/USDC pairs found, searching for any SONIC pairs")
                            sonic_pairs = await self.search_pairs("SONIC", SONIC_CHAIN_ID_STR, force_refresh=True)
                            sonic_pairs = [pair for pair in sonic_pairs if self.is_sonic_chain(pair.get('chain', ''))]
                            
                            if sonic_pairs:
                                logger.info(f"Found {len(sonic_pairs)} SONIC pairs")
                                dexscreener_pairs = {pair.get('pairAddress', f'fallback_{i}'): pair for i, pair in enumerate(sonic_pairs)}
                    
                    if dexscreener_pairs:
                        logger.info(f"DexScreener Pairs Fetched: {len(dexscreener_pairs)}")
                        
                        # Save each pair to the database
                        for address, pair_data in dexscreener_pairs.items():
                            await self.save_pair_data_to_database(pair_data)
                            
                            # Also save to legacy table for compatibility
                            base_token = pair_data.get('baseToken', {}).get('symbol', '')
                            if base_token:
                                await self.save_price_data_to_legacy_table(base_token, pair_data)
                                
                                # Explicitly save SONIC token data for any pair that has SONIC as base or quote token
                                if base_token.upper() == 'SONIC' or base_token.upper() == 'WSONIC':
                                    logger.info(f"Saving special SONIC data from DexScreener pair with {base_token}")
                                    await self.save_price_data_to_legacy_table('SONIC', pair_data, 'dexscreener')
                    else:
                        logger.warning("No DexScreener pairs found for SONIC token")
                    
                    # Log the update
                    await self.log_market_update('dexscreener', 'success', {
                        'pairs_updated': len(dexscreener_pairs),
                        'sonic_price_updated': pricing_data['sonic_price'] is not None,
                        'oracle_price_updated': pricing_data['oracle_price'] is not None,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    update_duration = time.time() - update_start
                    logger.info(f"Price update completed in {update_duration:.1f} seconds")
                    
                    # Wait for next update cycle (minus time spent updating)
                    wait_time = max(0, update_interval - update_duration)
                    logger.info(f"Waiting {wait_time:.1f} seconds until next price update")
                    await asyncio.sleep(wait_time)
                    
                except Exception as e:
                    logger.error(f"Error in price update cycle: {str(e)}")
                    await self.log_market_update('dexscreener', 'failed', {
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
                    await asyncio.sleep(60)  # Wait longer on error
            
            logger.info("Regular price updates stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start regular price updates: {str(e)}")
            return False
    
    async def stop_price_updates(self):
        """Stop background price updates"""
        self._closing = True
        self._update_running = False
        logger.info("Stopping price updates...")


if __name__ == "__main__":
    async def example():
        service = None
        try:
            service = DexScreenerService()
            # Initialize first
            if await service.connect():
                print("\n=== Testing Basic Functionality ===")
                pairs = await service.search_pairs("Sonic")
                print(f"Initial fetch - Found {len(pairs)} pairs")
                
                # Test specific pair fetch
                pair_address = SPECIFIC_PAIR_ADDRESSES[0] if SPECIFIC_PAIR_ADDRESSES else "0xf316A1cB7376021ad52705c1403DF86C7A7A18d0"
                pair_data = await service.get_pair_by_address(pair_address)
                if pair_data:
                    print(f"\nPair: {pair_data.get('pair')}")
                    print(f"Price: ${pair_data.get('priceUsd')}")
                    print(f"Volume: ${pair_data.get('volume24h')}")
                    print(f"Liquidity: ${pair_data.get('liquidity')}")
                
                print("\n=== Testing New Price Updates ===")
                # Test Sonic price fetch
                sonic_price = await service.fetch_sonic_price()
                if sonic_price and sonic_price.get('result', {}).get('ethusd'):
                    print(f"Sonic Price (SonicScan): ${float(sonic_price['result']['ethusd']):.4f}")
                
                # Test oracle price fetch
                wrapped_sonic_address = "0x039e2fB66102314Ce7b64Ce5Ce3E5183bc94aD38"
                oracle_price = await service.fetch_token_price_from_oracle(wrapped_sonic_address)
                if oracle_price:
                    print(f"Wrapped Sonic Price (Oracle): ${oracle_price:.4f}")
                
                # Test specific pairs fetch
                print("\nFetching specific DexScreener pairs...")
                specific_pairs = await service.fetch_dexscreener_specific_pairs()
                print(f"Found {len(specific_pairs)} specific pairs")
                
                # Show a comprehensive pricing data fetch
                print("\n=== Testing Comprehensive Price Data Fetch ===")
                pricing_data = await service.fetch_pricing_data()
                print("Comprehensive price data fetched successfully")
                
                # For demonstration, let's run the regular updates once
                print("\n=== Testing Regular Price Updates ===")
                print("Starting regular price updates (will run one cycle only)...")
                
                # Start a task to run the updates
                update_task = asyncio.create_task(service.start_regular_price_updates(10))
                
                # Let it run for a few seconds
                await asyncio.sleep(15)
                
                # Stop the updates
                await service.stop_price_updates()
                
                # Wait for the task to complete
                await update_task
                
                print("\n✅ All tests completed successfully!")
                
            else:
                print("❌ Failed to initialize service")
        except Exception as e:
            logger.error(f"❌ Error: {str(e)}")
        finally:
            if service:
                await service.close()
                print("\nService closed")

    # Run the example
    asyncio.run(example())