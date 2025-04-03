"""KyberSwap Aggregator API connection handler"""
import logging
import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, Optional, List
from web3 import Web3

logger = logging.getLogger(__name__)

class KyberSwapAggregator:
    """KyberSwap Aggregator API integration for Sonic chain"""

    # Base API URL for aggregator
    BASE_URL = "https://aggregator-api.kyberswap.com/sonic/api/v1"

    # Router contract address on Sonic
    ROUTER_ADDRESS = "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5"

    # Supported DEX protocols on Sonic
    SUPPORTED_DEXES = [
        "kyberswap-elastic",
        "kyberswap-classic",
        "equalizer",
        "solidly",
        "balancer",
        "curve"
    ]

    def __init__(self):
        """Initialize KyberSwap aggregator connection"""
        self._session: Optional[aiohttp.ClientSession] = None
        self._initialized = False
        logger.info("Initialized KyberSwap aggregator connection")

    async def connect(self) -> bool:
        """Establish API connection with proper headers"""
        try:
            if self._initialized and self._session and not self._session.closed:
                return True

            if self._session:
                await self._session.close()

            self._session = aiohttp.ClientSession(
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "X-Client-Id": "Latest"
                }
            )

            # Test connection
            test_params = {
                "ids": ",".join(self.SUPPORTED_DEXES),
                "page": 1,
                "pageSize": 1
            }
            async with self._session.get(f"{self.BASE_URL}/tokens", params=test_params) as response:
                if response.status == 200:
                    self._initialized = True
                    logger.info("✅ Successfully connected to KyberSwap API")
                    return True
                else:
                    text = await response.text()
                    logger.error(f"Failed to connect to KyberSwap API: {response.status} - {text}")
                    return False

        except Exception as e:
            logger.error(f"Error connecting to KyberSwap: {str(e)}")
            if self._session and not self._session.closed:
                await self._session.close()
            return False

    async def get_quote(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get swap quote from aggregator API"""
        try:
            if not self._session or self._session.closed:
                if not await self.connect():
                    return None

            token_in = params.get("tokenIn")
            token_out = params.get("tokenOut")
            amount_in = params.get("amountIn")
            to_address = params.get("to")
            slippage = params.get("slippageTolerance", "50")

            if not all([token_in, token_out, amount_in, to_address]):
                logger.error("Missing required parameters for quote")
                return None

            # Build quote request
            request_params = {
                "tokenIn": token_in,
                "tokenOut": token_out,
                "amountIn": amount_in,
                "saveGas": "0",
                "gasInclude": "true",
                "slippageTolerance": slippage,
                "ids": ",".join(self.SUPPORTED_DEXES),
                "clientData": json.dumps({"source": "ZerePyBot"})
            }

            logger.debug(f"Getting quote with params: {request_params}")
            async with self._session.get(f"{self.BASE_URL}/routes", params=request_params) as response:
                text = await response.text()
                logger.debug(f"Quote response: {text}")

                if response.status == 200:
                    data = json.loads(text)
                    if data.get("code") == 0:
                        quote_data = data.get("data")
                        if not quote_data or not quote_data.get("routeSummary"):
                            logger.error("Quote missing routeSummary")
                            return None
                        logger.info("✅ Successfully got KyberSwap quote")
                        return quote_data
                    else:
                        error_msg = data.get("message")
                        logger.error(f"KyberSwap quote error: {error_msg}")
                else:
                    logger.error(f"Failed to get quote: {response.status} - {text}")
                return None

        except Exception as e:
            logger.error(f"Error getting quote: {str(e)}")
            return None

    async def build_swap_data(self, chain_id: int, quote_data: Dict[str, Any], sender: str) -> Optional[Dict[str, Any]]:
        """Build swap transaction data from quote"""
        try:
            if not self._session or self._session.closed:
                if not await self.connect():
                    return None

            route_summary = quote_data.get("routeSummary")
            if not route_summary:
                logger.error("Missing routeSummary in quote data")
                return None

            # Build swap parameters
            build_params = {
                "routeSummary": route_summary,
                "sender": sender,
                "recipient": sender,
                "slippageTolerance": quote_data.get("slippageTolerance", 50),
                "deadline": int(time.time()) + 1200,  # 20 minutes
                "source": "ZerePyBot",
                "enableGasEstimation": True
            }

            logger.debug(f"Building swap with params: {json.dumps(build_params, indent=2)}")
            async with self._session.post(f"{self.BASE_URL}/route/build", json=build_params) as response:
                text = await response.text()
                logger.debug(f"Build response: {text}")

                if response.status == 200:
                    data = json.loads(text)
                    if data.get("code") == 0:
                        tx_data = data.get("data", {})
                        logger.info("✅ Successfully built swap transaction")
                        return {
                            "router_address": self.ROUTER_ADDRESS,
                            "transaction": tx_data,
                            "value": tx_data.get("value", "0")
                        }
                    else:
                        error_msg = data.get("message")
                        logger.error(f"KyberSwap build error: {error_msg}")
                else:
                    logger.error(f"Failed to build swap: {response.status} - {text}")
                return None

        except Exception as e:
            logger.error(f"Error building swap: {str(e)}", exc_info=True)
            return None

    async def close(self):
        """Close API connection"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._initialized = False
            logger.info("Closed KyberSwap connection")