"""OpenOcean API connection handler"""
import logging
import os
import json
import time
from typing import Dict, Any, Optional, List, Tuple, Union, cast
import aiohttp
import asyncio
from web3 import Web3
from web3.contract import Contract

logger = logging.getLogger(__name__)

# ERC20 ABI for token approval functions
ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

class OpenOceanConnection:
    """Connection handler for OpenOcean API"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize OpenOcean connection

        Args:
            config: Configuration dictionary containing:
                - chain_id: Chain ID (default: 1 for Ethereum)
                - slippage: Default slippage percentage (default: 1%)
                - referrer: Optional referrer address for fee sharing
                - referrer_fee: Optional referrer fee percentage (0.01-3)
                - use_pro_api: Whether to use Pro API (default: True)
                - api_key: OpenOcean Pro API key (can also be set via OPENOCEAN_API_KEY env var)
        """
        self.chain_id = config.get('chain_id', '1')  # Default to Ethereum
        self.chain_name = self._get_chain_name(self.chain_id)
        self.use_pro_api = config.get('use_pro_api', True)  # Default to Pro API
        
        # Set base URL based on Pro API setting
        if self.use_pro_api:
            self.base_url = "https://open-api-pro.openocean.finance/v4"
            self.api_key = config.get('api_key', os.getenv('OPENOCEAN_API_KEY', 'mNhHD7nFNkCHGevafz40BQc1dX9AzxkH'))
        else:
            self.base_url = "https://open-api.openocean.finance/v4"
            self.api_key = None
            
        self._session: Optional[aiohttp.ClientSession] = None
        self.min_interval = 1  # 1 second between requests
        self._last_request = 0
        self.slippage = config.get('slippage', 1)  # Default 1% slippage
        self.referrer = config.get('referrer', None)
        self.referrer_fee = config.get('referrer_fee', None)
        
        logger.info(f"Initialized OpenOcean connection for chain {self.chain_name} (ID: {self.chain_id})")
    
    def _get_chain_name(self, chain_id: str) -> str:
        """Convert chain ID to chain name for OpenOcean API"""
        chain_map = {
            '1': 'eth',      # Ethereum
            '56': 'bsc',     # Binance Smart Chain
            '137': 'polygon', # Polygon
            '42161': 'arbitrum', # Arbitrum
            '10': 'optimism', # Optimism
            '43114': 'avax',  # Avalanche
            '250': 'fantom',  # Fantom
            '146': 'sonic',   # Sonic - Use "sonic" as chain name (not chain ID)
            # Add more chains as needed
        }
        
        # Convert numeric chain_id to string if needed
        if isinstance(chain_id, int):
            chain_id = str(chain_id)
            
        logger.debug(f"Mapping chain ID {chain_id} to OpenOcean chain name")
        return chain_map.get(chain_id, 'eth')
    
    async def connect(self, verbose: bool = False) -> bool:
        """Establish connection and verify API access
        
        Args:
            verbose: Whether to print token list details (default: False)
            
        Returns:
            True if connected successfully, False otherwise
        """
        try:
            self._session = aiohttp.ClientSession()
            # Test connection by getting token list (non-verbose mode)
            test_response = await self.get_token_list(verbose=verbose)
            if test_response:
                logger.info(f"Successfully connected to OpenOcean API for {self.chain_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to connect to OpenOcean API: {str(e)}")
            return False
    
    async def close(self) -> None:
        """Close the connection"""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Make a request to the OpenOcean API with rate limiting
        
        Args:
            endpoint: API endpoint to call
            params: Query parameters
            
        Returns:
            Response data or None if the request failed
        """
        if not self._session:
            logger.error("Connection not established. Call connect() first.")
            return None
        
        # Apply rate limiting
        now = time.time()
        if now - self._last_request < self.min_interval:
            await asyncio.sleep(self.min_interval - (now - self._last_request))
        self._last_request = time.time()
        
        try:
            url = f"{self.base_url}/{self.chain_name}/{endpoint}"
            logger.info(f"Making request to OpenOcean API: {url}")
            logger.info(f"Request parameters: {json.dumps(params, indent=2) if params else 'None'}")
            
            # Set up headers with API key if using Pro API
            headers = {}
            if self.use_pro_api and self.api_key:
                headers['apikey'] = self.api_key
                headers['Content-Type'] = 'application/json'
                logger.info("Using OpenOcean Pro API with API key")
            
            # Make the request with appropriate headers
            async with self._session.get(url, params=params, headers=headers, timeout=30) as response:
                response_text = await response.text()
                
                if response.status != 200:
                    logger.error(f"OpenOcean API request failed with status {response.status}: {response_text}")
                    logger.error(f"Request URL: {url}")
                    logger.error(f"Headers: {dict(response.headers)}")
                    return None
                
                try:
                    data = json.loads(response_text)
                    
                    # For large responses like token lists, only log summary
                    if endpoint == 'tokenList' and 'data' in data and isinstance(data['data'], list):
                        token_count = len(data['data'])
                        logger.info(f"OpenOcean API response: Retrieved {token_count} tokens")
                        logger.debug(f"Full token list: {json.dumps(data, indent=2)}")
                    else:
                        # For other responses, log the full response but with a size limit
                        response_str = json.dumps(data, indent=2)
                        if len(response_str) > 500:  # If response is very large
                            logger.info(f"OpenOcean API response: {response_str[:500]}... (truncated)")
                            logger.debug(f"Full response: {response_str}")
                        else:
                            logger.info(f"OpenOcean API response: {response_str}")
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse OpenOcean API response as JSON: {response_text}")
                    return None
                
                if data.get('code') != 200:
                    logger.error(f"OpenOcean API returned error code: {data.get('code')}")
                    logger.error(f"Error response: {data}")
                    if data.get('message'):
                        logger.error(f"Error message: {data.get('message')}")
                    if data.get('error'):
                        logger.error(f"Error details: {data.get('error')}")
                    return None
                
                # Check if data structure is valid
                if 'data' not in data:
                    # For some endpoints (like quote), a success code without data field
                    # might be a legitimate empty response indicating no available route
                    if endpoint in ['quote', 'swap'] and data.get('code') == 200:
                        logger.warning(f"OpenOcean API returned success code but no data field for {endpoint}: {data}")
                        # Return empty dict to indicate success but no route available
                        return {}
                    elif data.get('code') == 200:
                        # Some endpoints may return just a success code when operation succeeded
                        logger.info(f"OpenOcean API returned success code for {endpoint} without data field")
                        return {}
                    elif data.get('code') in [400, 404, 500] and endpoint in ['quote', 'swap']:
                        # Error codes for these endpoints might mean no route available
                        logger.warning(f"OpenOcean API returned error code {data.get('code')} for {endpoint} - likely no route available: {data}")
                        return {}
                    else:
                        logger.error(f"OpenOcean API response missing 'data' field: {data}")
                        return None
                
                return data.get('data')
        except aiohttp.ClientError as e:
            logger.error(f"OpenOcean API connection error for {url}: {str(e)}")
            return None
        except asyncio.TimeoutError:
            logger.error(f"OpenOcean API request timed out for {url}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error making request to OpenOcean API ({endpoint}): {str(e)}")
            return None
    
    async def get_token_list(self, verbose: bool = False) -> Optional[List[Dict[str, Any]]]:
        """Get list of supported tokens for the current chain
        
        Args:
            verbose: Whether to print token list details (default: False)
            
        Returns:
            List of token data or None if the request failed
        """
        # Store original log level
        original_level = logger.level
        
        try:
            # If not verbose, temporarily increase log level to reduce output
            if not verbose:
                logger.setLevel(logging.WARNING)
            
            # Make the request
            return await self._make_request('tokenList')
        finally:
            # Restore original log level
            logger.setLevel(original_level)
    
    async def get_token_by_symbol(self, symbol: str, verbose: bool = False) -> Optional[Dict[str, Any]]:
        """Get token details by symbol
        
        Args:
            symbol: Token symbol (e.g., 'ETH', 'USDC')
            verbose: Whether to print token list details (default: False)
            
        Returns:
            Token data or None if not found
        """
        tokens = await self.get_token_list(verbose=verbose)
        if not tokens:
            return None
        
        # Find token by symbol (case-insensitive)
        for token in tokens:
            if token.get('symbol', '').lower() == symbol.lower():
                return token
        
        logger.warning(f"Token with symbol {symbol} not found")
        return None
    
    async def get_dex_list(self) -> Optional[List[Dict[str, Any]]]:
        """Get list of supported DEXes for the current chain
        
        Returns:
            List of DEX data or None if the request failed
        """
        return await self._make_request('dexList')
    
    async def get_quote(self, 
                       in_token_address: str, 
                       out_token_address: str, 
                       amount: str,
                       gas_price: str = None,
                       disabled_dex_ids: List[str] = None,
                       enabled_dex_ids: List[str] = None) -> Optional[Dict[str, Any]]:
        """Get a swap quote without executing the swap
        
        Args:
            in_token_address: Input token address
            out_token_address: Output token address
            amount: Token amount (without decimals)
            gas_price: Gas price in GWEI (without decimals)
            disabled_dex_ids: List of DEX IDs to disable
            enabled_dex_ids: List of DEX IDs to enable (higher priority than disabled)
            
        Returns:
            Quote data or None if the request failed
        """
        # Set default gas price to 1 to match the working direct test
        default_gas_price = "1"
        
        params = {
            'inTokenAddress': in_token_address,
            'outTokenAddress': out_token_address,
            'amount': amount,
            'gasPrice': gas_price if gas_price is not None else default_gas_price,
            'slippage': str(self.slippage)  # Add slippage parameter which is required 
        }
        
        if disabled_dex_ids:
            params['disabledDexIds'] = ','.join(disabled_dex_ids)
            
        if enabled_dex_ids:
            params['enabledDexIds'] = ','.join(enabled_dex_ids)
        
        # Make direct request to ensure we get the proper response including the 'data' field
        if not self._session:
            logger.error("Connection not established. Call connect() first.")
            return None
            
        url = f"{self.base_url}/{self.chain_name}/quote"
        headers = {}
        if self.use_pro_api and self.api_key:
            headers['apikey'] = self.api_key
            headers['Content-Type'] = 'application/json'
        
        logger.info(f"Making direct quote request to: {url}")
        logger.info(f"Request parameters: {json.dumps(params, indent=2)}")
        
        try:
            # Apply rate limiting
            now = time.time()
            if now - self._last_request < self.min_interval:
                await asyncio.sleep(self.min_interval - (now - self._last_request))
            self._last_request = time.time()
            
            async with self._session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"OpenOcean API quote request failed with status {response.status}")
                    return None
                
                full_response = await response.json()
                logger.info(f"OpenOcean API response (truncated): {json.dumps(full_response)[:200]}...")
                
                if full_response.get('code') != 200:
                    logger.error(f"OpenOcean API returned error code: {full_response.get('code')}")
                    return None
                
                # Extract the data field which contains the quote information
                if 'data' in full_response and isinstance(full_response['data'], dict):
                    quote_data = full_response['data']
                    return quote_data
                else:
                    logger.warning(f"No quote data found in response!")
                    return None
                
        except Exception as e:
            logger.error(f"Error making quote request: {str(e)}")
            return None
    
    async def get_swap_transaction(self,
                                 in_token_address: str,
                                 out_token_address: str,
                                 amount: str,
                                 account: str,
                                 slippage: float = None,
                                 gas_price: str = None,
                                 referrer: str = None,
                                 referrer_fee: float = None,
                                 enabled_dex_ids: List[str] = None) -> Optional[Dict[str, Any]]:
        """Get a swap transaction data
        
        Args:
            in_token_address: Input token address
            out_token_address: Output token address
            amount: Token amount (without decimals)
            account: User's wallet address
            slippage: Slippage percentage (0.05-50)
            gas_price: Gas price in GWEI (without decimals)
            referrer: Referrer address for fee sharing
            referrer_fee: Referrer fee percentage (0.01-3)
            enabled_dex_ids: List of DEX IDs to enable
            
        Returns:
            Swap transaction data or None if the request failed
        """
        # Set default gas price to 1 to match the working direct test
        default_gas_price = "1"
        
        params = {
            'inTokenAddress': in_token_address,
            'outTokenAddress': out_token_address,
            'amount': amount,
            'account': account,
            'slippage': str(slippage) if slippage is not None else str(self.slippage),
            'gasPrice': gas_price if gas_price is not None else default_gas_price,
        }
        
        if referrer or self.referrer:
            params['referrer'] = referrer or self.referrer
            
        if (referrer_fee or self.referrer_fee) and (referrer or self.referrer):
            params['referrerFee'] = referrer_fee or self.referrer_fee
            
        if enabled_dex_ids:
            params['enabledDexIds'] = ','.join(enabled_dex_ids)
            
        # Make direct request to ensure we get the proper response including the 'data' field
        if not self._session:
            logger.error("Connection not established. Call connect() first.")
            return None
            
        url = f"{self.base_url}/{self.chain_name}/swap"
        headers = {}
        if self.use_pro_api and self.api_key:
            headers['apikey'] = self.api_key
            headers['Content-Type'] = 'application/json'
        
        logger.info(f"Making direct swap request to: {url}")
        logger.info(f"Request parameters: {json.dumps(params, indent=2)}")
        
        try:
            # Apply rate limiting
            now = time.time()
            if now - self._last_request < self.min_interval:
                await asyncio.sleep(self.min_interval - (now - self._last_request))
            self._last_request = time.time()
            
            async with self._session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"OpenOcean API swap request failed with status {response.status}")
                    return None
                
                full_response = await response.json()
                logger.info(f"OpenOcean API response (truncated): {json.dumps(full_response)[:200]}...")
                
                if full_response.get('code') != 200:
                    logger.error(f"OpenOcean API returned error code: {full_response.get('code')}")
                    return None
                
                # Extract the data field which contains the swap information
                if 'data' in full_response and isinstance(full_response['data'], dict):
                    swap_data = full_response['data']
                    # Verify the correct router address
                    router = swap_data.get('to', '')
                    logger.info(f"Swap will use router: {router}")
                    return swap_data
                else:
                    logger.warning(f"No swap data found in response!")
                    return None
                
        except Exception as e:
            logger.error(f"Error making swap request: {str(e)}")
            return None
    
    async def check_token_allowance_direct(self,
                                     token_address: str,
                                     owner_address: str) -> Optional[Dict[str, Any]]:
        """Check token allowance using OpenOcean's allowance API endpoint
        
        Args:
            token_address: Token contract address
            owner_address: Token owner address
            
        Returns:
            Dictionary with allowance information or None if check failed
        """
        try:
            # Build API endpoint for allowance check
            chain_name = self._get_chain_name(self.chain_id)
            endpoint = f"allowance"
            
            # Set up parameters
            params = {
                "inTokenAddress": token_address,
                "account": owner_address
            }
            
            # Make request to allowance endpoint
            logger.info(f"Checking allowance for token {token_address}, account {owner_address}")
            
            # Get the full response including code and data fields
            if not self._session:
                logger.error("Connection not established. Call connect() first.")
                return None
                
            url = f"{self.base_url}/{self.chain_name}/{endpoint}"
            headers = {}
            if self.use_pro_api and self.api_key:
                headers['apikey'] = self.api_key
                headers['Content-Type'] = 'application/json'
            
            try:
                async with self._session.get(url, params=params, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"OpenOcean API allowance request failed with status {response.status}")
                        return None
                    
                    full_response = await response.json()
                    
                    if full_response.get('code') != 200:
                        logger.error(f"OpenOcean API returned error code: {full_response.get('code')}")
                        return None
                    
                    # Extract the data field which contains the allowance information
                    if 'data' in full_response and isinstance(full_response['data'], list) and len(full_response['data']) > 0:
                        allowance_info = full_response['data'][0]
                        logger.info(f"Allowance info for token {token_address}: {allowance_info}")
                        return allowance_info
                        
                    # Default to zero allowance if we couldn't find data
                    logger.warning(f"No allowance data found in response: {full_response}")
                    return {"allowance": "0", "raw": "0"}
                    
            except Exception as e:
                logger.error(f"Error making allowance API request: {str(e)}")
                return None
                
        except Exception as e:
            logger.error(f"Error checking token allowance via API: {str(e)}")
            return None
            
    async def check_token_allowance(self,
                               token_address: str,
                               owner_address: str,
                               spender_address: str,
                               rpc_url: str = None) -> Optional[int]:
        """Check token allowance for a specific spender
        
        Args:
            token_address: Token contract address
            owner_address: Token owner address
            spender_address: Address of the spender (router contract)
            rpc_url: RPC URL for the chain (optional, defaults to env var)
            
        Returns:
            Current allowance as an integer or None if check failed
        """
        try:
            # First try to use the direct API method
            allowance_info = await self.check_token_allowance_direct(token_address, owner_address)
            if allowance_info and "raw" in allowance_info:
                return int(allowance_info["raw"])
                
            # Fall back to using web3 if direct API method fails
            # Get RPC URL for the chain if not provided
            if not rpc_url:
                rpc_url = os.getenv(f"WEB3_RPC_URL_{self.chain_id}", os.getenv("WEB3_RPC_URL", ""))
                if not rpc_url:
                    logger.error(f"No RPC URL configured for chain ID {self.chain_id}")
                    return None
            
            # Create Web3 instance
            web3 = Web3(Web3.HTTPProvider(rpc_url))
            if not web3.is_connected():
                logger.error(f"Failed to connect to node at {rpc_url}")
                return None
            
            # Create token contract instance
            token_contract = web3.eth.contract(
                address=Web3.to_checksum_address(token_address), 
                abi=ERC20_ABI
            )
            
            # Check allowance
            allowance = token_contract.functions.allowance(
                Web3.to_checksum_address(owner_address),
                Web3.to_checksum_address(spender_address)
            ).call()
            
            logger.info(f"Current allowance for {token_address}: {allowance}")
            return allowance
        
        except Exception as e:
            logger.error(f"Error checking token allowance: {str(e)}")
            return None
    
    async def check_and_create_approval_transaction(self,
                                               swap_data: Dict[str, Any],
                                               owner_address: str,
                                               amount_to_approve: str = "max") -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if token approval is needed and create approval transaction
        
        Args:
            swap_data: Swap transaction data from get_swap_transaction
            owner_address: Token owner address
            amount_to_approve: Amount to approve ("max" for unlimited approval, or a specific amount)
            
        Returns:
            Tuple of (needs_approval, approval_tx_data)
        """
        try:
            # Extract necessary information from swap data
            if not swap_data or not isinstance(swap_data, dict):
                logger.error("Invalid swap data provided")
                return False, None
            
            # Get router address (the contract that will execute the swap)
            router_address = swap_data.get("to", "")
            if not router_address:
                logger.error("Router address not found in swap data")
                return False, None
            
            in_token = swap_data.get("inToken", {})
            if not in_token or not isinstance(in_token, dict):
                logger.error("Input token information not found in swap data")
                return False, None
            
            token_address = in_token.get("address", "")
            if not token_address:
                logger.error("Input token address not found in swap data")
                return False, None
            
            # Get the amount needed for the swap
            amount_needed = swap_data.get("inAmount", "0")
            
            # Check current allowance
            current_allowance = await self.check_token_allowance(
                token_address=token_address,
                owner_address=owner_address,
                spender_address=router_address
            )
            
            if current_allowance is None:
                logger.error("Failed to check token allowance")
                return True, None  # Assume approval is needed to be safe
            
            # Check if we need approval
            amount_needed_int = int(amount_needed)
            if current_allowance >= amount_needed_int:
                logger.info(f"Allowance {current_allowance} is sufficient for amount {amount_needed_int}")
                return False, None
            
            logger.info(f"Allowance {current_allowance} is insufficient for amount {amount_needed_int}, approval needed")
            
            # Create approval transaction
            # Get RPC URL for the chain
            rpc_url = os.getenv(f"WEB3_RPC_URL_{self.chain_id}", os.getenv("WEB3_RPC_URL", ""))
            if not rpc_url:
                logger.error(f"No RPC URL configured for chain ID {self.chain_id}")
                return True, None
            
            # Create Web3 instance
            web3 = Web3(Web3.HTTPProvider(rpc_url))
            if not web3.is_connected():
                logger.error(f"Failed to connect to node at {rpc_url}")
                return True, None
            
            # Create token contract instance
            token_contract = web3.eth.contract(
                address=Web3.to_checksum_address(token_address), 
                abi=ERC20_ABI
            )
            
            # Determine approval amount
            if amount_to_approve == "max":
                # Max uint256 value for unlimited approval
                approval_amount = 2**256 - 1
            else:
                approval_amount = int(amount_to_approve)
            
            # Create approval transaction
            approval_data = token_contract.functions.approve(
                Web3.to_checksum_address(router_address),
                approval_amount
            ).build_transaction({
                'from': Web3.to_checksum_address(owner_address),
                'nonce': web3.eth.get_transaction_count(Web3.to_checksum_address(owner_address)),
                'gas': 60000,  # Standard gas limit for approve
                'gasPrice': web3.eth.gas_price,
                'chainId': int(self.chain_id)
            })
            
            return True, approval_data
            
        except Exception as e:
            logger.error(f"Error creating approval transaction: {str(e)}")
            return True, None  # Assume approval is needed to be safe
    
    async def execute_approval_transaction(self,
                                       token_address: str,
                                       spender_address: str,
                                       private_key: str,
                                       amount: str = "max",
                                       gas_price: str = None) -> Optional[Dict[str, Any]]:
        """Execute a token approval transaction
        
        Args:
            token_address: Token contract address
            spender_address: Address of the spender (router contract)
            private_key: Private key for signing transaction
            amount: Amount to approve ("max" for unlimited approval, or a specific amount)
            gas_price: Gas price in GWEI (without decimals)
            
        Returns:
            Transaction data or None if the approval failed
        """
        try:
            # Get RPC URL for the chain
            rpc_url = os.getenv(f"WEB3_RPC_URL_{self.chain_id}", os.getenv("WEB3_RPC_URL", ""))
            if not rpc_url:
                logger.error(f"No RPC URL configured for chain ID {self.chain_id}")
                return None
            
            # Create Web3 instance
            web3 = Web3(Web3.HTTPProvider(rpc_url))
            if not web3.is_connected():
                logger.error(f"Failed to connect to node at {rpc_url}")
                return None
            
            # Create account from private key
            account = web3.eth.account.from_key(private_key)
            owner_address = account.address
            
            # Create token contract instance
            token_contract = web3.eth.contract(
                address=Web3.to_checksum_address(token_address), 
                abi=ERC20_ABI
            )
            
            # Determine approval amount
            if amount == "max":
                # Max uint256 value for unlimited approval
                approval_amount = 2**256 - 1
            else:
                approval_amount = int(amount)
            
            # Determine gas price
            gas_price_wei = None
            if gas_price:
                gas_price_wei = web3.to_wei(gas_price, 'gwei')
            else:
                gas_price_wei = web3.eth.gas_price
            
            # Create approval transaction
            tx = token_contract.functions.approve(
                Web3.to_checksum_address(spender_address),
                approval_amount
            ).build_transaction({
                'from': Web3.to_checksum_address(owner_address),
                'nonce': web3.eth.get_transaction_count(Web3.to_checksum_address(owner_address)),
                'gas': 60000,  # Standard gas limit for approve
                'gasPrice': gas_price_wei,
                'chainId': int(self.chain_id)
            })
            
            # Sign and send transaction
            signed_tx = account.sign_transaction(tx)
            tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for transaction receipt
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            
            result = {
                'success': receipt['status'] == 1,
                'tx_hash': web3.to_hex(tx_hash),
                'explorer_url': self._get_explorer_url(web3.to_hex(tx_hash)),
                'gas_used': receipt['gasUsed'],
                'token_address': token_address,
                'spender_address': spender_address,
                'approval_amount': str(approval_amount)
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Error executing approval transaction: {str(e)}")
            return None
    
    async def execute_swap(self,
                         in_token_address: str,
                         out_token_address: str,
                         amount: str,
                         private_key: str,
                         slippage: float = None,
                         gas_price: str = None,
                         referrer: str = None,
                         referrer_fee: float = None,
                         check_allowance: bool = True,
                         auto_approve: bool = True) -> Optional[Dict[str, Any]]:
        """Execute a token swap using the OpenOcean API
        
        Args:
            in_token_address: Input token address
            out_token_address: Output token address
            amount: Token amount (without decimals)
            private_key: Private key for signing transaction
            slippage: Slippage percentage (0.05-50)
            gas_price: Gas price in GWEI (without decimals)
            referrer: Referrer address for fee sharing
            referrer_fee: Referrer fee percentage (0.01-3)
            check_allowance: Whether to check if token approval is needed
            auto_approve: Whether to automatically execute approval transaction if needed
            
        Returns:
            Transaction data or None if the swap failed
        """
        # Create Web3 instance for the chain
        rpc_url = os.getenv(f"WEB3_RPC_URL_{self.chain_id}", os.getenv("WEB3_RPC_URL", ""))
        if not rpc_url:
            logger.error(f"No RPC URL configured for chain ID {self.chain_id}")
            return None
        
        web3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Get account from private key
        account = web3.eth.account.from_key(private_key)
        user_address = account.address
        
        try:
            # Get swap transaction data
            swap_data = await self.get_swap_transaction(
                in_token_address=in_token_address,
                out_token_address=out_token_address,
                amount=amount,
                account=user_address,
                slippage=slippage,
                gas_price=gas_price,
                referrer=referrer,
                referrer_fee=referrer_fee
            )
            
            if not swap_data:
                logger.error("Failed to get swap transaction data")
                return None
            
            # Check if token approval is needed
            approval_result = None
            if check_allowance:
                needs_approval, approval_tx = await self.check_and_create_approval_transaction(
                    swap_data=swap_data,
                    owner_address=user_address,
                    amount_to_approve="max"  # Use max approval amount
                )
                
                if needs_approval:
                    logger.info("Token approval needed before swap")
                    
                    if auto_approve and approval_tx:
                        logger.info("Executing token approval transaction...")
                        
                        # Get token address from swap data
                        token_address = swap_data.get("inToken", {}).get("address", "")
                        if not token_address:
                            logger.error("Input token address not found in swap data")
                            return None
                        
                        # Execute approval transaction
                        approval_result = await self.execute_approval_transaction(
                            token_address=token_address,
                            spender_address=swap_data.get("to", ""),
                            private_key=private_key,
                            amount="max",
                            gas_price=gas_price
                        )
                        
                        if not approval_result or not approval_result.get("success"):
                            logger.error("Token approval failed")
                            return {
                                'success': False,
                                'error': 'Token approval failed',
                                'approval_result': approval_result
                            }
                        
                        logger.info(f"Token approval successful: {approval_result.get('tx_hash')}")
                        
                        # Wait a short time for approval to be recognized
                        await asyncio.sleep(2)
                    elif not auto_approve:
                        logger.warning("Token approval needed but auto_approve is disabled")
                        return {
                            'success': False,
                            'error': 'Token approval needed but auto_approve is disabled',
                            'needs_approval': True,
                            'token_address': swap_data.get("inToken", {}).get("address", ""),
                            'spender_address': swap_data.get("to", "")
                        }
                    else:
                        logger.error("Failed to create approval transaction")
                        return {
                            'success': False,
                            'error': 'Failed to create approval transaction'
                        }
            
            # Create swap transaction
            tx = {
                'to': swap_data['to'],
                'value': int(swap_data['value']),
                'gas': int(swap_data['estimatedGas'] * 1.2),  # Add 20% buffer to gas estimate
                'gasPrice': int(swap_data['gasPrice']),
                'nonce': web3.eth.get_transaction_count(user_address),
                'data': swap_data['data'],
                'chainId': int(self.chain_id)
            }
            
            # Sign and send transaction
            signed_tx = account.sign_transaction(tx)
            tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for transaction receipt
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            
            result = {
                'success': receipt['status'] == 1,
                'tx_hash': web3.to_hex(tx_hash),
                'explorer_url': self._get_explorer_url(web3.to_hex(tx_hash)),
                'gas_used': receipt['gasUsed'],
                'from_token': swap_data['inToken'],
                'to_token': swap_data['outToken'],
                'amount_in': swap_data['inAmount'],
                'amount_out': swap_data['outAmount'],
                'price_impact': swap_data.get('price_impact', 'N/A')
            }
            
            # Include approval result if an approval was executed
            if approval_result:
                result['approval'] = {
                    'success': approval_result['success'],
                    'tx_hash': approval_result['tx_hash'],
                    'explorer_url': approval_result['explorer_url']
                }
            
            return result
        
        except Exception as e:
            logger.error(f"Error executing swap: {str(e)}")
            return None
    
    def _get_explorer_url(self, tx_hash: str) -> str:
        """Get explorer URL for transaction
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Explorer URL for the transaction
        """
        explorer_map = {
            '1': f"https://etherscan.io/tx/{tx_hash}",
            '56': f"https://bscscan.com/tx/{tx_hash}",
            '137': f"https://polygonscan.com/tx/{tx_hash}",
            '42161': f"https://arbiscan.io/tx/{tx_hash}",
            '10': f"https://optimistic.etherscan.io/tx/{tx_hash}",
            '43114': f"https://snowtrace.io/tx/{tx_hash}",
            '250': f"https://ftmscan.com/tx/{tx_hash}",
            '146': f"https://explorer.sonic.ooo/tx/{tx_hash}",
            # Add more chains as needed
        }
        
        return explorer_map.get(self.chain_id, f"https://etherscan.io/tx/{tx_hash}")
    
    # Cross-chain functionality
    
    async def get_cross_chain_quote(self,
                           from_chain_id: str,
                           to_chain_id: str,
                           from_token_address: str,
                           to_token_address: str,
                           amount: str,
                           wallet_address: str) -> Optional[Dict[str, Any]]:
        """Get a cross-chain swap quote
        
        Args:
            from_chain_id: Source chain ID
            to_chain_id: Destination chain ID
            from_token_address: Token address on source chain
            to_token_address: Token address on destination chain
            amount: Amount to swap (without decimals)
            wallet_address: User's wallet address
            
        Returns:
            Cross-chain quote data or None if the request failed
        """
        # Store original chain ID
        original_chain_id = self.chain_id
        
        # We need to use the source chain for the API request
        if from_chain_id != self.chain_id:
            logger.info(f"Switching from chain {self.chain_id} to {from_chain_id} for cross-chain quote")
            self.chain_id = from_chain_id
            self.chain_name = self._get_chain_name(from_chain_id)
        
        try:
            url = f"{self.base_url}/v1/cross_chain/cross/quote"
            headers = {}
            
            if self.use_pro_api and self.api_key:
                headers['apikey'] = self.api_key
                headers['Content-Type'] = 'application/json'
            
            params = {
                'account': wallet_address,
                'fromChainId': from_chain_id,
                'toChainId': to_chain_id,
                'fromTokenAddress': from_token_address,
                'toTokenAddress': to_token_address,
                'amount': amount,
                'slippage': str(self.slippage)
            }
            
            logger.info(f"Making cross-chain quote request to: {url}")
            logger.info(f"Request parameters: {json.dumps(params, indent=2)}")
            
            # Apply rate limiting
            now = time.time()
            if now - self._last_request < self.min_interval:
                await asyncio.sleep(self.min_interval - (now - self._last_request))
            self._last_request = time.time()
            
            async with self._session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"OpenOcean cross-chain quote request failed with status {response.status}")
                    return None
                
                full_response = await response.json()
                logger.info(f"OpenOcean cross-chain quote response (truncated): {json.dumps(full_response)[:200]}...")
                
                if full_response.get('code') != 200:
                    logger.error(f"OpenOcean API returned error code: {full_response.get('code')}")
                    return None
                
                # Extract the data field which contains the quote information
                if 'data' in full_response and isinstance(full_response['data'], dict):
                    quote_data = full_response['data']
                    return quote_data
                else:
                    logger.warning(f"No cross-chain quote data found in response!")
                    return None
        
        except Exception as e:
            logger.error(f"Error making cross-chain quote request: {str(e)}")
            return None
        
        finally:
            # Restore original chain ID
            if original_chain_id != self.chain_id:
                logger.info(f"Restoring chain ID from {self.chain_id} to {original_chain_id}")
                self.chain_id = original_chain_id
                self.chain_name = self._get_chain_name(original_chain_id)
    
    async def get_cross_chain_swap_transaction(self,
                                        account: str,
                                        route: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cross-chain swap transaction data
        
        Args:
            account: User's wallet address
            route: Route data from cross-chain quote API
            
        Returns:
            Cross-chain swap transaction data or None if the request failed
        """
        try:
            url = f"{self.base_url}/v1/cross_chain/cross/swap"
            headers = {}
            
            if self.use_pro_api and self.api_key:
                headers['apikey'] = self.api_key
                headers['Content-Type'] = 'application/json'
            
            # Prepare the request body
            data = {
                'account': account,
                'route': route
            }
            
            logger.info(f"Making cross-chain swap request to: {url}")
            logger.info(f"Request data: {json.dumps(data, indent=2)}")
            
            # Apply rate limiting
            now = time.time()
            if now - self._last_request < self.min_interval:
                await asyncio.sleep(self.min_interval - (now - self._last_request))
            self._last_request = time.time()
            
            async with self._session.post(url, json=data, headers=headers) as response:
                if response.status != 201 and response.status != 200:
                    logger.error(f"OpenOcean cross-chain swap request failed with status {response.status}")
                    try:
                        error_text = await response.text()
                        logger.error(f"Error response: {error_text}")
                    except:
                        pass
                    return None
                
                full_response = await response.json()
                logger.info(f"OpenOcean cross-chain swap response (truncated): {json.dumps(full_response)[:200]}...")
                
                if full_response.get('code') != 200:
                    logger.error(f"OpenOcean API returned error code: {full_response.get('code')}")
                    return None
                
                # Extract the data field which contains the transaction information
                if 'data' in full_response and isinstance(full_response['data'], dict):
                    tx_data = full_response['data']
                    return tx_data
                else:
                    logger.warning(f"No cross-chain swap transaction data found in response!")
                    return None
        
        except Exception as e:
            logger.error(f"Error making cross-chain swap request: {str(e)}")
            return None
    
    async def get_cross_chain_status(self, tx_hash: str, from_chain_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a cross-chain transaction
        
        Args:
            tx_hash: Transaction hash
            from_chain_id: Source chain ID
            
        Returns:
            Cross-chain status data or None if the request failed
        """
        try:
            url = f"{self.base_url}/v1/cross_chain/cross/getCrossStatus"
            headers = {}
            
            if self.use_pro_api and self.api_key:
                headers['apikey'] = self.api_key
                headers['Content-Type'] = 'application/json'
            
            params = {
                'hash': tx_hash,
                'fromChainId': from_chain_id
            }
            
            logger.info(f"Checking cross-chain status for tx {tx_hash}")
            
            # Apply rate limiting
            now = time.time()
            if now - self._last_request < self.min_interval:
                await asyncio.sleep(self.min_interval - (now - self._last_request))
            self._last_request = time.time()
            
            async with self._session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"OpenOcean cross-chain status request failed with status {response.status}")
                    return None
                
                full_response = await response.json()
                
                if full_response.get('code') != 200:
                    logger.error(f"OpenOcean API returned error code: {full_response.get('code')}")
                    return None
                
                # Extract the data field which contains the status information
                if 'data' in full_response and isinstance(full_response['data'], dict):
                    status_data = full_response['data']
                    return status_data
                else:
                    logger.warning(f"No cross-chain status data found in response!")
                    return None
        
        except Exception as e:
            logger.error(f"Error checking cross-chain status: {str(e)}")
            return None
    
    # DCA functionality
    
    async def create_dca_order(self, 
                           from_token_address: str,
                           to_token_address: str,
                           total_amount: str,
                           time_interval: int,
                           num_orders: int,
                           min_price_ratio: str = "0.9",
                           max_price_ratio: str = "1.1") -> Optional[Dict[str, Any]]:
        """Create a DCA (Dollar Cost Averaging) order
        
        Args:
            from_token_address: Token to sell (e.g. USDC)
            to_token_address: Token to buy (e.g. wS)
            total_amount: Total amount to spend across all orders
            time_interval: Time between orders in seconds (e.g. 3600 for hourly)
            num_orders: Number of orders to place
            min_price_ratio: Minimum acceptable price ratio (default: 0.9)
            max_price_ratio: Maximum acceptable price ratio (default: 1.1)
            
        Returns:
            DCA order creation data or None if the request failed
        """
        try:
            url = f"{self.base_url}/v1/{self.chain_name}/dca/swap"
            headers = {}
            
            if self.use_pro_api and self.api_key:
                headers['apikey'] = self.api_key
                headers['Content-Type'] = 'application/json'
            
            # Calculate the amount per order
            per_order_amount = str(int(float(total_amount) / num_orders))
            
            # Prepare the request (note: this is a simplified version, 
            # in a real implementation you would need detailed order parameters)
            data = {
                "route": {
                    "makerAsset": from_token_address,
                    "takerAsset": to_token_address,
                    "makingAmount": total_amount,
                    "time": time_interval,
                    "times": num_orders,
                    "minPrice": min_price_ratio,
                    "maxPrice": max_price_ratio
                }
            }
            
            logger.info(f"Creating DCA order request to: {url}")
            logger.info(f"Request data: {json.dumps(data, indent=2)}")
            
            # Apply rate limiting
            now = time.time()
            if now - self._last_request < self.min_interval:
                await asyncio.sleep(self.min_interval - (now - self._last_request))
            self._last_request = time.time()
            
            async with self._session.post(url, json=data, headers=headers) as response:
                if response.status != 201 and response.status != 200:
                    logger.error(f"OpenOcean DCA order request failed with status {response.status}")
                    try:
                        error_text = await response.text()
                        logger.error(f"Error response: {error_text}")
                    except:
                        pass
                    return None
                
                full_response = await response.json()
                logger.info(f"OpenOcean DCA order response: {json.dumps(full_response)}")
                
                if full_response.get('code') != 200:
                    logger.error(f"OpenOcean API returned error code: {full_response.get('code')}")
                    return None
                
                # Extract the data field which contains the transaction information
                if 'data' in full_response and isinstance(full_response['data'], dict):
                    order_data = full_response['data']
                    return order_data
                else:
                    logger.warning(f"No DCA order data found in response!")
                    return None
        
        except Exception as e:
            logger.error(f"Error creating DCA order: {str(e)}")
            return None
    
    async def get_dca_orders(self, wallet_address: str) -> Optional[List[Dict[str, Any]]]:
        """Get all DCA orders for a wallet address
        
        Args:
            wallet_address: Wallet address to check orders for
            
        Returns:
            List of DCA orders or None if the request failed
        """
        try:
            url = f"{self.base_url}/v1/limit-order/{self.chain_name}/address/{wallet_address}"
            headers = {}
            
            if self.use_pro_api and self.api_key:
                headers['apikey'] = self.api_key
                headers['Content-Type'] = 'application/json'
            
            logger.info(f"Getting DCA orders for address {wallet_address}")
            
            # Apply rate limiting
            now = time.time()
            if now - self._last_request < self.min_interval:
                await asyncio.sleep(self.min_interval - (now - self._last_request))
            self._last_request = time.time()
            
            async with self._session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"OpenOcean DCA orders request failed with status {response.status}")
                    return None
                
                full_response = await response.json()
                
                if full_response.get('code') != 200:
                    logger.error(f"OpenOcean API returned error code: {full_response.get('code')}")
                    return None
                
                # Extract the data field which contains the orders information
                if 'data' in full_response and isinstance(full_response['data'], list):
                    orders = full_response['data']
                    return orders
                else:
                    logger.warning(f"No DCA orders found in response!")
                    return []
        
        except Exception as e:
            logger.error(f"Error getting DCA orders: {str(e)}")
            return None