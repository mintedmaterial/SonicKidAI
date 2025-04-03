"""Trading connection implementation with DexScreener price checks and Odos/KyberSwap fallbacks"""
import logging
import os
from typing import Dict, Any, Optional, List, Union, cast
import asyncio
import json
import time
from datetime import datetime

try:
    import aiohttp
    from dotenv import load_dotenv
    from web3 import Web3
    from web3.middleware import geth_poa_middleware  # Fixed middleware import
except ImportError as e:
    logging.error(f"Failed to import required modules: {str(e)}")
    raise

from ..services.dexscreener_service import DexScreenerService
from ..utils.odos_router import OdosRouter
from .sonic_connection import SonicConnection
from .defillama_connection import DefiLlamaConnection
from .openocean_connection import OpenOceanConnection

logger = logging.getLogger(__name__)
load_dotenv()

# Default test wallet for development/testing environments
DEFAULT_TEST_WALLET = "0xCC98d2e64279645D204DD7b25A7c09b6B3ded0d9"

class TradingConnection:
    """Base class for trading connections"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.web3_connections: Dict[str, Web3] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.retry_attempts = 3
        self.retry_delay = 5

        # Initialize wallet address with fallback
        self.wallet_address = os.getenv('AGENT_WALLET_ADDRESS')
        if not self.wallet_address:
            if 'test' in config.get('environment', '').lower():
                self.wallet_address = DEFAULT_TEST_WALLET
                logger.info(f"Using test wallet address: {self.wallet_address}")
            else:
                logger.debug("No wallet address configured")
                self.wallet_address = None

        # Initialize API base URLs
        self.api_base_url = os.getenv('ODOS_API', 'https://api.odos.xyz')
        self.kyber_api = os.getenv('KYBER_API', 'https://aggregator-api.kyberswap.com')

        # Initialize optional services
        try:
            self.dexscreener = DexScreenerService()
            self.odos_router = OdosRouter()
            self.sonic_connection = SonicConnection(config)
            self.defillama = DefiLlamaConnection()
            
            # Initialize OpenOcean connection with Sonic chain configuration
            self.openocean = OpenOceanConnection({
                'chain_id': '146',  # Sonic chain ID
                'slippage': 1.0     # Default 1% slippage
            })
            
        except ImportError as e:
            logger.warning(f"Some services could not be initialized: {str(e)}")
            self.dexscreener = None
            self.odos_router = None
            self.sonic_connection = None
            self.defillama = None
            self.openocean = None

        # Token address mapping
        self.token_addresses = {
            'sonic': "0x6fB9897896Fe5D05025Eb43306675727887D0B7c",
            'shadow': "0x5C19a8a61278875F1EAE1BE4c977885B8c93A0F4",
            'metro': "0x89D453A3ae45e2f8E531Fb34dD972Ab0C3238Ecd",
            'whale': "0x2f4c28dBE76B1EeF0F2Adb537c96D10722AA351E"
        }

    async def connect(self) -> None:
        """Initialize connections"""
        try:
            # Initialize aiohttp session with proper headers
            if not self.session:
                self.session = aiohttp.ClientSession(
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': 'ZerePy/1.0'
                    }
                )
            logger.info("Testing API connections...")

            # Initialize Web3 connections
            for network, settings in self.config.get('networks', {}).items():
                try:
                    provider = Web3.HTTPProvider(
                        settings['rpc_url'],
                        request_kwargs={'timeout': 30}
                    )
                    web3 = Web3(provider)

                    # Fixed middleware injection
                    web3.middleware_onion.inject(geth_poa_middleware, layer=0)

                    if web3.is_connected():
                        chain_id = await self._get_chain_id(web3)
                        if chain_id == settings['chain_id']:
                            self.web3_connections[network] = web3
                            logger.info(f"Connected to {network} (Chain ID: {chain_id})")
                        else:
                            logger.error(f"Chain ID mismatch for {network}")
                except Exception as e:
                    logger.error(f"Failed to connect to {network}: {str(e)}")

            # Connect to other services if available
            if self.sonic_connection:
                await self.sonic_connection.connect()
            if self.defillama:
                await self.defillama.connect()
            if self.dexscreener:
                await self.dexscreener.connect()
            if self.openocean:
                if await self.openocean.connect():
                    logger.info("OpenOcean connection established successfully")
                else:
                    logger.warning("OpenOcean connection failed")

            logger.info("All trading connections initialized")

        except Exception as e:
            logger.error(f"Error in connect: {str(e)}")
            await self.close()
            raise

    async def close(self) -> None:
        """Close all connections properly"""
        try:
            # Close main session
            if self.session:
                await self.session.close()
                self.session = None

            # Close service connections
            if self.sonic_connection:
                await self.sonic_connection.close()
            if self.defillama:
                await self.defillama.close()
            if self.dexscreener:
                await self.dexscreener.close()
            if self.openocean:
                await self.openocean.close()
                
            # Close any web3 connections
            self.web3_connections.clear()

            logger.info("Successfully closed all connections")
        except Exception as e:
            logger.error(f"Error closing connections: {str(e)}")

    async def _get_chain_id(self, web3: Web3) -> int:
        """Get chain ID with retries"""
        for attempt in range(self.retry_attempts):
            try:
                return web3.eth.chain_id
            except Exception as e:
                if attempt == self.retry_attempts - 1:
                    raise
                await asyncio.sleep(self.retry_delay)
        raise Exception("Failed to get chain ID after all retries")

    async def get_token_price(self, token_address: str) -> float:
        """Get token price using DexScreener service with DeFi Llama fallback"""
        try:
            # Check for invalid token address
            if not token_address or token_address == "0x0000000000000000000000000000000000000000":
                return 0.0

            # Try DexScreener first if available
            if self.dexscreener:
                price = await self.dexscreener.get_token_price(token_address)
                if price > 0:
                    logger.info(f"Retrieved price from DexScreener: ${price:.4f}")
                    return price

            # Fallback to DeFi Llama if available
            if self.defillama:
                logger.info("DexScreener price unavailable, trying DeFi Llama fallback")
                price_data = await self.defillama.get_token_price("Sonic", token_address)
                if price_data and price_data.get('price', 0) > 0:
                    price = float(price_data['price'])
                    logger.info(f"Retrieved price from DeFi Llama: ${price:.4f}")
                    return price

            logger.warning(f"Failed to get price for token {token_address}")
            return 0.0

        except Exception as e:
            logger.error(f"Error fetching token price: {str(e)}")
            return 0.0

    async def analyze_market_query(self, text: str) -> str:
        """Enhanced market query analysis with price data integration"""
        try:
            query_lower = text.lower()
            response_parts = []

            # Check for price-related queries
            if any(word in query_lower for word in ['price', 'value', 'worth']):
                # Check for specific tokens
                for token_name, address in self.token_addresses.items():
                    if token_name in query_lower:
                        price = await self.get_token_price(address)
                        if price > 0:
                            response_parts.append(f"🔹 {token_name.title()}: ${price:.4f}")
                        else:
                            response_parts.append(f"⚠️ {token_name.title()} price data temporarily unavailable")

                # Add common tokens if mentioned
                token_map = {
                    'Sonic': "0x6fB9897896Fe5D05025Eb43306675727887D0B7c",
                    'Shadow': "0x5C19a8a61278875F1EAE1BE4c977885B8c93A0F4",
                    'Metro': "0x89D453A3ae45e2f8E531Fb34dD972Ab0C3238Ecd",
                    'Whale': "0x2f4c28dBE76B1EeF0F2Adb537c96D10722AA351E",
                    'eth': ('ETH', 'Ethereum'),
                    'btc': ('BTC', 'Bitcoin'),
                    'usdc': ('USDC', 'USD Coin')
                }

                for key, value in token_map.items():
                    if isinstance(value, tuple):
                        symbol, name = value
                    else:
                        name = key
                        symbol = key

                    if key in query_lower:
                        response_parts.append(f"ℹ️ {name} ({symbol}): Price query not supported yet")

                response = "📊 Current Market Prices:\n\n" + "\n".join(response_parts)
                if not response_parts:
                    response = "I couldn't find price data for the requested tokens. Please try again later."

                return response
            else:
                # Handle non-price queries
                return "I understand this is a market-related query. However, I need more specific information about what you'd like to know. You can ask about token prices, market stats, or trading information."

        except Exception as e:
            logger.error(f"Error in market query analysis: {str(e)}")
            return "I apologize, but I encountered an error while fetching market data. Please try again later."

    async def execute_cross_chain_swap(self, trade_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a cross-chain swap"""
        try:
            logger.info(f"Executing cross-chain swap with params: {json.dumps(trade_params, indent=2)}")

            # Get agent wallet address 
            agent_wallet = os.getenv('AGENT_WALLET_ADDRESS')
            if not agent_wallet:
                logger.error("AGENT_WALLET_ADDRESS environment variable not set")
                return {"success": False, "error": "AGENT_WALLET_ADDRESS not set"}

            # Validate token addresses
            from_token = trade_params.get('fromToken')
            to_token = trade_params.get('toToken')

            if not from_token or not to_token:
                logger.error("Missing token addresses for swap")
                return {"success": False, "error": "Missing token addresses"}

            # Try OpenOcean first if available (PRIMARY)
            if self.openocean:
                try:
                    # First get quote from OpenOcean to verify price and slippage
                    logger.info("Getting price quote from OpenOcean (PRIMARY ROUTER)")
                    
                    from_token = trade_params.get('fromToken', trade_params.get('token_address'))
                    to_token = trade_params.get('toToken')
                    amount = trade_params.get('fromAmount', trade_params.get('amount'))
                    
                    # If to_token is not provided, use a default stable token for the chain 
                    if not to_token:
                        # Default USDC for Sonic chain
                        default_tokens = {
                            '1': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',  # USDC on Ethereum
                            '146': '0x04068DA6C83AFCFA0e13ba15A6696662335D5B75',  # USDC on Sonic
                        }
                        chain_id = trade_params.get('source_chain_id', '146')
                        to_token = default_tokens.get(str(chain_id), '0x04068DA6C83AFCFA0e13ba15A6696662335D5B75')
                    
                    # Get quote from OpenOcean
                    quote = await self.openocean.get_quote(
                        in_token_address=from_token,
                        out_token_address=to_token,
                        amount=str(amount)
                    )
                    
                    if not quote:
                        logger.warning("Failed to get quote from OpenOcean, trying execution directly")
                    else:
                        # Include quote details in trade parameters
                        trade_params['quote'] = quote
                        logger.info(f"OpenOcean quote: in={quote.get('inAmount')} {quote.get('inToken', {}).get('symbol')}, " + 
                                   f"out={quote.get('outAmount')} {quote.get('outToken', {}).get('symbol')}")
                    
                    # Attempt swap with OpenOcean
                    logger.info("Attempting swap with OpenOcean (PRIMARY ROUTER)")
                    result = await self._execute_openocean_swap(trade_params, agent_wallet)
                    if result:
                        logger.info("✅ OpenOcean swap executed successfully")
                        return result
                    logger.warning("OpenOcean swap execution failed, trying Odos as secondary router")
                except Exception as e:
                    logger.warning(f"OpenOcean Router failed, trying Odos as secondary: {str(e)}")
            else:
                logger.warning("OpenOcean connection unavailable, trying Odos")
            
            # Try Odos Router as secondary option if available
            if self.odos_router:
                try:
                    logger.info("Attempting swap with Odos (SECONDARY ROUTER)")
                    quote = await self.odos_router.get_quote(
                        chain_id=146,  # Sonic chain
                        quote_payload={
                            "inputTokens": [{
                                "tokenAddress": from_token,
                                "amount": trade_params['fromAmount']
                            }],
                            "outputTokens": [{
                                "tokenAddress": to_token,
                                "proportion": 1
                            }],
                            "userAddr": agent_wallet,
                            "slippageLimitPercent": trade_params.get('slippage', 0.8),
                            "disableRFQs": True,
                        }
                    )

                    if quote:
                        result = await self._execute_odos_swap(quote, trade_params, agent_wallet)
                        if result:
                            logger.info("✅ Odos swap executed successfully")
                            return result
                        logger.warning("Odos swap execution failed, trying KyberSwap as final fallback")
                except Exception as e:
                    logger.warning(f"Odos Router failed, trying KyberSwap as final fallback: {str(e)}")

            # Try KyberSwap as last resort fallback
            logger.info("Attempting swap with KyberSwap (FINAL FALLBACK)")
            kyber_result = await self._execute_kyber_swap(trade_params, agent_wallet)
            if kyber_result:
                logger.info("✅ KyberSwap fallback executed successfully")
                return kyber_result

            return {"success": False, "error": "All swap attempts failed"}

        except Exception as e:
            logger.error(f"Error executing cross-chain swap: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _execute_odos_swap(self, quote: Dict[str, Any], trade_params: Dict[str, Any], agent_wallet: str) -> Optional[Dict[str, Any]]:
        """Execute swap using Odos Router"""
        try:
            if not self.odos_router:
                return None

            assembly_payload = {
                "pathId": quote['pathId'],
                "userAddress": agent_wallet
            }

            tx_data = await self.odos_router.assemble_transaction(
                chain_id=146,
                assembly_payload=assembly_payload
            )

            if not tx_data:
                return None

            web3 = self.web3_connections.get('sonic')
            if not web3:
                return None

            # Sign and send transaction
            signed_tx = web3.eth.account.sign_transaction({
                "to": tx_data['to'],
                "data": tx_data['data'],
                "value": tx_data.get('value', 0),
                "gasPrice": await web3.eth.gas_price,
                "gasLimit": tx_data['gasLimit'],
                "nonce": await web3.eth.get_transaction_count(agent_wallet),
            }, os.getenv("SONIC_PRIVATE_KEY"))

            tx_hash = await web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = await web3.eth.wait_for_transaction_receipt(tx_hash)

            return {
                "success": receipt.status == 1,
                "tx_hash": tx_hash.hex(),
                "route": "odos",
                "gas_used": receipt.gasUsed,
                "amount_in": trade_params['fromAmount'],
                "amount_out": quote.get('outAmounts', [0])[0] if quote.get('outAmounts') else 0
            }

        except Exception as e:
            logger.error(f"Error executing Odos swap: {str(e)}")
            return None

    async def _execute_openocean_swap(self, trade_params: Dict[str, Any], agent_wallet: str) -> Optional[Dict[str, Any]]:
        """Execute swap using OpenOcean as primary router"""
        try:
            if not self.openocean:
                logger.warning("OpenOcean connection not available")
                return None
            
            from_token = trade_params.get('fromToken')
            to_token = trade_params.get('toToken')
            amount = trade_params.get('fromAmount')
            slippage = trade_params.get('slippage', 1.0)  # Default 1% slippage
            
            # Get private key from environment
            private_key = os.getenv("SONIC_PRIVATE_KEY")
            if not private_key:
                logger.error("SONIC_PRIVATE_KEY environment variable not set")
                return None
            
            logger.info(f"Executing OpenOcean swap: {from_token} -> {to_token}, amount: {amount}")
            
            # Get quote from OpenOcean
            quote_result = await self.openocean.get_quote(
                in_token_address=from_token,
                out_token_address=to_token,
                amount=str(amount)
            )
            
            if not quote_result:
                logger.warning("Failed to get quote from OpenOcean")
                return None
                
            # Execute the swap transaction with the quote
            swap_result = await self.openocean.execute_swap(
                in_token_address=from_token,
                out_token_address=to_token,
                amount=str(amount),
                private_key=private_key,
                slippage=slippage
            )
            
            if not swap_result or not swap_result.get('success'):
                error_msg = swap_result.get('error') if swap_result else "Unknown error"
                logger.warning(f"OpenOcean swap execution failed: {error_msg}")
                return None
            
            return {
                "success": True,
                "tx_hash": swap_result.get('tx_hash'),
                "route": "openocean",
                "gas_used": swap_result.get('gas_used', 0),
                "amount_in": amount,
                "amount_out": swap_result.get('amount_out', 0)
            }
            
        except Exception as e:
            logger.error(f"Error executing OpenOcean swap: {str(e)}")
            return None
    
    async def _execute_kyber_swap(self, trade_params: Dict[str, Any], agent_wallet: str) -> Optional[Dict[str, Any]]:
        """Execute swap using KyberSwap as fallback"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': 'ZerePy/1.0'
                    }
                )

            # Get quote from KyberSwap
            async with self.session.post(
                f"{self.kyber_api}/sonic/route/encode",
                json={
                    "tokenIn": trade_params['fromToken'],
                    "tokenOut": trade_params['toToken'],
                    "amountIn": trade_params['fromAmount'],
                    "to": agent_wallet,
                    "slippageTolerance": trade_params.get('slippage', 100),  # 1%
                }
            ) as response:
                if response.status != 200:
                    return None

                kyber_data = await response.json()
                if not kyber_data.get('data'):
                    return None

                web3 = self.web3_connections.get('sonic')
                if not web3:
                    return None

                # Sign and send transaction
                signed_tx = web3.eth.account.sign_transaction({
                    "to": kyber_data['routerAddress'],
                    "data": kyber_data['data'],
                    "value": kyber_data.get('value', 0),
                    "gasPrice": await web3.eth.gas_price,
                    "gasLimit": kyber_data['gas'],
                    "nonce": await web3.eth.get_transaction_count(agent_wallet),
                }, os.getenv("SONIC_PRIVATE_KEY"))

                tx_hash = await web3.eth.send_raw_transaction(signed_tx.rawTransaction)
                receipt = await web3.eth.wait_for_transaction_receipt(tx_hash)

                return {
                    "success": receipt.status == 1,
                    "tx_hash": tx_hash.hex(),
                    "route": "kyberswap",
                    "gas_used": receipt.gasUsed,
                    "amount_in": trade_params['fromAmount'],
                    "amount_out": kyber_data.get('outputAmount', 0)
                }

        except Exception as e:
            logger.error(f"Error executing KyberSwap fallback: {str(e)}")
            return None

    async def get_token_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get current token prices"""
        raise NotImplementedError("get_token_prices must be implemented by subclass")

    async def analyze_trading_opportunity(self, symbol: str) -> Dict[str, Any]:
        """Analyze trading opportunity for symbol"""
        raise NotImplementedError("analyze_trading_opportunity must be implemented by subclass")

    async def calculate_technical_indicators(self, symbol: str) -> Dict[str, float]:
        """Calculate technical indicators for symbol"""
        raise NotImplementedError("calculate_technical_indicators must be implemented by subclass")

    async def update_price_history(self, symbol: str, price: float) -> None:
        """Update price history for symbol"""
        raise NotImplementedError("update_price_history must be implemented by subclass")