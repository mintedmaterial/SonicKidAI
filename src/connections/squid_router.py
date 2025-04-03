import logging
import os
from typing import Dict, Any, Optional
import aiohttp
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

class SquidRouterConnection:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_base_url = "https://apiplus.squidrouter.com/v2"
        self.integrator_id = "sonic-kid-5e63d38d-d397-4e67-8bdb-db7140421929"
        self.session = None
        self.wallet_address = "0x46ec3B933283a14A8f3c7e2d9A8086b4F592C3c6"  # Default wallet

        # Chain IDs for common networks
        self.chains = {
            "ETH": "1",       # Ethereum
            "BSC": "56",      # Binance Smart Chain
            "ARBITRUM": "42161",  # Arbitrum
            "POLYGON": "137", # Polygon
            "OPTIMISM": "10", # Optimism
            "AVALANCHE": "43114",  # Avalanche
            "Sonic": "146"  # Sonic
        }

    async def connect(self):
        """Initialize connection"""
        try:
            self.session = aiohttp.ClientSession(
                headers={
                    "x-integrator-id": self.integrator_id,
                    "Content-Type": "application/json"
                }
            )
            logger.info("SquidRouter connection initialized")
            logger.info(f"Using wallet address: {self.wallet_address}")

            # Validate connection with a simple route request
            test_params = {
                "fromAddress": self.wallet_address,
                "fromChain": self.chains["ETH"],
                "toChain": self.chains["ARBITRUM"],
                "fromToken": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
                "toToken": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",  # USDC
                "fromAmount": "1000000000000000000",  # 1 ETH
                "toAddress": self.wallet_address,
                "slippage": 1,
                "slippageConfig": {"autoMode": 1}
            }

            test_result = await self.get_route(test_params)
            if test_result:
                logger.info("Successfully validated Squid Router connection")

        except Exception as e:
            logger.error(f"Error initializing SquidRouter connection: {str(e)}")
            raise

    async def get_route(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get optimal route for swap"""
        try:
            # Ensure fromAddress and toAddress are set
            if 'fromAddress' not in params:
                params['fromAddress'] = self.wallet_address
            if 'toAddress' not in params:
                params['toAddress'] = self.wallet_address

            logger.info(f"Requesting route with params: {params}")

        self.session = aiohttp.ClientSession()
                f"{self.api_base_url}/route",
                json=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    request_id = response.headers.get("x-request-id")
                    logger.info(f"Successfully received route with request ID: {request_id}")
                    return {"data": data, "requestId": request_id}
                else:
                    error_data = await response.json()
                    logger.error(f"Route API error: {error_data}")
                    return None
        except Exception as e:
            logger.error(f"Error getting route: {str(e)}")
            return None

    async def get_status(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get transaction status"""
        try:
            async with self.session.get(
                f"{self.api_base_url}/status",
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_data = await response.json()
                    logger.error(f"Status API error: {error_data}")
                    return None
        except Exception as e:
            logger.error(f"Error getting status: {str(e)}")
            return None

    async def execute_cross_chain_swap(self, trade_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute a cross-chain token swap"""
        try:
            # Prepare route parameters
            route_params = {
                "fromAddress": self.wallet_address,
                "fromChain": trade_params["fromChain"],
                "fromToken": trade_params["fromToken"],
                "fromAmount": trade_params["fromAmount"],
                "toChain": trade_params["toChain"],
                "toToken": trade_params["toToken"],
                "toAddress": self.wallet_address,
                "slippage": trade_params.get("slippage", 1),
                "slippageConfig": {"autoMode": 1}
            }

            logger.info(f"Requesting route with params: {route_params}")
            route_result = await self.get_route(route_params)

            if not route_result:
                logger.error("Failed to get route from Squid Router")
                return None

            route = route_result["data"]["route"]
            request_id = route_result["requestId"]
            logger.info(f"Route received with request ID: {request_id}")

            # Return the execution data
            return {
                "route": route,
                "requestId": request_id,
                "transactionRequest": route["transactionRequest"]
            }

        except Exception as e:
            logger.error(f"Error executing cross-chain swap: {str(e)}")
            return None

    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()