"""
GOAT SDK connection implementation for blockchain interactions
"""
import logging
import os
import importlib
from typing import Dict, Any, List, Optional
from web3 import Web3
from dotenv import load_dotenv

from .base_connection import BaseConnection
from .errors import SonicConnectionError 

logger = logging.getLogger("connections.goat")

class GoatPlugin:
    """Base class for GOAT plugins"""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.initialized = False
        self.web3 = None

    def initialize(self, web3: Web3) -> bool:
        """Initialize plugin with Web3 instance"""
        try:
            self.web3 = web3
            self.initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize plugin: {str(e)}")
            return False

    def validate_config(self) -> bool:
        """Validate plugin configuration"""
        return True

class GoatConnection(BaseConnection):
    """GOAT SDK connection for blockchain interactions"""

    def __init__(self, config: Dict[str, Any]):
        # Load environment variables
        load_dotenv()

        # Initialize configuration
        self.rpc_url = config.get('rpc_url')
        self.chain_id = config.get('chain_id', 146)  # Default to Sonic
        self.web3 = None
        self.plugins: Dict[str, GoatPlugin] = {}

        # Initialize base class
        super().__init__(config)

        # Initialize Web3 and plugins
        self._initialize_web3()
        self._load_plugins()

        logger.info(f"Initialized GOAT connection for chain ID: {self.chain_id}")

    def _initialize_web3(self) -> None:
        """Initialize Web3 connection"""
        try:
            if not self.rpc_url:
                raise SonicConnectionError("No RPC URL provided")

            self.web3 = Web3(Web3.HTTPProvider(
                self.rpc_url,
                request_kwargs={'timeout': 30}
            ))

            if not self.web3.is_connected():
                raise SonicConnectionError("Failed to connect to network")

            chain_id = self.web3.eth.chain_id
            if chain_id != self.chain_id:
                raise SonicConnectionError(
                    f"Chain ID mismatch. Expected {self.chain_id}, got {chain_id}"
                )

            logger.info(f"Connected to network with chain ID: {chain_id}")

        except Exception as e:
            logger.error(f"Web3 initialization failed: {str(e)}")
            raise SonicConnectionError(f"Failed to initialize Web3: {str(e)}")

    def _load_plugins(self) -> None:
        """Load GOAT plugins"""
        default_plugins = [
            {
                'name': 'erc20',
                'path': 'goat_sdk_plugin_erc20.plugin',
                'args': {
                    'tokens': ['WETH', 'USDC']
                }
            },
            {
                'name': 'jsonrpc',
                'path': 'goat_sdk_plugin_jsonrpc.plugin',
                'args': {
                    'rpc_url': self.rpc_url
                }
            }
        ]

        plugin_configs = self.config.get('plugins', default_plugins)

        for plugin_config in plugin_configs:
            try:
                plugin_path = plugin_config.get('path')
                if not plugin_path:
                    continue

                # Import plugin module and class
                module_path, class_name = plugin_path.rsplit('.', 1)
                try:
                    module = importlib.import_module(module_path)
                    if hasattr(module, class_name):
                        plugin_class = getattr(module, class_name)
                        # Initialize plugin with Web3
                        plugin = plugin_class(plugin_config.get('args', {}))
                        if plugin.initialize(self.web3):
                            plugin_name = plugin_config.get('name', class_name)
                            self.plugins[plugin_name] = plugin
                            logger.info(f"✅ Loaded GOAT plugin: {plugin_name}")
                        else:
                            logger.error(f"❌ Failed to initialize plugin: {plugin_path}")
                    else:
                        logger.error(f"❌ Plugin class not found in module: {class_name}")
                except ImportError as e:
                    logger.error(f"❌ Failed to import plugin module {module_path}: {str(e)}")
                except Exception as e:
                    logger.error(f"❌ Unexpected error loading plugin {plugin_path}: {str(e)}")

            except Exception as e:
                logger.error(f"Failed to load plugin: {str(e)}")

    def get_web3(self) -> Web3:
        """Get Web3 instance"""
        if not self.web3 or not self.web3.is_connected():
            self._initialize_web3()
        return self.web3

    def get_plugin(self, name: str) -> Optional[GoatPlugin]:
        """Get plugin instance by name"""
        return self.plugins.get(name)

    def get_contract(self, address: str, abi: List[Dict[str, Any]]) -> Any:
        """Get contract instance"""
        try:
            if not self.web3.is_address(address):
                raise ValueError(f"Invalid contract address: {address}")

            return self.web3.eth.contract(
                address=Web3.to_checksum_address(address),
                abi=abi
            )

        except Exception as e:
            logger.error(f"Failed to get contract: {str(e)}")
            raise SonicConnectionError(f"Contract initialization failed: {str(e)}")

    async def is_configured(self) -> bool:
        """Check if connection is properly configured"""
        try:
            return (
                bool(self.rpc_url) and
                self.web3 is not None and
                self.web3.is_connected() and
                self.web3.eth.chain_id == self.chain_id
            )
        except Exception:
            return False

    async def close(self) -> None:
        """Close connection and cleanup resources"""
        self.web3 = None
        for plugin in self.plugins.values():
            if hasattr(plugin, 'cleanup'):
                await plugin.cleanup()
        self.plugins.clear()

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate GOAT connection configuration"""
        if not self.rpc_url:
            raise ValueError("No RPC URL provided")

        # Validate plugin configurations
        for plugin in self.plugins.values():
            if not plugin.validate_config():
                raise ValueError(f"Invalid configuration for plugin: {plugin.__class__.__name__}")

        return config

    def register_actions(self) -> None:
        """Register available GOAT actions"""
        # Basic wallet actions
        self.actions['get-balance'] = Action(
            name='get-balance',
            parameters=[
                ActionParameter('token_address', False, str, 'Token address (optional, native token if not provided)')
            ],
            description='Get wallet balance'
        )

        self.actions['send-transaction'] = Action(
            name='send-transaction',
            parameters=[
                ActionParameter('to_address', True, str, 'Recipient address'),
                ActionParameter('amount', True, float, 'Amount to send'),
                ActionParameter('token_address', False, str, 'Token address (optional)')
            ],
            description='Send tokens'
        )

        self.actions['get-token-info'] = Action(
            name='get-token-info',
            parameters=[
                ActionParameter('token_address', True, str, 'Token address to get information for')
            ],
            description='Get token information from DexScreener'
        )

        self.actions['custom-rpc-call'] = Action(
            name='custom-rpc-call',
            parameters=[
                ActionParameter('method', True, str, 'RPC method name'),
                ActionParameter('params', True, list, 'List of parameters for the RPC call')
            ],
            description='Make a custom JSON-RPC call'
        )

    async def get_balance(self, token_address: Optional[str] = None) -> float:
        """Get wallet balance for native or specific token"""
        try:
            # Use ERC20 plugin for token balances
            if token_address and 'erc20' in self.plugins:
                return await self.plugins['erc20'].get_balance(token_address)

            # Use JSON-RPC plugin for native token balance
            if 'jsonrpc' in self.plugins:
                return await self.plugins['jsonrpc'].get_balance()

            return 0.0

        except Exception as e:
            logger.error(f"Failed to get balance: {str(e)}")
            return 0.0

    async def get_token_info(self, token_address: str) -> Dict[str, Any]:
        """Get token information from DexScreener"""
        try:
            if 'dexscreener' in self.plugins:
                return await self.plugins['dexscreener'].get_token_info(token_address)
            raise ValueError("DexScreener plugin not loaded")
        except Exception as e:
            logger.error(f"Failed to get token info: {str(e)}")
            return {}

    async def custom_rpc_call(self, method: str, params: List[Any]) -> Any:
        """Execute custom JSON-RPC call"""
        try:
            if 'jsonrpc' in self.plugins:
                return await self.plugins['jsonrpc'].call(method, params)
            raise ValueError("JSON-RPC plugin not loaded")
        except Exception as e:
            logger.error(f"RPC call failed: {str(e)}")
            return None

    async def send_transaction(
        self, 
        to_address: str, 
        amount: float,
        token_address: Optional[str] = None
    ) -> str:
        """Send transaction using appropriate plugin"""
        try:
            # Use ERC20 plugin for token transfers
            if token_address and 'erc20' in self.plugins:
                return await self.plugins['erc20'].transfer(to_address, amount, token_address)

            # Use JSON-RPC plugin for native token transfers
            if 'jsonrpc' in self.plugins:
                return await self.plugins['jsonrpc'].send_transaction(to_address, amount)

            raise ValueError("No suitable plugin found for transaction")

        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}")
            raise