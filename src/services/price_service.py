"""Token Price Service

This service provides accurate token price data from multiple sources with fallbacks:
1. DexScreener (primary) - for real-time DEX prices
2. OpenOcean (secondary) - for price quotes
3. CoinGecko (tertiary) - for additional mainstream token data

This ensures accurate pricing when determining swap values.
"""
import logging
import os
import json
import time
import asyncio
from typing import Dict, Any, List, Optional, Union, Tuple
import aiohttp
import re
from web3 import Web3

logger = logging.getLogger(__name__)

class PriceService:
    """Service for fetching token prices from multiple sources"""
    
    def __init__(self):
        """Initialize the price service"""
        self._session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lifetime = 60  # Cache lifetime in seconds
        
    async def connect(self) -> bool:
        """Initialize connections to price services
        
        Returns:
            True if successfully connected
        """
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return True
        
    async def close(self) -> None:
        """Close connections"""
        if self._session:
            await self._session.close()
            self._session = None
            
    def _get_cache_key(self, token_address: str, chain_id: Union[str, int]) -> str:
        """Generate cache key for token price
        
        Args:
            token_address: Token contract address
            chain_id: Chain ID
            
        Returns:
            Cache key string
        """
        # Normalize inputs
        token_address = token_address.lower()
        chain_id = str(chain_id)
        
        return f"{chain_id}:{token_address}"
        
    def _get_from_cache(self, token_address: str, chain_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """Get token price data from cache if available and fresh
        
        Args:
            token_address: Token contract address
            chain_id: Chain ID
            
        Returns:
            Cached price data or None if not cached or expired
        """
        key = self._get_cache_key(token_address, chain_id)
        cached = self._cache.get(key)
        
        if cached:
            # Check if cache is still valid
            if time.time() - cached.get('timestamp', 0) < self._cache_lifetime:
                logger.info(f"Using cached price data for {key}")
                return cached
            
        return None
        
    def _add_to_cache(self, token_address: str, chain_id: Union[str, int], data: Dict[str, Any]) -> None:
        """Add token price data to cache
        
        Args:
            token_address: Token contract address
            chain_id: Chain ID
            data: Price data to cache
        """
        key = self._get_cache_key(token_address, chain_id)
        
        # Add timestamp to data
        data['timestamp'] = time.time()
        
        # Store in cache
        self._cache[key] = data
        logger.info(f"Added price data to cache for {key}")
    
    async def get_dexscreener_pairs(self, token_address: str, chain: str) -> Optional[List[Dict[str, Any]]]:
        """Get token pairs from DexScreener API
        
        Args:
            token_address: Token contract address
            chain: Chain name (e.g., 'ethereum', 'bsc', 'fantom', 'sonic')
            
        Returns:
            List of token pairs or None if request failed
        """
        if not self._session:
            await self.connect()
            
        try:
            # Normalize the address
            token_address = token_address.lower()
            
            # Map chain name to DexScreener format
            chain_mapping = {
                'eth': 'ethereum',
                'ethereum': 'ethereum',
                'bsc': 'bsc',
                'binance': 'bsc',
                'polygon': 'polygon',
                'matic': 'polygon',
                'fantom': 'fantom',
                'ftm': 'fantom',
                'sonic': 'fantom',  # DexScreener uses fantom for Sonic chain
                'avax': 'avalanche',
                'avalanche': 'avalanche',
                'optimism': 'optimism',
                'arbitrum': 'arbitrum'
            }
            
            dex_chain = chain_mapping.get(chain.lower(), chain.lower())
            
            # DexScreener search endpoint
            url = f"https://api.dexscreener.com/latest/dex/search"
            params = {
                "q": token_address
            }
            
            logger.info(f"Fetching DexScreener pairs for {token_address} on {dex_chain}")
            
            async with self._session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"DexScreener API request failed: {response.status}")
                    return None
                    
                data = await response.json()
                
                if not data or 'pairs' not in data:
                    logger.warning(f"No pairs found in DexScreener response")
                    return None
                    
                # Filter pairs by chain if specified
                pairs = data['pairs']
                if dex_chain:
                    pairs = [p for p in pairs if p.get('chainId', '').lower() == dex_chain]
                    
                if not pairs:
                    logger.warning(f"No pairs found for chain {dex_chain}")
                    
                return pairs
                
        except Exception as e:
            logger.error(f"Error fetching DexScreener pairs: {str(e)}")
            return None
    
    async def get_price_from_dexscreener(self, token_address: str, chain_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """Get token price from DexScreener
        
        Args:
            token_address: Token contract address
            chain_id: Chain ID
            
        Returns:
            Token price data or None if not found
        """
        # Convert chain_id to chain name
        chain_name_map = {
            '1': 'ethereum',
            '56': 'bsc',
            '137': 'polygon',
            '250': 'fantom',
            '43114': 'avalanche',
            '10': 'optimism',
            '42161': 'arbitrum',
            '146': 'sonic',  # Use fantom for Sonic as DexScreener categorizes it under Fantom
        }
        
        chain_id_str = str(chain_id)
        chain_name = chain_name_map.get(chain_id_str, 'fantom')
        
        # For Sonic chain (146), use 'fantom' in DexScreener
        if chain_id_str == '146':
            chain_name = 'fantom'
        
        # Get pairs from DexScreener
        pairs = await self.get_dexscreener_pairs(token_address, chain_name)
        
        if not pairs:
            logger.warning(f"No pairs found for {token_address} on chain {chain_id}")
            return None
            
        # Find the best pair (highest liquidity in USD)
        best_pair = None
        highest_liquidity = 0
        
        for pair in pairs:
            # Check if token address matches
            base_token = pair.get('baseToken', {})
            quote_token = pair.get('quoteToken', {})
            
            # Check either base or quote token
            is_base = base_token.get('address', '').lower() == token_address.lower()
            is_quote = quote_token.get('address', '').lower() == token_address.lower()
            
            if not (is_base or is_quote):
                continue
                
            # Check liquidity
            liquidity = pair.get('liquidity', {}).get('usd', 0)
            if liquidity > highest_liquidity:
                highest_liquidity = liquidity
                best_pair = pair
                
        if not best_pair:
            logger.warning(f"No matching pairs found for {token_address}")
            return None
            
        # Extract price data
        price_usd = best_pair.get('priceUsd')
        if not price_usd:
            logger.warning(f"No USD price found for {token_address}")
            return None
            
        # Determine if this is the base or quote token
        base_token = best_pair.get('baseToken', {})
        is_base = base_token.get('address', '').lower() == token_address.lower()
        
        # Build result
        result = {
            'price': price_usd,
            'symbol': base_token.get('symbol') if is_base else best_pair.get('quoteToken', {}).get('symbol'),
            'name': base_token.get('name') if is_base else best_pair.get('quoteToken', {}).get('name'),
            'address': token_address,
            'liquidity_usd': best_pair.get('liquidity', {}).get('usd', 0),
            'volume_24h': best_pair.get('volume', {}).get('h24', 0),
            'pair_address': best_pair.get('pairAddress'),
            'dex_id': best_pair.get('dexId'),
            'source': 'dexscreener'
        }
        
        return result
        
    async def get_price_from_openocean(self, token_address: str, chain_id: Union[str, int], 
                                       vs_token: str = None) -> Optional[Dict[str, Any]]:
        """Get token price from OpenOcean quote
        
        Args:
            token_address: Token contract address
            chain_id: Chain ID
            vs_token: Address of token to quote against (default: chain's native token)
            
        Returns:
            Token price data or None if not found
        """
        if not self._session:
            await self.connect()
            
        try:
            # Map chain ID to OpenOcean chain name
            chain_map = {
                '1': 'eth',
                '56': 'bsc',
                '137': 'polygon',
                '250': 'fantom',
                '43114': 'avax',
                '10': 'optimism',
                '42161': 'arbitrum',
                '146': 'sonic',
            }
            
            chain_id_str = str(chain_id)
            chain_name = chain_map.get(chain_id_str, 'eth')
            
            # Get stable coin address for the chain to quote against
            stable_tokens = {
                'eth': '0xdAC17F958D2ee523a2206206994597C13D831ec7',  # USDT on Ethereum
                'bsc': '0x55d398326f99059fF775485246999027B3197955',  # USDT on BSC
                'polygon': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',  # USDT on Polygon
                'fantom': '0x04068DA6C83AFCFA0e13ba15A6696662335D5B75',  # USDC on Fantom
                'avax': '0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7',  # USDT on Avalanche
                'optimism': '0x94b008aA00579c1307B0EF2c499aD98a8ce58e58',  # USDT on Optimism
                'arbitrum': '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9',  # USDT on Arbitrum
                'sonic': '0x04068DA6C83AFCFA0e13ba15A6696662335D5B75',  # USDC on Sonic/Fantom
            }
            
            # Use provided vs_token or default to stable token
            vs_address = vs_token if vs_token else stable_tokens.get(chain_name)
            if not vs_address:
                logger.warning(f"No stable token defined for chain {chain_name}, using default USDC")
                vs_address = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'  # USDC on Ethereum
                
            # Check if token_address is already a stable token
            if token_address.lower() == vs_address.lower():
                # Return price of 1.0 if this is a stablecoin
                return {
                    'price': '1.0',
                    'symbol': 'USDT',  # Assume it's a stablecoin
                    'address': token_address,
                    'source': 'openocean'
                }
                
            # Build quote request
            base_url = "https://open-api.openocean.finance/v4"
            pro_url = "https://open-api-pro.openocean.finance/v4"
            
            # Try with Pro API first
            api_key = os.getenv('OPENOCEAN_API_KEY')
            if api_key:
                url = f"{pro_url}/{chain_name}/quote"
                headers = {
                    'apikey': api_key,
                    'Content-Type': 'application/json'
                }
            else:
                url = f"{base_url}/{chain_name}/quote"
                headers = {}
                
            # Default amount for price check (equivalent to 1 token)
            amount = '1000000000000000000'  # 1 with 18 decimals
            
            params = {
                'inTokenAddress': token_address,
                'outTokenAddress': vs_address,
                'amount': amount,
                'gasPrice': '1',
                'slippage': '1'
            }
            
            logger.info(f"Getting OpenOcean quote for {token_address} on {chain_name}")
            
            async with self._session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"OpenOcean API request failed: {response.status}")
                    return None
                    
                data = await response.json()
                
                if data.get('code') != 200 or 'data' not in data:
                    logger.warning(f"No quote data in OpenOcean response: {data}")
                    return None
                    
                quote_data = data['data']
                
                # Calculate price
                in_amount = float(quote_data.get('inAmount', '0'))
                out_amount = float(quote_data.get('outAmount', '0'))
                
                if in_amount <= 0 or out_amount <= 0:
                    logger.warning(f"Invalid amounts in OpenOcean quote: in={in_amount}, out={out_amount}")
                    return None
                
                # Price in vs_token
                token_price = out_amount / in_amount
                
                # Build result
                result = {
                    'price': str(token_price),
                    'symbol': quote_data.get('inToken', {}).get('symbol', ''),
                    'name': quote_data.get('inToken', {}).get('name', ''),
                    'address': token_address,
                    'source': 'openocean'
                }
                
                return result
                
        except Exception as e:
            logger.error(f"Error fetching OpenOcean price: {str(e)}")
            return None
    
    async def get_token_price(self, token_address: str, chain_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """Get token price from all available sources with fallbacks
        
        Args:
            token_address: Token contract address
            chain_id: Chain ID
            
        Returns:
            Token price data with source information
        """
        # Check cache first
        cached = self._get_from_cache(token_address, chain_id)
        if cached:
            return cached
            
        # Try DexScreener first (most reliable DEX data)
        dex_price = await self.get_price_from_dexscreener(token_address, chain_id)
        if dex_price:
            self._add_to_cache(token_address, chain_id, dex_price)
            return dex_price
            
        # Fallback to OpenOcean
        oo_price = await self.get_price_from_openocean(token_address, chain_id)
        if oo_price:
            self._add_to_cache(token_address, chain_id, oo_price)
            return oo_price
            
        logger.warning(f"Could not find price for {token_address} on chain {chain_id} from any source")
        return None
    
    async def get_swap_quote(self, in_token: str, out_token: str, amount: str, chain_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """Get swap quote from OpenOcean
        
        Args:
            in_token: Input token address
            out_token: Output token address
            amount: Amount to swap (in token's smallest unit)
            chain_id: Chain ID
            
        Returns:
            Swap quote data or None if not available
        """
        if not self._session:
            await self.connect()
            
        try:
            # Map chain ID to OpenOcean chain name
            chain_map = {
                '1': 'eth',
                '56': 'bsc',
                '137': 'polygon',
                '250': 'fantom',
                '43114': 'avax',
                '10': 'optimism',
                '42161': 'arbitrum',
                '146': 'sonic',
            }
            
            chain_id_str = str(chain_id)
            chain_name = chain_map.get(chain_id_str, 'eth')
            
            # Build quote request
            base_url = "https://open-api.openocean.finance/v4"
            pro_url = "https://open-api-pro.openocean.finance/v4"
            
            # Try with Pro API first
            api_key = os.getenv('OPENOCEAN_API_KEY')
            if api_key:
                url = f"{pro_url}/{chain_name}/quote"
                headers = {
                    'apikey': api_key,
                    'Content-Type': 'application/json'
                }
            else:
                url = f"{base_url}/{chain_name}/quote"
                headers = {}
                
            params = {
                'inTokenAddress': in_token,
                'outTokenAddress': out_token,
                'amount': amount,
                'gasPrice': '1',
                'slippage': '1'
            }
            
            logger.info(f"Getting OpenOcean swap quote on {chain_name}: {in_token} -> {out_token}, amount: {amount}")
            
            async with self._session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"OpenOcean quote request failed: {response.status}")
                    return None
                    
                data = await response.json()
                
                if data.get('code') != 200 or 'data' not in data:
                    logger.warning(f"No quote data in OpenOcean response: {data}")
                    return None
                    
                quote_data = data['data']
                
                # Add quote source
                quote_data['source'] = 'openocean'
                
                return quote_data
                
        except Exception as e:
            logger.error(f"Error fetching OpenOcean swap quote: {str(e)}")
            return None


# Singleton instance
price_service = PriceService()