import logging
import os
import json
import time
import aiohttp
import asyncio
from web3 import Web3
import requests
from typing import Dict, Any, Optional
from functools import partial

logger = logging.getLogger("connections.eternalai_connection")

IPFS = "ipfs://"
LIGHTHOUSE_IPFS = "https://gateway.lighthouse.storage/ipfs/"
GCS_ETERNAL_AI_BASE_URL = "https://cdn.eternalai.org/upload/"
AGENT_CONTRACT_ABI = [{"inputs": [{"internalType": "uint256","name": "_agentId","type": "uint256"}],"name": "getAgentSystemPrompt","outputs": [{"internalType": "bytes[]","name": "","type": "bytes[]"}],"stateMutability": "view","type": "function"}]
AGENT_ETH_ADDRESS = "0x4b4C05b1dc15102307A55932c14bC6Cd51767eC5"
AGENT_TOKEN_CONTRACT = "0xaC101cB24286C6B972b2327a16F5Dd19cBf6952e"

# Chain-specific contract addresses
AGENT_CONTRACT_ADDRESSES = {
    "8453": "0x1E65FCa9b6640bC87AE41f1a897762c334821D1C",  # BASE
    "56": "0x3B9710bA5578C2eeD075D8A23D8c596925fa4625",   # BSC
}

class ConnectionError(Exception):
    """Base class for EternalAI connection errors"""
    pass

class EternalAIConnection:
    """Connection handler for EternalAI API interactions"""
    def __init__(self, config: Dict[str, Any]):
        """Initialize EternalAI connection"""
        self.config = self.validate_config(config)
        self.timeout = config.get('timeout', 30)
        self.base_url = "https://api.eternalai.org/v1"
        self.agent_url = "https://agent.api.eternalai.org/api/agent"
        self.max_retries = 3

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate EternalAI configuration"""
        required_fields = ["model", "agent_id", "chain_id"]
        missing_fields = [field for field in required_fields if field not in config]

        if missing_fields:
            raise ValueError(f"Missing required configuration fields: {', '.join(missing_fields)}")

        if not isinstance(config["model"], str):
            raise ValueError("model must be a string")

        try:
            # Set chain-specific configuration
            chain_id = str(config.get('chain_id', '8453'))
            if chain_id in AGENT_CONTRACT_ADDRESSES:
                config['contract_address'] = Web3.to_checksum_address(AGENT_CONTRACT_ADDRESSES[chain_id])
                logger.info(f"Using chain-specific contract address for chain {chain_id}")
            elif 'contract_address' in config:
                config['contract_address'] = Web3.to_checksum_address(config['contract_address'])

            # Validate ETH address
            if 'eth_address' in config:
                config['eth_address'] = Web3.to_checksum_address(config['eth_address'])
            else:
                config['eth_address'] = Web3.to_checksum_address(AGENT_ETH_ADDRESS)

            config['token_contract'] = Web3.to_checksum_address(AGENT_TOKEN_CONTRACT)
        except ValueError as e:
            raise ValueError(f"Invalid Ethereum address format: {str(e)}")

        # Log critical fields
        logger.info(f"Validating config - agent_id: {config['agent_id']}")
        logger.info(f"Agent ETH address: {config['eth_address']}")
        logger.info(f"Agent token contract: {config['token_contract']}")
        if 'contract_address' in config:
            logger.info(f"Contract address configured: {config['contract_address']}")
        if 'rpc_url' in config:
            logger.info(f"RPC URL configured: {config['rpc_url']}")

        return config

    async def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information from EternalAI API"""
        try:
            agent_id = self.config["agent_id"]
            if not agent_id:
                raise ConnectionError("Missing agent_id in configuration")

            api_key = os.getenv("ETERNAL_AI_KEY")
            if not api_key:
                raise ConnectionError("EternalAI API key not found")

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            # Create session with short timeout
            timeout = aiohttp.ClientTimeout(total=10, connect=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                try:
                    async with await asyncio.wait_for(
                        session.get(f"{self.agent_url}/{agent_id}", headers=headers),
                        timeout=10
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise ConnectionError(f"Failed to get agent info: HTTP {response.status} - {error_text}")

                        data = await response.json()
                        if data.get("error"):
                            raise ConnectionError(f"Error getting agent info: {data['error']}")

                        result = data.get("result", {})
                        logger.info(f"Retrieved agent info for {agent_id}")

                        # Validate agent ETH address
                        eth_address = result.get('eth_address', '')
                        if eth_address:
                            try:
                                eth_address = Web3.to_checksum_address(eth_address)
                                if eth_address != self.config['eth_address']:
                                    logger.warning(f"Agent ETH address mismatch. Expected: {self.config['eth_address']}, Got: {eth_address}")
                            except ValueError:
                                logger.warning(f"Invalid eth_address format from API: {eth_address}")

                        # Log important agent details
                        if result:
                            logger.info(f"Agent ETH address: {eth_address}")
                            logger.info(f"Agent wallet balance: {result.get('wallet_balance')}")
                            logger.info(f"Agent contract address: {result.get('agent_contract_address')}")
                            logger.info(f"Network ID: {result.get('network_id')}")

                        return result

                except asyncio.TimeoutError:
                    raise ConnectionError("Timeout getting agent info")
                except aiohttp.ClientError as e:
                    raise ConnectionError(f"Network error: {str(e)}")

        except Exception as e:
            raise ConnectionError(f"Failed to get agent info: {str(e)}")

    async def _make_contract_call(self, web3: Web3, contract_address: str, agent_id: int) -> Optional[bytes]:
        """Make an async contract call without blocking"""
        try:
            checksum_address = Web3.to_checksum_address(contract_address)
            contract = web3.eth.contract(address=checksum_address, abi=AGENT_CONTRACT_ABI)

            # Create partial function for the contract call
            fn = partial(contract.functions.getAgentSystemPrompt(agent_id).call)
            logger.info(f"Making contract call to {checksum_address} with agent_id: {agent_id}")

            try:
                # Execute contract call in a separate thread with strict timeout
                result = await asyncio.wait_for(asyncio.to_thread(fn), timeout=5.0)

                if result and len(result) > 0:
                    return result[0]
                logger.warning(f"Empty result from contract {checksum_address}")
                return None

            except asyncio.TimeoutError:
                logger.error(f"Contract call timeout for {checksum_address}")
                return None
            except Exception as e:
                logger.warning(f"Contract call failed: {str(e)}")
                return None

        except Exception as e:
            logger.warning(f"Contract initialization failed for {contract_address}: {str(e)}")
            return None

    async def _make_chat_completion_request(self, request_data: Dict[str, Any], start_time: float) -> str:
        """Make chat completion API request with timeout handling"""
        api_key = os.getenv("ETERNAL_AI_KEY")
        if not api_key:
            raise ConnectionError("EternalAI API key not found")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Create session with strict timeouts
        timeout = aiohttp.ClientTimeout(total=15, connect=5, sock_read=10)
        logger.info("Creating new session for chat completion request")

        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = f"{self.base_url}/chat/completions"
            logger.info(f"Making API request to {url}")
            logger.info(f"Request data: {json.dumps(request_data, indent=2)}")

            try:
                # Wrap the API call in wait_for to ensure timeout
                async with await asyncio.wait_for(
                    session.post(url, json=request_data, headers=headers),
                    timeout=15
                ) as response:
                    try:
                        response_data = await response.json()
                    except Exception as e:
                        raise ConnectionError(f"Failed to parse API response: {str(e)}")

                    if response.status != 200 or response_data.get("code", -1) != 0:
                        error_text = await response.text()
                        error_msg = response_data.get("message", error_text)
                        raise ConnectionError(f"API request failed: {error_msg}")

                    request_duration = time.time() - start_time
                    logger.info(f"API request completed in {request_duration:.2f} seconds")

                    choices = response_data.get("choices", [])
                    if not choices:
                        raise ConnectionError("No choices in response")

                    message = choices[0].get("message", {})
                    content = message.get("content")
                    if not content:
                        raise ConnectionError("No message content in response")

                    if onchain_data := response_data.get("onchain_data"):
                        logger.info("Transaction details:")
                        logger.info(f"Inference ID: {onchain_data.get('infer_id')}")
                        logger.info(f"Committee: {onchain_data.get('pbft_committee')}")
                        logger.info(f"Proposer: {onchain_data.get('proposer')}")
                        logger.info(f"Inference TX: {onchain_data.get('infer_tx')}")

                    logger.info(f"Generated text response: {content[:100]}...")
                    return content

            except asyncio.TimeoutError:
                raise ConnectionError(f"API request timed out after 15 seconds")
            except aiohttp.ClientError as e:
                raise ConnectionError(f"Network error: {str(e)}")
            except Exception as e:
                raise ConnectionError(f"API request failed: {str(e)}")

    async def generate_text(self, prompt: str, system_prompt: str, model: Optional[str] = None, chain_id: Optional[str] = None, **kwargs) -> str:
        """Generate text using EternalAI models"""
        start_time = time.time()
        retry_count = 0

        model = model or self.config["model"]
        chain_id = chain_id or self.config.get("chain_id", "8453")  # Use Base chain ID
        logger.info(f"Using model: {model}")
        logger.info(f"Using chain_id: {chain_id}")

        # Only try to get system prompt once
        try:
            web3 = Web3(Web3.HTTPProvider(self.config["rpc_url"]))
            if web3.is_connected():
                logger.info(f"Web3 connected to {self.config['rpc_url']}")

                # Try to get prompt from token contract
                try:
                    token_addr = Web3.to_checksum_address(AGENT_TOKEN_CONTRACT)
                    agent_id_int = int(self.config["agent_id"])

                    result = await self._make_contract_call(web3, token_addr, agent_id_int)
                    if result:
                        decoded = result.decode("utf-8")
                        if IPFS in decoded:
                            system_prompt = await self.get_system_prompt_content(decoded)
                        else:
                            system_prompt = decoded
                        logger.info(f"Got system prompt from token contract: {system_prompt[:100]}...")
                    else:
                        logger.info("No system prompt from token contract, using provided prompt")
                except Exception as e:
                    logger.warning(f"Failed to get system prompt from token contract: {str(e)}")
            else:
                logger.warning(f"Failed to connect to RPC endpoint: {self.config['rpc_url']}")
        except Exception as e:
            logger.warning(f"Error during contract interaction: {str(e)}")

        while retry_count < self.max_retries:
            try:
                request_data = {
                    "chain_id": chain_id,
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 250,
                    "top_p": 1,
                    "frequency_penalty": 0,
                    "presence_penalty": 0,
                    "stream": False
                }

                # Wrap entire request in a timeout
                try:
                    async with asyncio.timeout(1000):  # Overall timeout for the request
                        return await self._make_chat_completion_request(request_data, start_time)
                except asyncio.TimeoutError:
                    raise ConnectionError("Request timed out")

            except ConnectionError as e:
                retry_count += 1
                if retry_count < self.max_retries:
                    await asyncio.sleep(1)
                    logger.info(f"Retrying request (attempt {retry_count + 1} of {self.max_retries})")
                    continue
                raise

            except Exception as e:
                retry_count += 1
                if retry_count < self.max_retries:
                    await asyncio.sleep(1)
                    logger.info(f"Retrying after error (attempt {retry_count + 1} of {self.max_retries}): {str(e)}")
                    continue
                raise ConnectionError(f"Text generation failed: {str(e)}")

        raise ConnectionError(f"Failed to generate text after {self.max_retries} attempts")

    async def close(self):
        """Close the connection"""
        pass

    async def test_connection(self) -> bool:
        """Test API connectivity with minimal payload"""
        try:
            api_key = os.getenv("ETERNAL_AI_KEY")
            if not api_key:
                raise ConnectionError("EternalAI API key not found")

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            test_data = {
                "model": self.config["model"],
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 1,
                "stream": False
            }

            timeout = aiohttp.ClientTimeout(total=5)  # Short timeout for test
            async with aiohttp.ClientSession(timeout=timeout) as session:
                try:
                    async with await asyncio.wait_for(
                        session.post(f"{self.base_url}/chat/completions", json=test_data, headers=headers),
                        timeout=5
                    ) as response:
                        return response.status == 200
                except asyncio.TimeoutError:
                    logger.error("Connection test timed out")
                    return False
                except aiohttp.ClientError as e:
                    logger.error(f"Connection test failed due to network error: {str(e)}")
                    return False

        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False

    async def get_system_prompt_content(self, on_chain_data: str) -> str:
        """Get system prompt content from IPFS or GCS"""
        try:
            if IPFS in on_chain_data:
                light_house = on_chain_data.replace(IPFS, LIGHTHOUSE_IPFS)
                logger.info(f"Trying Lighthouse IPFS gateway: {light_house}")

                timeout = aiohttp.ClientTimeout(total=10, connect=5)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    try:
                        async with await asyncio.wait_for(
                            session.get(light_house),
                            timeout=10
                        ) as response:
                            if response.status == 200:
                                content = await response.text()
                                logger.info(f"Retrieved system prompt from Lighthouse: {content[:100]}...")
                                return content

                            gcs = on_chain_data.replace(IPFS, GCS_ETERNAL_AI_BASE_URL)
                            logger.info(f"Trying GCS fallback: {gcs}")
                            async with await asyncio.wait_for(
                                session.get(gcs),
                                timeout=10
                            ) as response:
                                if response.status == 200:
                                    content = await response.text()
                                    logger.info(f"Retrieved system prompt from GCS: {content[:100]}...")
                                    return content
                                raise ConnectionError(f"Invalid on-chain system prompt response status: {response.status}")
                    except asyncio.TimeoutError:
                        raise ConnectionError("Timeout retrieving system prompt content")
            else:
                if len(on_chain_data) > 0:
                    logger.info(f"Using direct on-chain data as system prompt: {on_chain_data[:100]}...")
                    return on_chain_data
                raise ConnectionError("Invalid on-chain system prompt: empty data")
        except Exception as e:
            raise ConnectionError(f"Failed to get system prompt content: {str(e)}")