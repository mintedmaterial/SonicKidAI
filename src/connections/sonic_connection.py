"""Sonic network connection implementation"""
import logging
import time
import os
import json
import sys
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account

# Add the src directory to the Python path to enable proper imports
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from utils.odos_router import OdosRouter
from constants.networks import SONIC_NETWORKS
from constants.abi import ERC20_ABI
# Import DexScreenerService lazily to avoid circular import
# from services.dexscreener_service import DexScreenerService
from services.price_oracle_service import PriceOracleService
from connections.sonic_wallet import SonicWalletConnection
from connections.errors import (
    SonicConnectionError,
    SonicSwapError,
    SonicQuoteError
)

logger = logging.getLogger(__name__)

class SonicConnection:
    """Handle Sonic network interactions"""

    # Class-level constants
    NATIVE_TOKEN = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
    WSONIC = "0x039e2fB66102314Ce7b64Ce5Ce3E5183bc94aD38"
    USDC = "0x88b6d6bd8ba1564f8ed1c0d0d67fbd64daa4ac25"

    # Safety thresholds for trading
    SAFETY_THRESHOLDS = {
        'min_liquidity': 10000,  # $10k minimum liquidity
        'min_price': 0.000000010,   # Minimum price in USD
        'max_slippage': 0.05     # 5% maximum slippage
    }

    def __init__(self, config: Dict[str, Any]):
        """Initialize Sonic connection"""
        self.network = config.get("network", "sonic")  # Changed default from "mainnet" to "sonic"
        if self.network not in SONIC_NETWORKS:
            raise SonicConnectionError(f"Invalid network: {self.network}")

        network_config = SONIC_NETWORKS[self.network]

        # Use DRPC URL if available, otherwise fallback to provided RPC or network default
        self.rpc_url = os.getenv('SONIC_RPC_URL') or config.get("rpc") or network_config.get("rpc_url") or "https://sonic-rpc.publicnode.com"
        if not self.rpc_url:
            raise SonicConnectionError("No RPC URL available")

        self.scanner_url = network_config["scanner_url"]
        self.chain_id = network_config["chain_id"]
        self._web3: Optional[Web3] = None

        # Create wallet connection config with proper RPC URLs
        wallet_config = {
            "rpc_url": self.rpc_url,
            "chain_id": self.chain_id
        }
        
        # If network config has a list of RPCs, pass them to the wallet connection
        if "rpc_urls" in network_config:
            wallet_config["rpc_urls"] = network_config["rpc_urls"]
            logger.info(f"Using RPC URLs from network config: {network_config['rpc_urls']}")

        # Initialize connections and services
        self.wallet = SonicWalletConnection(wallet_config)
        self.odos_router = OdosRouter()
        self.price_oracle = PriceOracleService()
        
        # Lazy import DexScreenerService to avoid circular import
        from services.dexscreener_service import DexScreenerService
        self.dexscreener = DexScreenerService()

        # Initialize caches
        self.equalizer_cache = {}
        self.whale_data_cache = {}
        self.liquidity_cache = {}

        logger.info(f"Initialized Sonic connection with RPC URL: {self.rpc_url}")

    async def connect(self) -> None:
        """Connect to Sonic network with RPC fallback support"""
        # Prepare list of RPC URLs to try
        try:
            # Use the wallet connection which already has RPC fallback mechanism
            await self.wallet.connect()
            self._web3 = self.wallet.get_web3()
            
            if not self._web3 or not self._web3.is_connected():
                raise SonicConnectionError("Could not connect to Sonic network via wallet connection")
                
            logger.info(f"Connected to Sonic network: {self.network} using wallet connection")
            
        except Exception as e:
            logger.error(f"Failed to connect to Sonic network: {str(e)}")
            raise SonicConnectionError(f"Failed to connect to Sonic network: {str(e)}")

    async def get_zap_quote(
        self,
        input_token: str,
        output_token: str,
        amount: float,
        user_address: str,
        slippage: float = 0.5
    ) -> Dict[str, Any]:
        """
        Get zap quote for token swap using Odos router

        Args:
            input_token: Input token address
            output_token: Output token address  
            amount: Input amount
            user_address: User wallet address
            slippage: Maximum allowed slippage percentage

        Returns:
            Quote data including pathId for transaction assembly
        """
        try:
            if not self._web3:
                await self.connect()

            # Convert amount to Wei
            amount_wei = self._web3.to_wei(amount, 'ether')

            # Prepare quote request payload
            quote_payload = {
                "chainId": self.chain_id,
                "inputTokens": [{
                    "tokenAddress": input_token,
                    "amount": str(amount_wei)
                }],
                "outputTokens": [{
                    "tokenAddress": output_token,
                    "proportion": 1
                }],
                "userAddr": user_address,
                "slippageLimitPercent": slippage,
                "compact": True
            }

            # Call Odos API for quote
            quote = await self.odos_router.get_quote(
                chain_id=self.chain_id,
                quote_payload=quote_payload
            )

            if not quote or not isinstance(quote, dict):
                raise SonicQuoteError("Invalid quote response")

            if 'pathId' not in quote:
                raise SonicQuoteError("Missing pathId in quote")

            logger.debug(f"Quote response: {quote}")
            return quote

        except Exception as e:
            logger.error(f"Error getting zap quote: {str(e)}")
            raise SonicQuoteError(f"Failed to get quote: {str(e)}")

    async def assemble_transaction(
        self,
        path_id: str,
        user_address: str,
        simulate: bool = True
    ) -> Dict[str, Any]:
        """
        Assemble transaction data for a quoted path

        Args:
            path_id: Path ID from quote response
            user_address: User wallet address
            simulate: Whether to simulate the transaction

        Returns:
            Transaction data ready for execution
        """
        try:
            assembly_payload = {
                "pathId": path_id,
                "userAddr": user_address,
                "simulate": simulate
            }

            tx_data = await self.odos_router.assemble_transaction(
                chain_id=self.chain_id,
                assembly_payload=assembly_payload
            )

            if not tx_data or not isinstance(tx_data, dict):
                raise SonicSwapError("Invalid transaction assembly response")

            return tx_data

        except Exception as e:
            logger.error(f"Failed to assemble transaction: {str(e)}")
            raise SonicSwapError(f"Transaction assembly failed: {str(e)}")

    async def execute_swap(self,
                        input_token: str,
                        output_token: str, 
                        amount: float,
                        user_address: str,
                        slippage: float = 0.5) -> Dict[str, Any]:
        """
        Execute token swap using Odos router with zap quote

        Args:
            input_token: Input token address
            output_token: Output token address
            amount: Input amount
            user_address: User wallet address
            slippage: Maximum allowed slippage percentage

        Returns:
            Transaction data and execution results
        """
        try:
            # Get zap quote first
            quote = await self.get_zap_quote(
                input_token=input_token,
                output_token=output_token,
                amount=amount,
                user_address=user_address,
                slippage=slippage
            )

            if not quote:
                raise SonicSwapError("Failed to get swap quote")

            # Assemble transaction
            tx_data = await self.assemble_transaction(
                path_id=quote['pathId'],
                user_address=user_address,
                simulate=True
            )

            # Add chain info and quote
            tx_data['chain_id'] = self.chain_id
            tx_data['scanner_url'] = self.scanner_url
            tx_data['quote'] = quote

            return tx_data

        except SonicQuoteError as e:
            raise SonicSwapError(f"Quote error: {str(e)}")
        except Exception as e:
            logger.error(f"Error executing swap: {str(e)}")
            raise SonicSwapError(f"Failed to execute swap: {str(e)}")

    async def get_token_price(self, token_address: str) -> float:
        """Get token price using PriceOracle service"""
        if token_address.lower() == self.NATIVE_TOKEN.lower():
            token_address = self.WSONIC
        return await self.price_oracle.get_token_price(token_address, 'sonic')

    async def get_pair_liquidity(self, token_a: str, token_b: str) -> float:
        """Get pair liquidity using PriceOracle service"""
        return await self.price_oracle.get_pair_liquidity(token_a, token_b, 'sonic')

    async def get_whale_trades(self, token_address: Optional[str] = None) -> List[Dict]:
        """Get whale trades using WhaleTracker service"""
        try:
            return await self.whale_tracker.get_whale_trades(token_address)
        except Exception as e:
            logger.error(f"Failed to get whale trades: {str(e)}")
            return []

    async def get_balance(self, token_address: Optional[str] = None) -> float:
        """Get token balance using wallet connection"""
        try:
            return await self.wallet.get_balance(token_address)
        except Exception as e:
            logger.error(f"Failed to get balance: {str(e)}")
            return 0.0

    async def transfer(self, to_address: str, amount: float, token_address: Optional[str] = None) -> str:
        """Transfer tokens using wallet connection"""
        try:
            if token_address and token_address.lower() != self.NATIVE_TOKEN.lower():
                return await self.wallet.send_token(token_address, to_address, amount)
            else:
                return await self.wallet.send_native(to_address, amount)
        except Exception as e:
            logger.error(f"Transfer failed: {str(e)}")
            raise

    async def get_token_info(self, token_address: str) -> Tuple[int, str]:
        """Get token info (decimals and symbol)"""
        try:
            if not self._web3:
                await self.connect()
            token_contract = self._web3.eth.contract(
                address=self._web3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )
            decimals = token_contract.functions.decimals().call()
            symbol = token_contract.functions.symbol().call()
            return decimals, symbol
        except Exception as e:
            logger.error(f"Failed to get token info: {str(e)}")
            return 18, "UNKNOWN"  # Default values

    def get_age_category(self, age_days: float) -> str:
        """Determine token age category"""
        if age_days < 7:
            return "New"
        elif age_days < 30:
            return "Young"
        elif age_days < 90:
            return "Mature"
        else:
            return "Old"

    async def get_project_contracts(self, project_name: Optional[str] = None) -> Dict[str, Any]:
        """Get contract addresses for specific or all top projects"""
        if project_name:
            return self.TOP_PROJECTS.get(project_name.lower(), {})
        return self.TOP_PROJECTS

    async def search_pairs(self, query: str, chain: Optional[str] = None) -> Optional[Dict]:
        """Search for trading pairs across supported chains"""
        try:
            return await self.dexscreener.search_pairs(query, chain)
        except Exception as e:
            logger.error(f"Error searching pairs: {str(e)}")
            return None

    async def get_pair_data(self, chain: str, pair_address: str) -> Optional[Dict]:
        """Get pair data from DexScreener"""
        try:
            return await self.dexscreener.get_pair_by_address(pair_address, chain)
        except Exception as e:
            logger.error(f"Error fetching pair data: {str(e)}")
            return None

    # 10Top Sonic Projects and Contracts
    TOP_PROJECTS = {
        'equalizer': {
            'name': 'Equalizer DEX',
            'type': 'dex',
            'contracts': {
                'factory': '0x1A29fBe1d5C8A7c04907Cc7A878C496853ce8588',
                'router': '0x7A250d5630B4cF539739dF2C5dAcb4c659F2488D',
                'staking': '0x4f8AD938eBA0CD19155a835f617317a6E788c868'
            }
        },
        'blacksail': {
            'name': 'BlackSail Finance',
            'type': 'lending',
            'contracts': {
                'main': '0x39E1931e8477ABD0e44827275A7CA5F28E4B39bA',
                'staking': '0x2b591e99afE9f32eAA6214f7B7629768c40Eeb39'
            }
        },
        'paintswap': {
            'name': 'PaintSwap NFT',
            'type': 'nft',
            'contracts': {
                'marketplace': '0x6F1c0C45F28Bb9E0b416AE7d2B4D76833b1fd797',
                'exchange': '0x733aB8b06DDDEf27Aaa1eA4686B590c71B559eb2'
            }
        }
    }

    # Common pairs with minimum liquidity thresholds (in USD)
    COMMON_PAIRS = {
        'SONIC/USDC': {
            'tokens': (NATIVE_TOKEN, USDC),
            'min_liquidity': 10000  # $10k minimum liquidity
        },
        'WSONIC/USDC': {
            'tokens': (WSONIC, USDC),
            'min_liquidity': 10000
        }
    }

    # Specific token pairs to track
    SPECIFIC_PAIR_ADDRESSES = [
        # Existing important pairs
        "0xf316A1cB7376021ad52705c1403DF86C7A7A18d0",
        "0xe920d1DA9A4D59126dC35996Ea242d60EFca1304",
        "0xC046dCb16592FBb3F9fA0C629b8D93090d4cB76",
        "0xf4F9C50455C698834Bb645089DbAa89093b93838",
        "0x690d956D97d3EEe18AB68ED1A28a89d531734F3d",
        "0x6fB9897896Fe5D05025Eb43306675727887D0B7c",
        "0x4EEC869d847A6d13b0F6D1733C5DEC0d1E741B4f",
        "0x79bbF4508B1391af3A0F4B30bb5FC4aa9ab0E07C",
        "0x71E99522EaD5E21CF57F1f542Dc4ad2E841F7321",
        "0x0e0Ce4D450c705F8a0B6Dd9d5123e3df2787D16B",
        "0xA04BC7140c26fc9BB1F36B1A604C7A5a88fb0E70",
        "0x59524D5667B299c0813Ba3c99a11C038a3908fBC",
        "0x3333b97138D4b086720b5aE8A7844b1345a33333",
        # New Kyberswap pairs
        "0xd3dce716f3ef535c5ff8d041c1a41c3bd89b97ae",
        "0xddf26b42c1d903de8962d3f79a74a501420d5f19",
        "0xe5da20f15420ad15de0fa650600afc998bbe3955",
        "0x7a08bf5304094ca4c7b4132ef62b5edc4a3478b7",
        "0x43f9a13675e352154f745d6402e853fecc388aa5",
        "0xc6ec02cebd0206b7339fcfe34f724aef49245bf0",
        "0x8d2b12d0dc9bb13c62d213efbea10fd0bfce3c88",
        "0x36adc8528277c46018456e3bc9dec56ac74beb36",
        "0x537c8c7193784d76ab154e13b4b0202990797964",
        "0x2be17859e8042b4deb1e9ea08cf15858eb4bd80a",
        "0x56192e94434c4fd3278b4fa53039293fb00de3db",
        "0xbf40bbbad774b0075ae0fa619059ddf273e13076"
    ]

    # List of whale wallets to monitor
    WHALE_WALLETS = [
        "0xe7BC06490A89bc5E2CefAe6ECaB7cD394cd25F94",
        "0xf74e5155E6553e06a43b14C280e925758D0ba878",
        "0x62c6E060EA69b7C6d145B73bC834ede9a1B7Eed8",
        "0x66c7f23E8A93A963e85c67B202bc1f5F01cF8dF8",
        "0x431e81e5dfb5a24541b5ff8762bdef3f32f96354",
        "0x5687F1A317c62fE52546cE993Bcf9cbDc8a36Be2",
        "0x480ADe73C2A40f347202de6dF6065576f7c82829",
        "0xa064B34DC0aEeF23e48B400DC4b0A3f940B55865"
    ]

    # Cache settings
    price_cache: Dict[str, Tuple[float, float]] = {}
    liquidity_cache: Dict[str, Tuple[float, float]] = {}
    specific_pair_cache: Dict[str, Dict[str, Any]] = {}
    whale_data_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
    equalizer_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    price_cache_duration = 30  # 30 seconds for specific pairs
    general_cache_duration = 60  # 1 minute for other pairs
    whale_cache_duration = 300  # 5 minutes for whale data

    async def analyze_token(self, token_address: str, whale_tracker = None) -> Dict[str, Any]:
        """Get comprehensive token analysis with optional whale tracking"""
        try:
            token_contract = self._web3.eth.contract(
                address=self._web3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )

            try:
                symbol = token_contract.functions.symbol().call()
                decimals = token_contract.functions.decimals().call()
            except Exception as e:
                logger.error(f"Error getting token info: {e}")
                symbol = "UNKNOWN"
                decimals = 18

            # Get data from services
            price = await self.get_token_price(token_address)
            liquidity = await self.get_pair_liquidity(token_address, self.USDC)

            # Get whale activity data if whale_tracker is provided
            whale_activity = {}
            if whale_tracker:
                try:
                    whale_activity = await whale_tracker.analyze_whale_activity(token_address)
                except Exception as e:
                    logger.error(f"Error getting whale activity: {e}")
                    whale_activity = {
                        'total_trades': 0,
                        'total_volume_usd': 0,
                        'buy_pressure': 0
                    }

            analysis = {
                'token_info': {
                    'address': token_address,
                    'symbol': symbol,
                    'decimals': decimals,
                    'price_usd': price
                },
                'market_data': {
                    'liquidity_usd': liquidity,
                    'whale_activity_24h': whale_activity.get('total_trades', 0),
                    'whale_volume_usd': whale_activity.get('total_volume_usd', 0),
                    'buy_pressure': whale_activity.get('buy_pressure', 0)
                },
                'analysis': {
                    'liquidity_status': "Healthy" if liquidity >= 50000 else "Low",
                    'whale_activity': "High" if whale_activity.get('total_trades', 0) > 5 else "Low",
                    'trading_status': self._get_trading_status(
                        liquidity,
                        whale_activity.get('total_trades', 0),
                        whale_activity.get('buy_pressure', 0)
                    )
                }
            }

            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze token: {str(e)}")
            return {}

    def _get_trading_status(
        self,
        liquidity: float,
        whale_trades: int,
        buy_pressure: float
    ) -> str:
        """Determine trading status based on metrics"""
        if liquidity < 10000:
            return "High Risk - Low Liquidity"
        elif liquidity >= 50000 and whale_trades > 5:
            if buy_pressure > 0.7:
                return "Active Accumulation"
            elif buy_pressure < 0.3:
                return "Heavy Distribution"
            else:
                return "Active Trading"
        elif liquidity >= 25000:
            return "Moderate Activity"
        else:
            return "Low Activity"

    async def fetch_equalizer_stats(self) -> Optional[Dict]:
        """Fetch pair data from Equalizer API"""
        try:
            current_time = time.time()

            # Check cache first
            if 'equalizer_stats' in self.equalizer_cache:
                timestamp, data = self.equalizer_cache['equalizer_stats']
                if current_time - timestamp < self.general_cache_duration:
                    return data

            #data = await self.equalizer.fetch_global_statistics() #Removed due to missing equalizer service

            # Cache the results
            #self.equalizer_cache['equalizer_stats'] = (current_time, data) #Removed due to missing equalizer service
            return None #Return None since data fetching is not possible.

        except Exception as e:
            logger.error(f"Failed to fetch Equalizer stats: {str(e)}")
            return None

    async def get_whale_trades(self, token_address: Optional[str] = None) -> List[Dict]:
        """Get recent whale wallet transactions from Equalizer"""
        try:
            current_time = time.time()

            # Check cache first
            cache_key = f"whale_trades_{token_address}" if token_address else "whale_trades_all"
            if cache_key in self.whale_data_cache:
                timestamp, trades = self.whale_data_cache[cache_key]
                if current_time - timestamp < self.whale_cache_duration:
                    return trades

            #whale_trades = await self.whale_tracker.get_whale_trades(token_address) #Removed due to missing whale_tracker service

            # Cache the results
            #self.whale_data_cache[cache_key] = (current_time, whale_trades) #Removed due to missing whale_tracker service
            return [] #Return empty list since data fetching is not possible

        except Exception as e:
            logger.error(f"Failed to get whale trades: {str(e)}")
            return []

    def get_trading_status(self, liquidity: float, whale_activity: int) -> str:
        """Determine trading status based on metrics"""
        if liquidity < 10000:
            return "High Risk - Low Liquidity"
        elif liquidity >= 50000 and whale_activity > 5:
            return "Active Trading"
        elif liquidity >= 25000:
            return "Moderate Activity"
        else:
            return "Low Activity"

    async def get_pair_liquidity(self, token_a: str, token_b: str) -> float:
        """Get pair liquidity in USD using Equalizer data"""
        try:
            # Check cache first
            pair_key = f"{token_a}_{token_b}"
            if pair_key in self.liquidity_cache:
                timestamp, liquidity = self.liquidity_cache[pair_key]
                if time.time() - timestamp < self.general_cache_duration:
                    return liquidity

            liquidity = await self.price_oracle.get_pair_liquidity(token_a, token_b, 'sonic')
            self.liquidity_cache[pair_key] = (time.time(), liquidity)
            return liquidity

        except Exception as e:
            logger.error(f"Failed to get pair liquidity: {str(e)}")
            return 0.0

    async def fetch_data(self, url: str, source_name: str) -> Optional[Dict]:
        """Generic data fetching helper function"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            logger.error(f"Error fetching data from {source_name}: {e}")
            return None

    async def fetch_token_data_from_dexscreener_specific_pairs(self) -> Dict[str, Dict[str, Any]]:
        """Batch fetch prices for specific token pairs"""
        specific_pairs_data = {}
        for address in self.SPECIFIC_PAIR_ADDRESSES:
            pair_data = await self.dexscreener.get_pair_by_address(address, 'sonic')
            if pair_data:
                specific_pairs_data[address] = pair_data
        return specific_pairs_data if specific_pairs_data else {}

    async def get_pair_info(self, token_a: str, token_b: str) -> Dict[str, Any]:
        """Get trading pair information including liquidity"""
        try:
            decimals_a, symbol_a = await self.get_token_info(token_a)
            decimals_b, symbol_b = await self.get_token_info(token_b)

            # Check if it's a common pair
            pair_name = f"{symbol_a}/{symbol_b}"
            pair_info = None
            for common_pair, info in self.COMMON_PAIRS.items():
                if pair_name == common_pair or f"{symbol_b}/{symbol_a}" == common_pair:
                    pair_info = info
                    break

            liquidity = await self.get_pair_liquidity(token_a, token_b)

            return {
                'token_a': {
                    'address': token_a,
                    'symbol': symbol_a,
                    'decimals': decimals_a,
                    'price': await self.get_token_price(token_a)
                },
                'token_b': {
                    'address': token_b,
                    'symbol': symbol_b,
                    'decimals': decimals_b,
                    'price': await self.get_token_price(token_b)
                },
                'pair_name': pair_name,
                'is_common': pair_info is not None,
                'min_liquidity': pair_info['min_liquidity'] if pair_info else 10000,  # Default $10k min liquidity
                'current_liquidity': liquidity
            }

        except Exception as e:
            logger.error(f"Failed to get pair info: {str(e)}")
            raise SonicConnectionError(f"Invalid trading pair: {token_a}/{token_b}")

    async def validate_pair(self, token_a: str, token_b: str) -> bool:
        """Validate if a trading pair is valid and has sufficient liquidity"""
        try:
            pair_info = await self.get_pair_info(token_a, token_b)
            logger.info(f"Validating trading pair: {pair_info['pair_name']}")

            # Check minimum liquidity requirements
            if pair_info['current_liquidity'] < pair_info['min_liquidity']:
                logger.warning(
                    f"Insufficient liquidity for {pair_info['pair_name']}. "
                    f"Required: ${pair_info['min_liquidity']:,.2f}, "
                    f"Available: ${pair_info['current_liquidity']:,.2f}"
                )
                return False

            # Check if either token is SONIC or WSONIC for routing
            is_sonic_pair = (
                token_a.lower() in [self.NATIVE_TOKEN.lower(), self.WSONIC.lower()] or
                token_b.lower() in [self.NATIVE_TOKEN.lower(), self.WSONIC.lower()]
            )

            # Check token prices and balances
            price_a = pair_info['token_a']['price']
            price_b = pair_info['token_b']['price']
            balance_a = await self.get_balance(token_a)
            balance_b = await self.get_balance(token_b)

            value_a = price_a * balance_a
            value_b = price_b * balance_b

            logger.info(
                f"Token values - "
                f"{pair_info['token_a']['symbol']}: ${value_a:,.2f}, "
                f"{pair_info['token_b']['symbol']}: ${value_b:,.2f}"
            )

            # Validate based on common pair status or SONIC involvement
            return (pair_info['is_common'] and pair_info['current_liquidity'] >= pair_info['min_liquidity']) or (
                is_sonic_pair and pair_info['current_liquidity'] >= 10000  # $10k min for non-common pairs
            )

        except Exception as e:
            logger.error(f"Failed to validate pair: {str(e)}")
            return False

    async def swap(
        self,
        token_in: str,
        token_out: str,
        amount: float,
        user_address: str,
        slippage: float = 0.5
    ) -> Dict[str, Any]:
        """Execute token swap using Odos router"""
        try:
            result = await self.execute_swap(input_token=token_in, output_token=token_out, amount=amount, user_address=user_address, slippage=slippage)
            return result
        except Exception as e:
            logger.error(f"Swap failed: {str(e)}")
            raise SonicConnectionError(f"Swap failed: {str(e)}")

    async def gettoken_decimals(self, token_address: str) -> int:
        """Get tokendecimals"""
        try:
            if not self._web3:  # Fixed typo from self_web3
                await self.connect()

            token_contract = self._web3.eth.contract(
                address=self._web3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )
            return token_contract.functions.decimals().call()
        except Exception as e:
            logger.error(f"Failed to get token decimals: {str(e)}")
            return 18  # Default to 18 decimals

    async def approve_token(
        self,
        token_address: str,
        spender_address: str,
        amount: int
    ) -> Optional[str]:
        """Approve spender for token transfers"""
        try:
            if not self._web3:
                await self.connect()

            if token_address.lower() == self.NATIVE_TOKEN.lower():
                return None  # No approval needed for native token

            token_contract = self._web3.eth.contract(
                address=self._web3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )

            private_key = os.getenv('WALLET_PRIVATE_KEY')
            if not private_key:
                raise SonicConnectionError("Missing WALLET_PRIVATE_KEY")

            if not private_key.startswith('0x'):
                private_key = '0x' + private_key

            account = self._web3.eth.account.from_key(private_key)
            spender_address = self._web3.to_checksum_address(spender_address)

            # Check current allowance
            current_allowance = token_contract.functions.allowance(
                account.address,
                spender_address
            ).call()

            if current_allowance < amount:
                #                # Get token info for logging
                decimals, symbol = await self.get_token_info(token_address)
                human_amount = amount / (10 ** decimals)
                logger.info(f"Approving {human_amount} {symbol} for spender {spender_address}")

                # Prepare approval transaction
                approve_tx = token_contract.functions.approve(
                    spender_address,
                    amount
                ).build_transaction({'from': account.address,
                    'gas': 100000,  # Estimated gas forapprovals
                    'gasPrice': int(self._web3.eth.gas_price * 1.1),  # 10% buffer
                    'nonce': self._web3.eth.get_transaction_count(account.address),
                    'chainId': self.chain_id
                })

                # Sign and send approval
                signed_tx = account.sign_transaction(approve_tx)
                tx_hash = self._web3.eth.send_raw_transaction(signed_tx.rawTransaction)

                # Wait for receipt
                receipt = self._web3.eth.wait_for_transaction_receipt(tx_hash)
                if receipt['status'] != 1:
                    raise SonicConnectionError("Approval transaction failed")

                return tx_hash.hex()

            return None

        except Exception as e:
            logger.error(f"Token approval failed: {str(e)}")
            raise

    async def analyze_pair(self, pair: Dict, dune_data: Dict = None) -> Dict[str, Any]:
        """Analyze trading pair with multiple data sources"""
        try:
            if not pair or not isinstance(pair, dict):
                raise ValueError("Invalid pair data")

            base_token = pair.get('baseToken', {})
            quote_token = pair.get('quoteToken', {})
            liquidity = pair.get('liquidity', {})
            price_change = pair.get('priceChange', {})

            pair_address = pair.get('pairAddress')
            if not pair_address:
                raise ValueError("Missing pair address")

            # Fetch data from multiple sources
            dexscreener_data = await self.dexscreener.get_pair_by_address(pair_address, 'sonic')
            #meme_api_data = await self.fetch_token_data_from_meme_api(base_token.get('address')) #Removed due to missing function
            #defillama_data = await self.fetch_token_data_from_defillama(base_token.get('address')) #Removed due to missing function

            # Combine data from all sources
            combined_data = {
                'dexscreener': dexscreener_data,
                #'meme_api': meme_api_data, #Removed due to missing function
                #'defillama': defillama_data #Removed due to missing function
            }

            # Get best value helper function
            def get_best_value(data_sources, *keys):
                for source in data_sources.values():
                    if source:
                        value = source
                        for key in keys:
                            if isinstance(value, dict) and key in value:
                                value = value[key]
                            else:
                                value = None
                                break
                        if value is not None:
                            return value
                return None

            # Analysis with safe type conversion
            def safe_float(value: Any) -> Optional[float]:
                if value is None:
                    return None
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return None

            # Use the most reliable data source for each metric
            analysis = {
                'pair_address': pair_address,
                'dex_id': pair.get('dexId'),
                'pair_url': pair.get('url'),
                'base_token_name': base_token.get('name', 'Unknown'),
                'base_token_symbol': base_token.get('symbol', 'Unknown'),
                'base_token_address': base_token.get('address'),
                'quote_token_symbol': quote_token.get('symbol', 'Unknown'),
                'price_usd': safe_float(get_best_value(combined_data, 'price_usd', 'priceUsd')),
                'liquidity_usd': safe_float(get_best_value(combined_data, 'liquidity_usd', 'liquidity', 'usd')),
                'volume_24h': safe_float(get_best_value(combined_data, 'volume_24h', 'volume24h')),
                'price_change_24h': safe_float(get_best_value(combined_data, 'price_change_24h', 'priceChange', 'h24')),
                'created_at': pair.get('pairCreatedAt'),
                'fdv': safe_float(get_best_value(combined_data, 'fdv')),
                'market_cap': safe_float(get_best_value(combined_data, 'market_cap', 'marketCap')),
            }

            # Add safety checks
            analysis['meets_liquidity_threshold'] = (
                analysis['liquidity_usd'] >= self.SAFETY_THRESHOLDS['min_liquidity']
            )

            # Calculate volume to liquidity ratio if data available
            if analysis['volume_24h'] and analysis['liquidity_usd']:
                analysis['volume_to_liquidity_ratio'] = (
                    analysis['volume_24h'] / analysis['liquidity_usd']
                )

            # Add age-related data if created_at exists
            if analysis['created_at']:
                age_days = (time.time() * 1000 - analysis['created_at']) / (1000 * 86400)
                analysis['age_days'] = age_days
                analysis['age_category'] = self.get_age_category(age_days)

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing pair: {str(e)}")
            return {
                'pair_address': pair.get('pairAddress', 'unknown'),
                'base_token_symbol': 'ERROR',
                'quote_token_symbol': 'ERROR',
                'error': str(e)
            }

    def get_age_category(self, age_days: float) -> str:
        """Determine token age category"""
        if age_days < 7:
            return "New"
        elif age_days < 30:
            return "Young"
        elif age_days < 90:
            return "Mature"
        else:
            return "Old"

    # Safety thresholds for trading
    SAFETY_THRESHOLDS = {
        'min_liquidity': 10000,  # $10k minimum liquidity
        'min_price': 0.000000010,   # Minimum price in USD
        'max_slippage': 0.05     # 5% maximum slippage
    }
    async def get_project_contracts(self, project_name: Optional[str] = None) -> Dict[str, Any]:
        """Get contract addresses for specific or all top projects"""
        if project_name:
            return self.TOP_PROJECTS.get(project_name.lower(), {})
        return self.TOP_PROJECTS

    async def search_project_pairs(self, project_name: str) -> Optional[Dict]:
        """Search for pairs related to a specific project"""
        try:
            project = self.TOP_PROJECTS.get(project_name.lower())
            if not project:
                return None

            # Search for all contract-related pairs
            pairs_data = {}
            for contract_name, address in project['contracts'].items():
                pairs = await self.dexscreener.search_pairs(address)
                if pairs:
                    pairs_data[contract_name] = pairs

            return {
                'project_name': project['name'],
                'project_type': project['type'],
                'pairs_data': pairs_data
            }

        except Exception as e:
            logger.error(f"Error searching project pairs: {str(e)}")
            return None

    async def analyze_project_liquidity(self, project_name: str) -> Dict[str, Any]:
        """Analyze liquidity across all pairs for a specific project"""
        try:
            pairs_data = await self.search_project_pairs(project_name)
            if not pairs_data:
                return {}

            total_liquidity = 0
            pair_count = 0
            active_pairs = []

            # Analyze each pair's data
            for contract_data in pairs_data.get('pairs_data', {}).values():
                for pair in contract_data.get('pairs', []):
                    liquidity = float(pair.get('liquidity', {}).get('usd', 0))
                    if liquidity > 0:
                        total_liquidity += liquidity
                        pair_count += 1
                        if liquidity >= self.SAFETY_THRESHOLDS['min_liquidity']:
                            active_pairs.append({
                                'pair_address': pair.get('pairAddress'),
                                'liquidity': liquidity,
                                'volume_24h': float(pair.get('volume', {}).get('h24', 0))
                            })

            return {
                'project_name': pairs_data['project_name'],
                'total_liquidity': total_liquidity,
                'pair_count': pair_count,
                'active_pairs': sorted(active_pairs, key=lambda x: x['liquidity'], reverse=True),
                'analysis_timestamp': time.time()
            }

        except Exception as e:
            logger.error(f"Error analyzing project liquidity: {str(e)}")
            return {}

    async def search_pairs(self, query: str, chain: Optional[str] = None) -> Optional[Dict]:
        """Search for trading pairs across supported chains"""
        try:
            return await self.dexscreener.search_pairs(query, chain)
        except Exception as e:
            logger.error(f"Error searching pairs: {str(e)}")
            return None

    # This duplicate method has been removed as it conflicts with the one earlier in the file

    async def close(self):
        """Close all connections"""
        try:
            # Close web3 connections
            self._web3 = None

            # Close wallet connection if exists
            if hasattr(self, 'wallet') and hasattr(self.wallet, 'close'):
                await self.wallet.close()

            # Close price oracle if exists
            if hasattr(self, 'price_oracle') and hasattr(self.price_oracle, 'close'):
                await self.price_oracle.close()

            # Close dexscreener if exists
            if hasattr(self, 'dexscreener') and hasattr(self.dexscreener, 'close'):
                await self.dexscreener.close()

            logger.info("Closed all Sonic connections")
        except Exception as e:
            logger.error(f"Error closing Sonic connections: {str(e)}")
            raise