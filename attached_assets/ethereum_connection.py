import logging
import os
from typing import Dict, Any, Optional, Union
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import geth_poa_middleware
from src.constants.networks import EVM_NETWORKS
from src.constants.abi import ERC20_ABI
from src.connections.abstract_wallet import AbstractWallet, WalletPlugin
from src.constants.actions import Action, ActionParameter
import requests
import time
import asyncio


logger = logging.getLogger("connections.ethereum_connection")


class EthereumConnectionError(Exception):
    """Base exception for Ethereum connection errors"""
    pass


class EthereumGasPlugin(WalletPlugin):
    """Plugin for managing gas estimation and limits"""
    def initialize(self) -> bool:
        self.max_gas_price = self.config.get('max_gas_price', 100000000000)  # 100 gwei
        return True

    def validate_transaction(self, tx_data: Dict[str, Any]) -> bool:
        """Validate gas prices are within acceptable limits"""
        if tx_data.get('gasPrice', 0) > self.max_gas_price:
            logger.warning(f"Gas price exceeds maximum: {tx_data['gasPrice']}")
            return False
        return True


class EthereumConnection(AbstractWallet):
    def __init__(self, config: Dict[str, Any]):
        # Add gas plugin to config
        if 'plugins' not in config:
            config['plugins'] = []
        config['plugins'].append({
            'path': 'ethereum_connection.EthereumGasPlugin',
            'max_gas_price': config.get('max_gas_price', 100000000000)
        })

        super().__init__(config)
        self.NATIVE_TOKEN = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"

        # Get network configuration
        self.network = config.get("network", "ethereum")
        self.rpc_url = config.get("rpc") or EVM_NETWORKS[self.network]["rpc_url"]
        self.scanner_url = EVM_NETWORKS[self.network]["scanner_url"]
        self.chain_id = EVM_NETWORKS[self.network]["chain_id"]
        self._initialize_web3()

        # Kyberswap aggregator API for best swap routes
        self.aggregator_api = f"https://aggregator-api.kyberswap.com/{self.network}/api/v1"

    async def get_balance(self, token_address: Optional[str] = None) -> float:
        """Get balance and value for the configured wallet."""
        try:
            # Use parent class's get_balance method
            return await super().get_balance(token_address)
        except Exception as e:
            logger.error(f"Failed to get balance: {str(e)}")
            return 0.0

    def _get_explorer_link(self, tx_hash: str) -> str:
        """Generate block explorer link for transaction"""
        return f"https://{self.scanner_url}/tx/{tx_hash}"

    def get_token_by_ticker(self, ticker: str) -> Optional[str]:
        """Get token address by ticker symbol"""
        try:
            if ticker.lower() in ["eth", "ethereum"]:
                return f"Token: ETH\nAddress: {self.NATIVE_TOKEN}"

            address = self._get_token_address(ticker)
            if address:
                return f"Token: {ticker}\nAddress: {address}"
            return f"No token found for ticker: {ticker}"

        except Exception as error:
            logger.error(f"Failed to get token by ticker: {str(error)}")
            return None

    async def transfer(
        self,
        to_address: str,
        amount: float,
        token_address: Optional[str] = None
    ) -> str:
        """Transfer ETH or tokens with enhanced validation"""
        try:
            # Validate balance first
            current_balance = await self.get_balance(token_address=token_address)
            if current_balance < amount:
                raise ValueError(
                    f"Insufficient balance. Required: {amount}, Available: {current_balance}"
                )

            # Use abstract wallet's send_transaction with plugin validation
            tx_hash = await self.send_transaction(to_address, amount, token_address)

            # Return explorer link
            return self._get_explorer_link(tx_hash)

        except Exception as e:
            logger.error(f"Transfer failed: {str(e)}")
            raise

    def _get_token_address(self, ticker: str) -> Optional[str]:
        """Helper function to get token address from DEXScreener"""
        try:
            response = requests.get(
                f"https://api.dexscreener.com/latest/dex/search?q={ticker}"
            )
            response.raise_for_status()

            data = response.json()
            if not data.get('pairs'):
                return None

            # Filter pairs for Ethereum network
            eth_pairs = [
                pair for pair in data["pairs"]
                if pair.get("chainId", "").lower() == "ethereum"
            ]

            # Sort by liquidity/volume
            eth_pairs.sort(
                key=lambda x: float(x.get('liquidity', {}).get('usd', 0) or 0) *
                            float(x.get('volume', {}).get('h24', 0) or 0),
                reverse=True
            )

            # Find exact ticker match
            for pair in eth_pairs:
                base_token = pair.get("baseToken", {})
                if base_token.get("symbol", "").lower() == ticker.lower():
                    return base_token.get("address")

            return None

        except Exception as error:
            logger.error(f"Error fetching token address: {str(error)}")
            return None

    def register_actions(self) -> None:
        """Register available Ethereum actions"""
        self.actions = {
            "get-token-by-ticker": Action(
                name="get-token-by-ticker",
                parameters=[
                    ActionParameter("ticker", True, str, "Token ticker symbol to look up")
                ],
                description="Get token address by ticker symbol"
            ),
            "get-balance": Action(
                name="get-balance",
                parameters=[
                    ActionParameter("address", False, str, "Address to check balance for (optional)"),
                    ActionParameter("token_address", False, str, "Token address (optional, native token if not provided)")
                ],
                description="Get ETH or token balance"
            ),
            "transfer": Action(
                name="transfer",
                parameters=[
                    ActionParameter("to_address", True, str, "Recipient address"),
                    ActionParameter("amount", True, float, "Amount to transfer"),
                    ActionParameter("token_address", False, str, "Token address (optional, native token if not provided)")
                ],
                description="Send ETH or tokens"
            ),
            "get-address": Action(
                name="get-address",
                parameters=[],
                description="Get your Ethereum wallet address"
            ),
            "swap": Action(
                name="swap",
                parameters=[
                    ActionParameter("token_in", True, str, "Input token address"),
                    ActionParameter("token_out", True, str, "Output token address"),
                    ActionParameter("amount", True, float, "Amount to swap"),
                    ActionParameter("slippage", False, float, "Max slippage percentage (default 0.5%)")
                ],
                description="Swap tokens using Kyberswap aggregator"
            )
        }

    def configure(self) -> bool:
        """Sets up Ethereum wallet and API credentials"""
        logger.info("\n⛓️ ETHEREUM SETUP")

        if self.is_configured():
            logger.info("Ethereum connection is already configured")
            response = input("Do you want to reconfigure? (y/n): ")
            if response.lower() != 'y':
                return True

        try:
            if not os.path.exists('.env'):
                with open('.env', 'w') as f:
                    f.write('')

            # Get wallet private key
            private_key = input("\nEnter your wallet private key: ")
            if not private_key.startswith('0x'):
                private_key = '0x' + private_key

            # Validate private key format
            if len(private_key) != 66 or not all(c in '0123456789abcdefABCDEF' for c in private_key[2:]):
                raise ValueError("Invalid private key format")

            # Test private key by deriving address
            account = self._web3.eth.account.from_key(private_key)
            logger.info(f"\nDerived address: {account.address}")

            # Get optional block explorer API key
            explorer_key = input("\nEnter your block explorer API key (optional, press Enter to skip): ")

            # Save credentials
            set_key('.env', 'ETH_PRIVATE_KEY', private_key)
            if explorer_key:
                set_key('.env', f'ETH_EXPLORER_KEY', explorer_key)

            logger.info("\n✅ Ethereum configuration saved successfully!")
            return True

        except Exception as e:
            logger.error(f"Configuration failed: {str(e)}")
            return False

    def is_configured(self, verbose: bool = False) -> bool:
        """Check if Ethereum connection is properly configured"""
        try:
            load_dotenv()

            # Check private key exists
            private_key = os.getenv('ETH_PRIVATE_KEY')
            if not private_key:
                if verbose:
                    logger.error("Missing ETH_PRIVATE_KEY in .env")
                return False

            # Validate Web3 connection
            if not self._web3 or not self._web3.is_connected():
                if verbose:
                    logger.error("Not connected to Ethereum network")
                return False

            # Test account access
            account = self._web3.eth.account.from_key(private_key)
            balance = self._web3.eth.get_balance(account.address)

            return True

        except Exception as e:
            if verbose:
                logger.error(f"Configuration check failed: {str(e)}")
            return False

    def get_address(self) -> str:
        try:
            private_key = os.getenv('ETH_PRIVATE_KEY')
            account = self._web3.eth.account.from_key(private_key)
            return f"Your Ethereum address: {account.address}"
        except Exception as e:
            return f"Failed to get address: {str(e)}"

    def _initialize_web3(self) -> None:
        """Initialize Web3 connection with retry logic"""
        if not self._web3:
            for attempt in range(3):
                try:
                    self._web3 = Web3(Web3.HTTPProvider(self.rpc_url))
                    self._web3.middleware_onion.inject(geth_poa_middleware, layer=0)

                    if not self._web3.is_connected():
                        raise EthereumConnectionError("Failed to connect to Ethereum network")

                    chain_id = self._web3.eth.chain_id
                    if chain_id != self.chain_id:
                        raise EthereumConnectionError(f"Connected to wrong chain. Expected {self.chain_id}, got {chain_id}")

                    logger.info(f"Connected to Ethereum network with chain ID: {chain_id}")
                    break

                except Exception as e:
                    if attempt == 2:
                        raise EthereumConnectionError(f"Failed to initialize Web3 after 3 attempts: {str(e)}")
                    logger.warning(f"Web3 initialization attempt {attempt + 1} failed: {str(e)}")


    @property
    def is_llm_provider(self) -> bool:
        return False

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Ethereum configuration from JSON"""
        if "rpc" not in config and "network" not in config:
            raise ValueError("Config must contain either 'rpc' or 'network'")
        return config

    async def swap(
        self,
        token_in: str,
        token_out: str,
        amount: float,
        slippage: float = 0.5
    ) -> str:
        """Execute token swap using Kyberswap aggregator"""
        try:
            private_key = os.getenv('ETH_PRIVATE_KEY')
            account = self._web3.eth.account.from_key(private_key)

            # Validate balance
            current_balance = await self.get_balance(
                token_address=None if token_in.lower() == self.NATIVE_TOKEN.lower() else token_in
            )
            if current_balance < amount:
                raise ValueError(f"Insufficient balance. Required: {amount}, Available: {current_balance}")

            # Get optimal swap route
            route_data = await self._get_swap_route(
                token_in,
                token_out,
                amount,
                account.address
            )

            # Handle token approval if needed
            if token_in.lower() != self.NATIVE_TOKEN.lower():
                router_address = route_data["routerAddress"]

                if token_in.lower() == "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2".lower():  # WETH
                    amount_raw = self._web3.to_wei(amount, 'ether')
                else:
                    token_contract = self._web3.eth.contract(
                        address=Web3.to_checksum_address(token_in),
                        abi=ERC20_ABI
                    )
                    decimals = token_contract.functions.decimals().call()
                    amount_raw = int(amount * (10 ** decimals))

                approval_hash = await self._handle_token_approval(token_in, router_address, amount_raw)
                if approval_hash:
                    logger.info(f"Token approval transaction: {self._get_explorer_link(approval_hash)}")

            # Build and send swap transaction
            swap_tx = await self._build_swap_tx(token_in, token_out, amount, slippage, route_data)
            signed_tx = account.sign_transaction(swap_tx)
            tx_hash = self._web3.eth.send_raw_transaction(signed_tx.rawTransaction)

            tx_url = self._get_explorer_link(tx_hash.hex())

            return (f"Swap transaction sent!(allow time for scanner to populate it):\n"
                    f"Transaction: {tx_url}")

        except Exception as e:
            return f"Swap failed: {str(e)}"


    async def perform_action(self, action_name: str, kwargs: Dict[str, Any]) -> Any:
        """Execute an Ethereum action with validation"""
        if action_name not in self.actions:
            raise KeyError(f"Unknown action: {action_name}")

        load_dotenv()

        if not self.is_configured(verbose=True):
            raise EthereumConnectionError("Ethereum connection is not properly configured")

        action = self.actions[action_name]
        errors = action.validate_params(kwargs)
        if errors:
            raise ValueError(f"Invalid parameters: {', '.join(errors)}")

        method_name = action_name.replace('-', '_')
        method = getattr(self, method_name)
        return await method(**kwargs) # Make it async

    async def _get_swap_route(
        self,
        token_in: str,
        token_out: str,
        amount: float,
        sender: str
    ) -> Dict:
        """Get optimal swap route from Kyberswap API"""
        try:
            url = f"{self.aggregator_api}/routes"

            # Convert amount to raw value with proper decimals
            if token_in.lower() == self.NATIVE_TOKEN.lower():
                amount_raw = self._web3.to_wei(amount, 'ether')
            else:
                token_contract = self._web3.eth.contract(
                    address=Web3.to_checksum_address(token_in),
                    abi=ERC20_ABI
                )
                decimals = token_contract.functions.decimals().call()
                amount_raw = int(amount * (10 ** decimals))

            # Prepare API request
            headers = {"x-client-id": "zerepy"}
            params = {
                "tokenIn": token_in,
                "tokenOut": token_out,
                "amountIn": str(amount_raw),
                "to": sender,
                "gasInclude": "true"
            }

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            if data.get("code") != 0:
                raise ValueError(f"API error: {data.get('message')}")

            return data["data"]

        except Exception as e:
            logger.error(f"Failed to get swap route: {str(e)}")
            raise

    async def _build_swap_tx(
        self,
        token_in: str,
        token_out: str,
        amount: float,
        slippage: float,
        route_data: Dict
    ) -> Dict[str, Any]:
        """Build swap transaction using route data"""
        try:
            private_key = os.getenv('ETH_PRIVATE_KEY')
            account = self._web3.eth.account.from_key(private_key)

            url = f"{self.aggregator_api}/route/build"
            headers = {"x-client-id": "zerepy"}

            payload = {
                "routeSummary": route_data["routeSummary"],
                "sender": account.address,
                "recipient": account.address,
                "slippageTolerance": int(slippage * 100),  # Convert to bps
                "deadline": int(time.time() + 1200),  # 20 minutes
                "source": "zerepy"
            }

            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()

            data = response.json()
            if data.get("code") != 0:
                raise ValueError(f"API error: {data.get('message')}")

            # Prepare transaction parameters
            tx = {
                'from': account.address,
                'to': Web3.to_checksum_address(route_data["routerAddress"]),
                'data': data["data"]["data"],
                'value': self._web3.to_wei(amount, 'ether') if token_in.lower() == self.NATIVE_TOKEN.lower() else 0,
                'nonce': self._web3.eth.get_transaction_count(account.address),
                'gasPrice': self._web3.eth.gas_price,
                'chainId': self.chain_id
            }

            # Estimate gas
            try:
                gas_estimate = self._web3.eth.estimate_gas(tx)
                tx['gas'] = int(gas_estimate * 1.2)  # Add 20% buffer
            except Exception as e:
                logger.warning(f"Gas estimation failed: {e}, using default gas limit")
                tx['gas'] = 500000  # Default gas limit for swaps

            return tx

        except Exception as e:
            logger.error(f"Failed to build swap transaction: {str(e)}")
            raise

    async def _handle_token_approval(
        self,
        token_address: str,
        spender_address: str,
        amount: int
    ) -> Optional[str]:
        """Handle token approval for spender, returns tx hash if approval needed"""
        try:
            private_key = os.getenv('ETH_PRIVATE_KEY')
            account = self._web3.eth.account.from_key(private_key)

            token_contract = self._web3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )

            # Check current allowance
            current_allowance = token_contract.functions.allowance(
                account.address,
                spender_address
            ).call()

            if current_allowance < amount:
                # Prepare approval transaction
                approve_tx = token_contract.functions.approve(
                    spender_address,
                    amount
                ).build_transaction({
                    'from': account.address,
                    'nonce': self._web3.eth.get_transaction_count(account.address),
                    'gasPrice': self._web3.eth.gas_price,
                    'chainId': self.chain_id
                })

                # Estimate gas for approval
                try:
                    gas_estimate = self._web3.eth.estimate_gas(approve_tx)
                    approve_tx['gas'] = int(gas_estimate * 1.1)  # Add 10% buffer
                except Exception as e:
                    logger.warning(f"Approval gas estimation failed: {e}, using default")
                    approve_tx['gas'] = 100000  # Default gas for approvals

                # Sign and send approval transaction
                signed_approve = account.sign_transaction(approve_tx)
                tx_hash = self._web3.eth.send_raw_transaction(signed_approve.rawTransaction)

                # Wait for approval to be mined
                receipt = self._web3.eth.wait_for_transaction_receipt(tx_hash)
                if receipt['status'] != 1:
                    raise ValueError("Token approval failed")

                return tx_hash.hex()

            return None

        except Exception as e:
            logger.error(f"Token approval failed: {str(e)}")
            raise

def set_key(filepath, key, value):
    with open(filepath, 'r+') as f:
        lines = f.readlines()
        f.seek(0)
        for line in lines:
            if line.startswith(key + '='):
                f.write(f'{key}={value}\n')
                break
        else:
            f.write(f'{key}={value}\n')
        f.truncate()