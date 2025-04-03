"""
OpenOcean API integration as a BaseConnection implementation
"""
import logging
import os
from typing import Dict, Any, Optional, List
from .base_connection import BaseConnection, Action, ActionParameter
from .openocean_connection import OpenOceanConnection
from web3 import Web3

logger = logging.getLogger(__name__)

class OpenOceanBaseConnection(BaseConnection):
    """OpenOcean DEX integration base connection"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the OpenOcean base connection
        
        Args:
            config: Configuration dictionary containing:
                - chain_id: Chain ID to use for OpenOcean
                - slippage: Default slippage percentage
                - referrer: Optional referrer address
                - referrer_fee: Optional referrer fee percentage
        """
        super().__init__(config)
        self.openocean = None
        self.web3 = None
        self.account = None
        
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and prepare configuration
        
        Args:
            config: Raw configuration dictionary
            
        Returns:
            Validated configuration
        """
        # Default configuration
        validated_config = {
            'chain_id': config.get('chain_id', '1'),  # Default to Ethereum
            'slippage': config.get('slippage', 1),    # Default 1% slippage
            'private_key_env': config.get('private_key_env', 'ETH_PRIVATE_KEY'),
            'rpc_url_env': config.get('rpc_url_env', 'WEB3_RPC_URL'),
        }
        
        # Optional referrer parameters
        if 'referrer' in config:
            validated_config['referrer'] = config['referrer']
        
        if 'referrer_fee' in config:
            fee = float(config['referrer_fee'])
            if 0.01 <= fee <= 3:
                validated_config['referrer_fee'] = fee
            else:
                logger.warning(f"Referrer fee {fee} is outside allowed range (0.01-3), ignoring")
        
        logger.info(f"OpenOcean configured for chain ID: {validated_config['chain_id']}")
        return validated_config
    
    async def connect(self) -> bool:
        """Connect to OpenOcean API and initialize Web3
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Initialize OpenOcean connection
            self.openocean = OpenOceanConnection(self.config)
            if not await self.openocean.connect():
                logger.error("Failed to connect to OpenOcean API")
                return False
            
            # Initialize Web3 connection
            chain_id = self.config['chain_id']
            rpc_env_key = self.config['rpc_url_env']
            rpc_chain_env = f"{rpc_env_key}_{chain_id}"
            
            rpc_url = os.getenv(rpc_chain_env, os.getenv(rpc_env_key))
            if not rpc_url:
                logger.error(f"No RPC URL found in environment variables ({rpc_chain_env} or {rpc_env_key})")
                return False
            
            self.web3 = Web3(Web3.HTTPProvider(rpc_url))
            if not self.web3.is_connected():
                logger.error(f"Failed to connect to Web3 provider at {rpc_url}")
                return False
            
            # Initialize account if private key is available
            private_key_env = self.config['private_key_env']
            private_key = os.getenv(private_key_env)
            if private_key:
                self.account = self.web3.eth.account.from_key(private_key)
                logger.info(f"Account initialized: {self.account.address}")
            else:
                logger.warning(f"No private key found in environment variable {private_key_env}")
            
            logger.info(f"Successfully connected to OpenOcean API and Web3 for chain ID {chain_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error connecting to OpenOcean: {str(e)}")
            return False
    
    async def close(self) -> None:
        """Close the connection"""
        if self.openocean:
            await self.openocean.close()
            self.openocean = None
    
    def register_actions(self) -> None:
        """Register available actions for OpenOcean"""
        self.actions = {
            "get-token-list": Action(
                name="get-token-list",
                description="Get list of supported tokens on the current chain",
                parameters=[]
            ),
            "get-token-by-symbol": Action(
                name="get-token-by-symbol",
                description="Get token details by symbol",
                parameters=[
                    ActionParameter("symbol", True, str, "Token symbol (e.g., 'ETH', 'USDC')")
                ]
            ),
            "get-dex-list": Action(
                name="get-dex-list",
                description="Get list of supported DEXes on the current chain",
                parameters=[]
            ),
            "get-swap-quote": Action(
                name="get-swap-quote",
                description="Get a quote for swapping tokens",
                parameters=[
                    ActionParameter("in_token", True, str, "Input token address or symbol"),
                    ActionParameter("out_token", True, str, "Output token address or symbol"),
                    ActionParameter("amount", True, str, "Token amount (without decimals)"),
                    ActionParameter("gas_price", False, str, "Gas price in GWEI (without decimals)"),
                ]
            ),
            "execute-swap": Action(
                name="execute-swap",
                description="Execute a token swap",
                parameters=[
                    ActionParameter("in_token", True, str, "Input token address or symbol"),
                    ActionParameter("out_token", True, str, "Output token address or symbol"),
                    ActionParameter("amount", True, str, "Token amount (without decimals)"),
                    ActionParameter("slippage", False, float, "Slippage percentage (0.05-50)"),
                ]
            ),
        }
    
    async def get_token_list(self, **kwargs) -> Dict[str, Any]:
        """Get list of supported tokens on the current chain
        
        Returns:
            Response with token list
        """
        try:
            if not self.openocean:
                return {"success": False, "error": "Not connected to OpenOcean API"}
            
            tokens = await self.openocean.get_token_list()
            return {
                "success": tokens is not None,
                "tokens": tokens or [],
                "count": len(tokens) if tokens else 0
            }
        except Exception as e:
            logger.error(f"Error getting token list: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_token_by_symbol(self, **kwargs) -> Dict[str, Any]:
        """Get token details by symbol
        
        Args:
            symbol: Token symbol (e.g., 'ETH', 'USDC')
            
        Returns:
            Response with token details
        """
        try:
            symbol = kwargs.get("symbol")
            if not symbol:
                return {"success": False, "error": "Token symbol is required"}
            
            if not self.openocean:
                return {"success": False, "error": "Not connected to OpenOcean API"}
            
            token = await self.openocean.get_token_by_symbol(symbol)
            return {
                "success": token is not None,
                "token": token or None,
                "token_address": token.get("address") if token else None
            }
        except Exception as e:
            logger.error(f"Error getting token by symbol: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_dex_list(self, **kwargs) -> Dict[str, Any]:
        """Get list of supported DEXes on the current chain
        
        Returns:
            Response with DEX list
        """
        try:
            if not self.openocean:
                return {"success": False, "error": "Not connected to OpenOcean API"}
            
            dexes = await self.openocean.get_dex_list()
            return {
                "success": dexes is not None,
                "dexes": dexes or [],
                "count": len(dexes) if dexes else 0
            }
        except Exception as e:
            logger.error(f"Error getting DEX list: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_swap_quote(self, **kwargs) -> Dict[str, Any]:
        """Get a quote for swapping tokens
        
        Args:
            in_token: Input token address or symbol
            out_token: Output token address or symbol
            amount: Token amount (without decimals)
            gas_price: Optional gas price in GWEI
            
        Returns:
            Response with swap quote
        """
        try:
            in_token = kwargs.get("in_token")
            out_token = kwargs.get("out_token")
            amount = kwargs.get("amount")
            gas_price = kwargs.get("gas_price")
            
            if not all([in_token, out_token, amount]):
                return {"success": False, "error": "Missing required parameters"}
            
            if not self.openocean:
                return {"success": False, "error": "Not connected to OpenOcean API"}
            
            # Resolve token symbols to addresses if needed
            in_token_address = in_token
            if not in_token.startswith("0x"):
                token_info = await self.openocean.get_token_by_symbol(in_token)
                if not token_info:
                    return {"success": False, "error": f"Token symbol not found: {in_token}"}
                in_token_address = token_info["address"]
            
            out_token_address = out_token
            if not out_token.startswith("0x"):
                token_info = await self.openocean.get_token_by_symbol(out_token)
                if not token_info:
                    return {"success": False, "error": f"Token symbol not found: {out_token}"}
                out_token_address = token_info["address"]
            
            quote = await self.openocean.get_quote(
                in_token_address=in_token_address,
                out_token_address=out_token_address,
                amount=amount,
                gas_price=gas_price
            )
            
            if not quote:
                return {"success": False, "error": "Failed to get swap quote"}
            
            return {
                "success": True,
                "quote": quote,
                "inToken": quote.get("inToken", {}),
                "outToken": quote.get("outToken", {}),
                "inAmount": quote.get("inAmount"),
                "outAmount": quote.get("outAmount"),
                "estimatedGas": quote.get("estimatedGas"),
                "price_impact": quote.get("price_impact")
            }
        except Exception as e:
            logger.error(f"Error getting swap quote: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def execute_swap(self, **kwargs) -> Dict[str, Any]:
        """Execute a token swap
        
        Args:
            in_token: Input token address or symbol
            out_token: Output token address or symbol
            amount: Token amount (without decimals)
            slippage: Optional slippage percentage
            
        Returns:
            Response with swap transaction details
        """
        try:
            in_token = kwargs.get("in_token")
            out_token = kwargs.get("out_token")
            amount = kwargs.get("amount")
            slippage = kwargs.get("slippage")
            
            if not all([in_token, out_token, amount]):
                return {"success": False, "error": "Missing required parameters"}
            
            if not self.openocean:
                return {"success": False, "error": "Not connected to OpenOcean API"}
            
            if not self.account:
                return {"success": False, "error": "No wallet configured, private key missing"}
            
            # Resolve token symbols to addresses if needed
            in_token_address = in_token
            if not in_token.startswith("0x"):
                token_info = await self.openocean.get_token_by_symbol(in_token)
                if not token_info:
                    return {"success": False, "error": f"Token symbol not found: {in_token}"}
                in_token_address = token_info["address"]
            
            out_token_address = out_token
            if not out_token.startswith("0x"):
                token_info = await self.openocean.get_token_by_symbol(out_token)
                if not token_info:
                    return {"success": False, "error": f"Token symbol not found: {out_token}"}
                out_token_address = token_info["address"]
            
            # Get private key from environment
            private_key_env = self.config['private_key_env']
            private_key = os.getenv(private_key_env)
            if not private_key:
                return {"success": False, "error": f"Private key not found in environment variable {private_key_env}"}
            
            # Execute swap
            result = await self.openocean.execute_swap(
                in_token_address=in_token_address,
                out_token_address=out_token_address,
                amount=amount,
                private_key=private_key,
                slippage=slippage
            )
            
            if not result:
                return {"success": False, "error": "Failed to execute swap"}
            
            return result
        except Exception as e:
            logger.error(f"Error executing swap: {str(e)}")
            return {"success": False, "error": str(e)}