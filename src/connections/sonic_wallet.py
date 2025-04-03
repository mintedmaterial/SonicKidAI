"""Sonic wallet connection implementation"""
import logging
import os
from typing import Optional, Dict, Any
from web3 import Web3
from web3.middleware import geth_poa_middleware
from dotenv import load_dotenv

from .errors import SonicConnectionError

logger = logging.getLogger("connections.sonic_wallet")

class SonicWalletConnection:
    """Manages Sonic network wallet connection and basic operations"""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Sonic wallet connection"""
        # Load environment variables
        load_dotenv()

        # Initialize configuration
        self.config = config or {}
        
        # Handle case where config is a string (RPC URL)
        if isinstance(config, str):
            self.rpc_url = config
            self.config = {'rpc_url': config}
        else:
            # Get primary RPC URL
            self.rpc_url = self.config.get('rpc_url', 'https://sonic-rpc.publicnode.com')
            
            # Get list of fallback RPC URLs
            self.rpc_urls = self.config.get('rpc_urls', [
                'https://sonic-rpc.publicnode.com',
                'https://rpc.soniclabs.com'
            ])
            
            # Make sure primary RPC is in the list if it's not already
            if self.rpc_url not in self.rpc_urls:
                self.rpc_urls.insert(0, self.rpc_url)
            
        self.chain_id = self.config.get('chain_id', 146)  # Sonic chain ID
        self._web3 = None
        self._account = None

        # Initialize connection
        self._initialize_web3()
        self._load_wallet()

    @property
    def web3(self) -> Web3:
        """Get Web3 instance with automatic initialization"""
        if not self._web3 or not self._web3.is_connected():
            self._initialize_web3()
        return self._web3

    def _initialize_web3(self):
        """Initialize Web3 connection with RPC fallback mechanism"""
        last_error = None
        
        # Try the primary URL first, then fallbacks if needed
        if hasattr(self, 'rpc_urls') and self.rpc_urls:
            rpc_list = self.rpc_urls
        else:
            # Fallback to using just the primary URL if rpc_urls not defined
            rpc_list = [self.rpc_url]
            
        for rpc_url in rpc_list:
            try:
                if not rpc_url:
                    continue
                    
                logger.info(f"Attempting to connect to RPC: {rpc_url}")
                
                # Create Web3 instance with timeout
                self._web3 = Web3(Web3.HTTPProvider(
                    rpc_url,
                    request_kwargs={'timeout': 20}  # Shorter timeout for faster failover
                ))

                # Add PoA middleware for Sonic network
                self._web3.middleware_onion.inject(geth_poa_middleware, layer=0)

                if not self._web3.is_connected():
                    logger.warning(f"Failed to connect to {rpc_url}")
                    continue

                # Verify chain ID
                connected_chain_id = self._web3.eth.chain_id
                if connected_chain_id != self.chain_id:
                    logger.warning(f"Wrong chain ID for {rpc_url}. Expected {self.chain_id}, got {connected_chain_id}")
                    continue

                # If we reached here, connection was successful
                logger.info(f"Successfully connected to Sonic network with RPC {rpc_url}, chain ID: {self.chain_id}")
                # Update the primary RPC URL to the one that worked
                self.rpc_url = rpc_url
                return
                
            except Exception as e:
                logger.warning(f"Failed to connect to {rpc_url}: {str(e)}")
                last_error = e
                continue
                
        # If we got here, all connection attempts failed
        error_msg = f"Failed to connect to any Sonic RPC endpoints. Last error: {str(last_error)}"
        logger.error(error_msg)
        raise SonicConnectionError(error_msg)

    def _load_wallet(self):
        """Load wallet from private key with validation"""
        try:
            private_key = os.getenv('WALLET_PRIVATE_KEY')

            if not private_key:
                raise SonicConnectionError("No wallet private key found in environment")

            if not private_key.startswith('0x'):
                private_key = f"0x{private_key}"

            self._account = self._web3.eth.account.from_key(private_key)
            logger.info(f"Wallet loaded with address: {self._account.address}")

        except Exception as e:
            logger.error(f"Failed to load wallet: {str(e)}")
            raise SonicConnectionError(f"Wallet loading failed: {str(e)}")

    def get_web3(self) -> Web3:
        """Get Web3 instance for contract interactions"""
        return self.web3

    def get_account(self):
        """Get account instance for transaction signing"""
        if not self._account:
            self._load_wallet()
        return self._account

    def get_contract(self, address: str, abi: list) -> Any:
        """Get contract instance with proper validation"""
        try:
            if not self.web3.is_address(address):
                raise ValueError(f"Invalid contract address: {address}")

            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(address),
                abi=abi
            )
            return contract

        except Exception as e:
            logger.error(f"Failed to get contract instance: {str(e)}")
            raise SonicConnectionError(f"Contract initialization failed: {str(e)}")

    async def get_balance(self, token_address: Optional[str] = None) -> float:
        """Get wallet balance with proper error handling"""
        try:
            if not self.web3.is_connected():
                self._initialize_web3()

            if token_address:
                # Get ERC20 token balance
                from .constants.abi import ERC20_ABI
                contract = self.get_contract(token_address, ERC20_ABI)
                balance = contract.functions.balanceOf(self._account.address).call()
                decimals = contract.functions.decimals().call()
                return balance / (10 ** decimals)
            else:
                # Get native token balance
                balance = self.web3.eth.get_balance(self._account.address)
                return self.web3.from_wei(balance, 'ether')

        except Exception as e:
            logger.error(f"Failed to get balance: {str(e)}")
            raise SonicConnectionError(f"Balance check failed: {str(e)}")

    def is_connected(self) -> bool:
        """Check if connection is active and valid"""
        try:
            return (
                self._web3 is not None and 
                self._web3.is_connected() and
                self._web3.eth.chain_id == self.chain_id
            )
        except Exception:
            return False

    async def connect(self):
        """Establish connection with retry logic"""
        try:
            if not self.is_connected():
                self._initialize_web3()
                self._load_wallet()
            return True
        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            raise SonicConnectionError(f"Connection failed: {str(e)}")

    async def close(self):
        """Clean up connection resources"""
        self._web3 = None
        self._account = None
        logger.info("Sonic wallet connection closed")