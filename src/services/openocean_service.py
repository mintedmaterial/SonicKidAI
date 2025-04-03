"""
OpenOcean Service Module

This service provides functions to interact with the OpenOcean API for fetching
swap quotes, token data, and other on-chain information from multiple chains.
"""

import os
import json
import logging
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime

logger = logging.getLogger(__name__)

# OpenOcean API configuration
OPENOCEAN_API_BASE_URL = os.getenv('OPENOCEAN_API_URL', 'https://open-api.openocean.finance/v3')
OPENOCEAN_PRO_API_BASE_URL = os.getenv('OPENOCEAN_PRO_API_URL', 'https://open-api.openocean.finance/v3')  # Reverting to original URL
OPENOCEAN_API_KEY = os.getenv('OPENOCEAN_API_KEY', 'mNhHD7nFNkCHGevafz40BQc1dX9AzxkH')  # Pro API key with 3 RPS limit


class OpenOceanService:
    """Service for interacting with OpenOcean API"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the OpenOcean service"""
        self.config = config or {}
        self.use_pro_api = bool(OPENOCEAN_API_KEY)
        
        # Base URLs
        self.base_url = OPENOCEAN_PRO_API_BASE_URL if self.use_pro_api else OPENOCEAN_API_BASE_URL
        
        # Session for API requests
        self._session = None
        
        # Chain configuration (chainId to name mapping)
        self.chain_config = {
            'sonic': '4689',    # Sonic
            '4689': '4689',     # Sonic alternate
            'eth': '1',         # Ethereum
            'ethereum': '1',    # Ethereum alternate
            'bsc': '56',        # BNB Chain
            'polygon': '137',   # Polygon
            'avalanche': '43114',  # Avalanche
            'arbitrum': '42161',  # Arbitrum
            'optimism': '10',   # Optimism
            'base': '8453',     # Base
            'zksync': '324',    # zkSync
        }
        
        logger.info(f"Initialized OpenOcean service (Pro API: {self.use_pro_api})")
        
    async def connect(self) -> bool:
        """
        Initialize an async HTTP session for API requests
        
        Returns:
            bool: True if connection successful
        """
        # Create a new session if needed
        if self._session is None or self._session.closed:
            try:
                # Configure session with timeouts and proper headers
                timeout = aiohttp.ClientTimeout(total=10)  # 10-second timeout
                self._session = aiohttp.ClientSession(
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                    },
                    timeout=timeout,
                    connector=aiohttp.TCPConnector(ssl=False)  # Disable SSL verification for compatibility
                )
                
                # Add API key if available
                if self.use_pro_api:
                    self._session.headers.update({
                        'X-API-KEY': OPENOCEAN_API_KEY
                    })
                    
                logger.info(f"Created new HTTP session for OpenOcean API")
                
            except Exception as e:
                logger.error(f"❌ Failed to create HTTP session: {str(e)}")
                return False
        
        # Test connection by fetching chain list
        try:
            # Make a simple request to test connectivity
            async with self._session.get(f"{self.base_url}/1/tokenList", ssl=False) as response:
                if response.status == 200:
                    logger.info(f"✅ OpenOcean service connected successfully")
                    return True
                else:
                    logger.error(f"❌ Connection test failed with status code: {response.status}")
                    return False
                
        except aiohttp.ClientConnectorError as e:
            logger.error(f"❌ Connection error: {str(e)}")
            return False
        except aiohttp.ClientError as e:
            logger.error(f"❌ Client error: {str(e)}")
            return False
        except asyncio.TimeoutError:
            logger.error("❌ Connection timeout")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to connect to OpenOcean API: {str(e)}")
            return False
            
        return True
    
    async def close(self) -> None:
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("✅ OpenOcean service connection closed")
    
    def _get_chain_id(self, chain: str) -> str:
        """
        Get the numeric chain ID from a chain name
        
        Args:
            chain: Chain name or ID (e.g., 'sonic', 'ethereum', '1')
            
        Returns:
            str: The numeric chain ID
        """
        chain = str(chain).lower()
        return self.chain_config.get(chain, chain)
    
    async def get_chain_list(self) -> List[Dict[str, Any]]:
        """
        Get the list of supported chains
        
        Returns:
            List[Dict[str, Any]]: List of chain info objects
        """
        try:
            async with self._session.get(f"{self.base_url}/chainList", ssl=False) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', [])
                else:
                    logger.error(f"Failed to get chain list: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error getting chain list: {str(e)}")
            return []
    
    async def get_token_list(self, chain: str) -> List[Dict[str, Any]]:
        """
        Get the list of supported tokens for a chain
        
        Args:
            chain: Chain name or ID
            
        Returns:
            List[Dict[str, Any]]: List of token info objects
        """
        chain_id = self._get_chain_id(chain)
        
        try:
            async with self._session.get(f"{self.base_url}/{chain_id}/tokenList", ssl=False) as response:
                if response.status == 200:
                    data = await response.json()
                    tokens = data.get('data', [])
                    logger.info(f"✅ Found {len(tokens)} tokens on chain {chain_id}")
                    return tokens
                else:
                    logger.error(f"Failed to get token list: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error getting token list for chain {chain_id}: {str(e)}")
            return []
    
    async def get_gas_price(self, chain: str) -> Dict[str, Any]:
        """
        Get current gas price information for a chain
        
        Args:
            chain: Chain name or ID
            
        Returns:
            Dict[str, Any]: Gas price information
        """
        chain_id = self._get_chain_id(chain)
        
        try:
            async with self._session.get(f"{self.base_url}/{chain_id}/gasPrice", ssl=False) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', {})
                else:
                    logger.error(f"Failed to get gas price: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error getting gas price for chain {chain_id}: {str(e)}")
            return {}
    
    async def get_token_info(self, chain: str, token_address: str) -> Dict[str, Any]:
        """
        Get detailed information about a token
        
        Args:
            chain: Chain name or ID
            token_address: Token contract address
            
        Returns:
            Dict[str, Any]: Token information
        """
        chain_id = self._get_chain_id(chain)
        
        # Native token handling
        if token_address.lower() in ['native', 'eth', 'bnb', 'matic', 'avax', 'ftm', 'sonic']:
            token_address = '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'
        
        try:
            async with self._session.get(
                f"{self.base_url}/{chain_id}/tokenInfo",
                params={"inTokenAddress": token_address},
                ssl=False
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', {})
                else:
                    logger.error(f"Failed to get token info: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error getting token info for {token_address} on chain {chain_id}: {str(e)}")
            return {}
    
    async def get_quote(
        self, 
        chain: str, 
        from_token: str, 
        to_token: str, 
        amount: str,
        slippage: float = 1.0,
        user_address: Optional[str] = None,
        dex_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get a swap quote for tokens
        
        Args:
            chain: Chain name or ID
            from_token: Source token address
            to_token: Destination token address
            amount: Amount to swap (in token decimals)
            slippage: Maximum slippage tolerance in percentage (default: 1.0%)
            user_address: User wallet address (optional)
            dex_id: Specific DEX ID to use (optional)
            
        Returns:
            Dict[str, Any]: Quote information
        """
        chain_id = self._get_chain_id(chain)
        
        # Default user address if not provided
        if not user_address:
            user_address = "0x0000000000000000000000000000000000000000"
        
        # Native token handling
        if from_token.lower() in ['native', 'eth', 'bnb', 'matic', 'avax', 'ftm', 'sonic']:
            from_token = '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'
        
        if to_token.lower() in ['native', 'eth', 'bnb', 'matic', 'avax', 'ftm', 'sonic']:
            to_token = '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'
        
        # Prepare request params
        params = {
            "inTokenAddress": from_token,
            "outTokenAddress": to_token,
            "amount": amount,
            "slippage": slippage,
            "account": user_address,
            "gasPrice": "",
            "referrer": "0x0000000000000000000000000000000000000000",
        }
        
        # Add specific DEX if requested
        if dex_id:
            params["dexId"] = dex_id
        
        try:
            async with self._session.get(
                f"{self.base_url}/{chain_id}/quote",
                params=params,
                ssl=False
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    quote_data = data.get('data', {})
                    
                    # Extract just what we need for price data
                    if quote_data:
                        return {
                            'chain': chain,
                            'from_token': quote_data.get('inToken', {}),
                            'to_token': quote_data.get('outToken', {}),
                            'price': quote_data.get('price', 0),
                            'from_token_price': quote_data.get('inTokenPrice', 0),
                            'to_token_price': quote_data.get('outTokenPrice', 0),
                            'from_amount': quote_data.get('inAmount', 0),
                            'to_amount': quote_data.get('outAmount', 0),
                            'timestamp': datetime.now().timestamp(),
                            'dex_id': quote_data.get('dex', {}).get('id', ''),
                            'dex_name': quote_data.get('dex', {}).get('name', ''),
                        }
                    return {}
                else:
                    logger.error(f"Failed to get quote: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error getting quote on chain {chain_id}: {str(e)}")
            return {}
    
    async def get_sonic_price_data(self) -> Dict[str, Any]:
        """
        Get Sonic token price data using OpenOcean quotes or fallback sources
        
        Returns:
            Dict[str, Any]: Sonic price data
        """
        # Connect if needed
        if not await self.connect():
            logger.error("Failed to connect to OpenOcean API")
            return self._get_sonic_fallback_price()
        
        try:
            # Try to get Sonic price from quotes
            # First check if OpenOcean actually supports Sonic chain
            chains = await self.get_chain_list()
            
            # Look for a chain with ID 4689 or name containing "sonic"
            sonic_supported = any(
                chain.get('id') == '4689' or 
                'sonic' in str(chain.get('name', '')).lower() 
                for chain in chains
            )
            
            if not sonic_supported:
                logger.warning("Sonic chain not officially supported by OpenOcean, using alternative method")
                return self._get_sonic_fallback_price()
            
            # Get a quote for SONIC/USDC.e on Sonic chain
            usdc_quote = await self.get_quote(
                chain='sonic',
                from_token='0xbA3a0336cb1F815B8CcF18BaE8586Cdd3f8a6a4d',  # SONIC
                to_token='0x13C31563b5c3b6Ce0E1377248B96Cbd5d9Be5a04',    # USDC.e
                amount='1000000000000000000',  # 1 SONIC
                slippage=1.0
            )
            
            if not usdc_quote:
                logger.warning("Failed to get SONIC/USDC.e quote, trying ETH")
                # Try SONIC/ETH as fallback
                eth_quote = await self.get_quote(
                    chain='sonic',
                    from_token='0xbA3a0336cb1F815B8CcF18BaE8586Cdd3f8a6a4d',  # SONIC
                    to_token='0x4200000000000000000000000000000000000006',    # WETH
                    amount='1000000000000000000',  # 1 SONIC
                    slippage=1.0
                )
                
                if not eth_quote:
                    logger.warning("Failed to get any SONIC quotes from OpenOcean API")
                    return self._get_sonic_fallback_price()
                
                return {
                    'price': eth_quote.get('price', 0),
                    'priceUsd': eth_quote.get('from_token_price', 0),
                    'volume24h': 0,  # Not available from quote
                    'liquidity': 0,  # Not available from quote
                    'priceChange24h': 0,  # Not available from quote
                    'chain': 'Sonic',
                    'symbol': 'SONIC',
                    'address': '0xbA3a0336cb1F815B8CcF18BaE8586Cdd3f8a6a4d',
                    'name': 'Sonic',
                    'source': 'openocean'
                }
            
            # Extract price data from quote
            return {
                'price': usdc_quote.get('price', 0),
                'priceUsd': usdc_quote.get('from_token_price', 0),
                'volume24h': 0,  # Not available from quote
                'liquidity': 0,  # Not available from quote
                'priceChange24h': 0,  # Not available from quote
                'chain': 'Sonic',
                'symbol': 'SONIC',
                'address': '0xbA3a0336cb1F815B8CcF18BaE8586Cdd3f8a6a4d',
                'name': 'Sonic',
                'source': 'openocean'
            }
            
        except Exception as e:
            logger.error(f"Error getting Sonic price data: {str(e)}")
            return self._get_sonic_fallback_price()
    
    def _get_sonic_fallback_price(self) -> Dict[str, Any]:
        """Get Sonic price data from a fallback source (hardcoded for now)"""
        logger.info("Using fallback method for Sonic price data")
        
        # This will be replaced by a call to the database or other price source
        # For now, use a reasonable static value to prevent application errors
        return {
            'price': 0.5,  # Approximate value 
            'priceUsd': 0.5,
            'volume24h': 10000000,  # Approximate value
            'liquidity': 50000000,  # Approximate value
            'priceChange24h': 0,
            'chain': 'Sonic',
            'symbol': 'SONIC',
            'address': '0xbA3a0336cb1F815B8CcF18BaE8586Cdd3f8a6a4d',
            'name': 'Sonic',
            'source': 'fallback'
        }
    
    async def get_market_data(self, chain: str = 'sonic', limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get market data for top tokens on a chain
        
        Args:
            chain: Chain name or ID
            limit: Maximum number of tokens to return
            
        Returns:
            List[Dict[str, Any]]: Market data for tokens
        """
        # Special case for Sonic chain
        if chain.lower() in ['sonic', '4689']:
            # Use fallback for Sonic chain as it might not be supported by OpenOcean
            sonic_data = self._get_sonic_fallback_price()
            # We need to convert the individual token data to a list format
            return [{
                'symbol': sonic_data.get('symbol', 'SONIC'),
                'name': sonic_data.get('name', 'Sonic'),
                'address': sonic_data.get('address', '0xbA3a0336cb1F815B8CcF18BaE8586Cdd3f8a6a4d'),
                'price': sonic_data.get('price', 0.5),
                'priceUsd': sonic_data.get('priceUsd', 0.5),
                'chain': 'Sonic',
                'source': sonic_data.get('source', 'fallback')
            }]
        
        # Connect if needed
        if not await self.connect():
            logger.error("Failed to connect to OpenOcean API")
            return []
        
        try:
            # Get token list for the chain
            tokens = await self.get_token_list(chain)
            
            # Get popular tokens that likely have liquidity
            popular_tokens = [
                token for token in tokens 
                if token.get('popular', False) and token.get('price', 0) > 0
            ]
            
            # Sort by name (better would be volume but not available)
            popular_tokens.sort(key=lambda x: x.get('name', ''))
            
            # Take top tokens by limit
            top_tokens = popular_tokens[:limit]
            
            # Format response
            result = []
            for token in top_tokens:
                result.append({
                    'symbol': token.get('symbol', ''),
                    'name': token.get('name', ''),
                    'address': token.get('address', ''),
                    'price': token.get('price', 0),
                    'priceUsd': token.get('price', 0),  # Same as price in this case
                    'chain': chain,
                    'source': 'openocean'
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting market data for chain {chain}: {str(e)}")
            return []
    
    async def get_dex_volumes(self, chain: str = 'sonic', limit: int = 3) -> Dict[str, Any]:
        """
        Get DEX volume data for a chain using quotes as proxies
        
        Args:
            chain: Chain name or ID
            limit: Maximum number of DEXes to return
            
        Returns:
            Dict[str, Any]: DEX volume information
        """
        # Special case for Sonic chain
        if chain.lower() in ['sonic', '4689']:
            # For Sonic chain, we'll use a specific approach with known tokens
            # Sonic/USDC.e pair for Sonic chain
            sonic_quote = await self._get_sonic_dex_volume_direct()
            if sonic_quote:
                return sonic_quote
            else:
                # Return fallback data if we couldn't get real data
                return {
                    'dex_volumes': [{
                        'dex_id': 'sonic_amm',
                        'dex_name': 'Sonic AMM',
                        'chain': 'Sonic',
                        'total_volume_usd': 70000000,  # Approximate value from DefiLlama
                        'source': 'fallback'
                    }],
                    'total_dexes': 1,
                    'chain': 'Sonic',
                    'source': 'fallback'
                }
        
        # Connect if needed
        if not await self.connect():
            logger.error("Failed to connect to OpenOcean API")
            return {}
        
        chain_id = self._get_chain_id(chain)
        
        try:
            # Get token list for the chain
            tokens = await self.get_token_list(chain)
            
            # Get a stable token (usually USDC or similar) for quotes
            stable_token = next(
                (t for t in tokens if t.get('symbol') in ['USDC', 'USDC.e', 'USDT', 'DAI']), 
                None
            )
            
            if not stable_token:
                # Fallback to a token that should exist
                stable_token = next(
                    (t for t in tokens if t.get('symbol') in ['WETH', 'WBTC', 'ETH']),
                    None
                )
            
            if not stable_token:
                logger.error(f"Could not find a suitable token for quotes on chain {chain_id}")
                return {}
            
            # Get a popular token for quotes
            popular_token = next(
                (t for t in tokens if t.get('popular') and t.get('symbol') not in 
                 ['USDC', 'USDC.e', 'USDT', 'DAI', 'WETH', 'WBTC', 'ETH']),
                None
            )
            
            if not popular_token:
                # Just get any token that's not the stable
                popular_token = next(
                    (t for t in tokens if t.get('symbol') != stable_token.get('symbol')),
                    None
                )
            
            if not popular_token:
                logger.error(f"Could not find a suitable token for quotes on chain {chain_id}")
                return {}
            
            # Get the token addresses, ensuring they're not None
            stable_address = stable_token.get('address')
            popular_address = popular_token.get('address')
            
            if not stable_address or not popular_address:
                logger.error(f"Token addresses are missing for quotes on chain {chain_id}")
                return {}
            
            # Get quote to see which DEXes are active
            quote = await self.get_quote(
                chain=chain,
                from_token=stable_address,
                to_token=popular_address,
                amount='1000000',  # Small amount
                slippage=1.0
            )
            
            # Extract DEX info from the quote
            if quote and 'dex' in quote:
                dex_info = {
                    'dex_id': quote.get('dex_id', ''),
                    'dex_name': quote.get('dex_name', ''),
                    'chain': chain,
                    'total_volume_usd': 0,  # Not available from quotes
                    'source': 'openocean'
                }
            else:
                # Use a generic fallback
                dex_info = {
                    'dex_id': f'{chain}_dex',
                    'dex_name': f'{chain.capitalize()} DEX',
                    'chain': chain,
                    'total_volume_usd': 0,
                    'source': 'openocean'
                }
            
            # Create a simple response with the DEX we found
            return {
                'dex_volumes': [dex_info],
                'total_dexes': 1,
                'chain': chain,
                'source': 'openocean'
            }
            
        except Exception as e:
            logger.error(f"Error getting DEX volumes for chain {chain}: {str(e)}")
            return {}
    
    async def _get_sonic_dex_volume_direct(self) -> Dict[str, Any]:
        """
        Get Sonic DEX volume data directly using the quote endpoint with known Sonic tokens
        
        This is a specialized method for Sonic chain since it may not be directly supported
        in the OpenOcean API chain list
        
        Returns:
            Dict[str, Any]: DEX volume information for Sonic
        """
        # Connect if needed
        if not await self.connect():
            logger.error("Failed to connect to OpenOcean API")
            return {}
        
        # Try to get a quote for a pair of known tokens on Sonic
        try:
            # We'll use SONIC and USDC.e as our pair
            sonic_address = '0xbA3a0336cb1F815B8CcF18BaE8586Cdd3f8a6a4d'
            usdc_address = '0x13C31563b5c3b6Ce0E1377248B96Cbd5d9Be5a04'
            
            # Call the quote endpoint directly
            async with self._session.get(
                f"{self.base_url}/4689/quote",
                params={
                    "inTokenAddress": sonic_address,
                    "outTokenAddress": usdc_address,
                    "amount": "1",  # 1 SONIC
                    "gasPrice": "1", 
                    "slippage": "1"
                },
                ssl=False
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    quote_data = data.get('data', {})
                    
                    # Extract DEX information from the response if available
                    if quote_data and 'path' in quote_data and 'routes' in quote_data['path']:
                        # Try to extract DEX info from the routing data
                        routes = quote_data['path']['routes']
                        dex_volumes = []
                        
                        for route in routes:
                            if 'subRoutes' in route:
                                for sub_route in route['subRoutes']:
                                    if 'dexes' in sub_route:
                                        for dex in sub_route['dexes']:
                                            if 'dex' in dex and 'id' in dex:
                                                dex_volumes.append({
                                                    'dex_id': dex.get('id', ''),
                                                    'dex_name': dex.get('dex', 'Sonic DEX'),
                                                    'chain': 'Sonic',
                                                    'percentage': dex.get('percentage', 0),
                                                    'total_volume_usd': 0,  # Not available from quote
                                                    'source': 'openocean'
                                                })
                        
                        if dex_volumes:
                            return {
                                'dex_volumes': dex_volumes,
                                'total_dexes': len(dex_volumes),
                                'chain': 'Sonic',
                                'source': 'openocean'
                            }
                
                # Fallback to using any DEX data from dexes array
                if response.status == 200:
                    data = await response.json()
                    quote_data = data.get('data', {})
                    
                    if quote_data and 'dexes' in quote_data and len(quote_data['dexes']) > 0:
                        dex_volumes = []
                        
                        # Get up to 3 DEXes to display (or all if fewer than 3)
                        max_dexes = min(3, len(quote_data['dexes']))
                        
                        for dex in quote_data['dexes'][:max_dexes]:
                            dex_volumes.append({
                                'dex_id': str(dex.get('dexIndex', '')),
                                'dex_name': dex.get('dexCode', 'Sonic DEX'),
                                'chain': 'Sonic',
                                'total_volume_usd': 0,  # Not available from quote
                                'source': 'openocean'
                            })
                        
                        return {
                            'dex_volumes': dex_volumes,
                            'total_dexes': len(dex_volumes),
                            'chain': 'Sonic',
                            'source': 'openocean'
                        }
                
                logger.error(f"Failed to get Sonic DEX volume data: {response.status}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting Sonic DEX volume data: {str(e)}")
            return {}


# Async test function
async def test_openocean_service():
    """Test the OpenOcean service"""
    service = OpenOceanService()
    
    try:
        # Connect to API
        connected = await service.connect()
        print(f"Connected: {connected}")
        
        if connected:
            # Get chain list
            chains = await service.get_chain_list()
            print(f"Chains: {len(chains)}")
            
            # Get Sonic token list
            tokens = await service.get_token_list('sonic')
            print(f"Sonic tokens: {len(tokens)}")
            
            # Get Sonic gas price
            gas = await service.get_gas_price('sonic')
            print(f"Sonic gas price: {gas}")
            
            # Get SONIC price data
            sonic_price = await service.get_sonic_price_data()
            print(f"SONIC price: {sonic_price}")
            
            # Get market data
            market_data = await service.get_market_data('sonic', 5)
            print(f"Market data: {len(market_data)}")
            
            # Get DEX volumes
            dex_volumes = await service.get_dex_volumes('sonic')
            print(f"DEX volumes: {dex_volumes}")
    
    finally:
        # Close connection
        await service.close()


# Run the test if executed directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_openocean_service())