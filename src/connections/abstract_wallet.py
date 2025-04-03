"""Abstract wallet connection with proper configuration and plugin support"""
import logging
import os
from typing import Dict, Any, Optional, List, Type, get_type_hints
import importlib
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

class AbstractWalletError(Exception):
    """Base exception for Abstract wallet errors"""
    pass

class WalletPlugin:
    """Base class for wallet plugins"""
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def initialize(self) -> bool:
        """Initialize the plugin"""
        return True

    def validate_transaction(self, tx_data: Dict[str, Any]) -> bool:
        """Validate transaction data"""
        return True

class AbstractWallet:
    def __init__(self, config: Dict[str, Any]):
        """Initialize Abstract wallet connection with configurations and plugins"""
        self.config = config
        self.web3 = None
        self.account = None
        self.retry_attempts = 3
        self.retry_delay = 5
        self.plugins: List[WalletPlugin] = []

        # Initialize wallet with proper configuration
        self.wallet_address = config.get('wallet_address', os.getenv('ABSTRACT_ADDRESS'))
        self.private_key = config.get('private_key', os.getenv('ABSTRACT_PRIVATE_KEY'))

        if not self.wallet_address or not self.private_key:
            raise AbstractWalletError("Missing Abstract wallet credentials")

        # Clean and validate the private key format
        if self.private_key.startswith('0x'):
            self.private_key = self.private_key[2:]

        if len(self.private_key) != 64:
            raise AbstractWalletError("Invalid private key format")

        # Initialize Web3 connection
        self.rpc_url = config.get('rpc_url', 'https://mainnet.abstract.com/v1')

        # Load plugins
        self._load_plugins()

    def _load_plugins(self) -> None:
        """Load wallet plugins from configuration"""
        plugin_configs = self.config.get('plugins', [])
        for plugin_config in plugin_configs:
            try:
                plugin_path = plugin_config.get('path')
                if not plugin_path:
                    continue

                module_path, class_name = plugin_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                plugin_class = getattr(module, class_name)

                plugin = plugin_class(plugin_config)
                if plugin.initialize():
                    self.plugins.append(plugin)
                    logger.info(f"Loaded wallet plugin: {class_name}")

            except Exception as e:
                logger.error(f"Failed to load plugin: {str(e)}")

    async def connect(self):
        """Initialize connection to Abstract network with enhanced error handling"""
        try:
            logger.info("Initializing Abstract wallet connection...")

            # Set up Web3 provider with retry mechanism
            provider = Web3.HTTPProvider(
                self.rpc_url,
                request_kwargs={
                    'timeout': 30,
                    'headers': {'Content-Type': 'application/json'}
                }
            )
            self.web3 = Web3(provider)
            self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)

            # Initialize account
            self.account = Account.from_key(self.private_key)
            if self.account.address.lower() != self.wallet_address.lower():
                raise AbstractWalletError("Private key does not match wallet address")

            # Validate connection through plugins
            for plugin in self.plugins:
                if not plugin.initialize():
                    logger.warning(f"Plugin initialization failed: {plugin.__class__.__name__}")

            logger.info(f"Successfully connected Abstract wallet: {self.wallet_address[:10]}...")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Abstract wallet: {str(e)}")
            raise AbstractWalletError(f"Connection failed: {str(e)}")

    async def get_balance(self, token_address: Optional[str] = None) -> float:
        """Get wallet balance for native or specific token with plugin support"""
        try:
            if not self.web3 or not self.web3.is_connected():
                await self.connect()

            if token_address:
                # Get ERC20 token balance
                contract = self.web3.eth.contract(
                    address=self.web3.to_checksum_address(token_address),
                    abi=[] # Add ERC20 ABI here
                )
                balance = contract.functions.balanceOf(self.wallet_address).call()
                decimals = contract.functions.decimals().call()
                return balance / (10 ** decimals)
            else:
                # Get native token balance
                balance = self.web3.eth.get_balance(self.wallet_address)
                return self.web3.from_wei(balance, 'ether')

        except Exception as e:
            logger.error(f"Failed to get balance: {str(e)}")
            return 0.0

    async def send_transaction(
        self, 
        to_address: str, 
        amount: float, 
        token_address: Optional[str] = None
    ) -> str:
        """Send transaction using Abstract wallet with plugin validation"""
        try:
            if not self.web3 or not self.web3.is_connected():
                await self.connect()

            nonce = self.web3.eth.get_transaction_count(self.wallet_address)

            if token_address:
                # ERC20 token transfer
                contract = self.web3.eth.contract(
                    address=self.web3.to_checksum_address(token_address),
                    abi=[] # Add ERC20 ABI here
                )
                decimals = contract.functions.decimals().call()
                amount_wei = int(amount * (10 ** decimals))

                tx = contract.functions.transfer(
                    to_address,
                    amount_wei
                ).build_transaction({
                    'from': self.wallet_address,
                    'nonce': nonce,
                    'gas': 100000,  # Estimate this
                    'gasPrice': self.web3.eth.gas_price
                })
            else:
                # Native token transfer
                tx = {
                    'nonce': nonce,
                    'to': to_address,
                    'value': self.web3.to_wei(amount, 'ether'),
                    'gas': 21000,
                    'gasPrice': self.web3.eth.gas_price
                }

            # Run transaction validation through plugins
            for plugin in self.plugins:
                if not plugin.validate_transaction(tx):
                    raise AbstractWalletError(f"Transaction validation failed by plugin: {plugin.__class__.__name__}")

            # Sign and send transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            return self.web3.to_hex(tx_hash)

        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}")
            raise AbstractWalletError(f"Transaction failed: {str(e)}")

    async def close(self):
        """Close the Abstract wallet connection"""
        if self.web3:
            self.web3 = None
            self.account = None
            logger.info("Abstract wallet connection closed")