"""Odos Router API connection handler"""
import logging
from typing import Dict, Any, Optional, List
import aiohttp
import asyncio
from datetime import datetime
import time
import json

logger = logging.getLogger(__name__)

class OdosConnection:
    """Connection handler for Odos Router API"""
    def __init__(self, config: Dict[str, Any]):
        """Initialize Odos connection

        Args:
            config: Configuration dictionary containing API settings
        """
        self.base_url = "https://api.odos.xyz"
        self._session: Optional[aiohttp.ClientSession] = None
        self.chain_id = config.get('chain_id', '146')  # Default to Sonic chain
        self._last_request = 0
        self.min_interval = 1  # 1 second between requests
        logger.info("Initialized Odos connection")

    async def connect(self) -> bool:
        """Establish connection and verify API access"""
        try:
            self._session = aiohttp.ClientSession()
            # Test connection using base info endpoint
            async with self._session.get(f"{self.base_url}/sor/info") as response:
                response_text = await response.text()
                logger.debug(f"Connection test response: {response.status} - {response_text}")

                if response.status == 200:
                    logger.info("✅ Successfully connected to Odos API")
                    # Now check if chain is supported
                    return await self._verify_chain_support()
                else:
                    logger.error(f"Failed to connect to Odos API: {response.status}, {response_text}")
                    return False
        except Exception as e:
            logger.error(f"Error connecting to Odos: {str(e)}")
            return False

    async def _verify_chain_support(self) -> bool:
        """Verify if the configured chain is supported"""
        try:
            if not self._session:
                return False

            async with self._session.get(f"{self.base_url}/sor/chains") as response:
                if response.status == 200:
                    data = await response.json()
                    supported_chains = [str(chain.get('chainId')) for chain in data.get('chains', [])]

                    if self.chain_id in supported_chains:
                        logger.info(f"Chain {self.chain_id} is supported by Odos")
                        return True
                    else:
                        logger.error(f"Chain {self.chain_id} not supported by Odos")
                        return False
                else:
                    logger.error("Failed to get supported chains list")
                    return False
        except Exception as e:
            logger.error(f"Error verifying chain support: {str(e)}")
            return False

    async def get_quote(self,
        input_tokens: List[Dict[str, str]],
        output_tokens: List[Dict[str, str]],
        user_addr: str,
        slippage: float = 0.5,
    ) -> Optional[Dict[str, Any]]:
        """Get swap quote from Odos

        Args:
            input_tokens: List of input token info [{"tokenAddress": addr, "amount": amount}]
            output_tokens: List of output token info [{"tokenAddress": addr, "proportion": 1}]
            user_addr: User's wallet address
            slippage: Slippage tolerance percentage

        Returns:
            Quote information or None on error
        """
        try:
            if not self._session:
                logger.error("No active session")
                return None

            # Basic rate limiting
            current_time = time.time()
            if current_time - self._last_request < self.min_interval:
                await asyncio.sleep(self.min_interval)
            self._last_request = current_time

            # Handle native token address conversions
            for token in input_tokens:
                if token['tokenAddress'].lower() == '0x0000000000000000000000000000000000000000':
                    token['tokenAddress'] = '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'
                    logger.debug(f"Converted input native token address to: {token['tokenAddress']}")

            for token in output_tokens:
                if token['tokenAddress'].lower() == '0x0000000000000000000000000000000000000000':
                    token['tokenAddress'] = '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'
                    logger.debug(f"Converted output native token address to: {token['tokenAddress']}")

            quote_data = {
                'inputTokens': input_tokens,
                'outputTokens': output_tokens,
                'userAddr': user_addr,
                'slippageLimitPercent': slippage,
                'chainId': int(self.chain_id),
                'compact': True,
                'disableRFQs': True,
                'version': 'v2'  # Use v2 of the API
            }

            url = f"{self.base_url}/sor/quote/v2"

            logger.debug(f"Getting Odos quote with data: {quote_data}")
            async with self._session.post(url, json=quote_data) as response:
                response_text = await response.text()
                logger.debug(f"Response status: {response.status}")
                logger.debug(f"Response text: {response_text}")

                if response.status == 200:
                    data = json.loads(response_text)
                    return data
                else:
                    logger.error(f"Odos API error {response.status}: {response_text}")
                    return None

        except Exception as e:
            logger.error(f"Error getting Odos quote: {str(e)}")
            return None

    async def get_supported_tokens(self) -> Optional[Dict[str, Any]]:
        """Get list of supported tokens on current chain"""
        try:
            if not self._session:
                logger.error("No active session")
                return None

            url = f"{self.base_url}/sor/v2/tokens"
            params = {'chainId': int(self.chain_id)}

            async with self._session.get(url, params=params) as response:
                response_text = await response.text()
                logger.debug(f"Response status: {response.status}")
                logger.debug(f"Response text: {response_text}")

                if response.status == 200:
                    data = json.loads(response_text)
                    return data
                else:
                    logger.error(f"Odos API error {response.status}: {response_text}")
                    return None

        except Exception as e:
            logger.error(f"Error getting supported tokens: {str(e)}")
            return None

    async def close(self) -> None:
        """Close the connection and cleanup resources"""
        if self._session:
            await self._session.close()
            logger.info("Closed Odos connection")

    async def assemble_transaction(self,
        path_id: str,
        receiver: str,
        simulation: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Assemble swap transaction from quote

        Args:
            path_id: Quote path ID from get_quote response
            receiver: Receiver address for tokens
            simulation: Whether to run simulation

        Returns:
            Transaction data or None on error
        """
        try:
            if not self._session:
                logger.error("No active session")
                return None

            assemble_data = {
                'pathId': path_id,
                'receiver': receiver,
                'simulate': simulation,
                'chainId': int(self.chain_id)
            }

            url = f"{self.base_url}/sor/assemble"

            logger.debug(f"Assembling Odos transaction with data: {assemble_data}")
            async with self._session.post(url, json=assemble_data) as response:
                response_text = await response.text()
                logger.debug(f"Response status: {response.status}")
                logger.debug(f"Response text: {response_text}")

                if response.status == 200:
                    data = json.loads(response_text)
                    return data
                else:
                    logger.error(f"Odos API error {response.status}: {response_text}")
                    return None

        except Exception as e:
            logger.error(f"Error assembling Odos transaction: {str(e)}")
            return None