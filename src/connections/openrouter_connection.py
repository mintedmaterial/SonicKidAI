"""OpenRouter connection implementation"""
import os
import logging
import traceback
import asyncio
import atexit
from typing import Dict, Any, Optional
import aiohttp
from .base_connection import BaseConnection, Action, Parameter
import sys

# Setup logging immediately
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

class OpenRouterConnection(BaseConnection):
    """Connection for OpenRouter API integration"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize OpenRouter connection"""
        try:
            super().__init__(config)
            self.api_key = os.getenv("OPENROUTER_API_KEY")  # Only use OpenRouter key
            self.base_url = "https://openrouter.ai/api/v1"  # OpenRouter base URL
            self.model = "anthropic/claude-3-sonnet"  # Full model name for OpenRouter
            self.session: Optional[aiohttp.ClientSession] = None
            self.connect_timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout for connection
            self.request_timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout for requests
            self.max_retries = 3
            self.is_connected = False

            # Register cleanup handler
            atexit.register(self._cleanup)

            self.actions = {
                "generate-text": Action(
                    name="generate-text",
                    description="Generate text using OpenRouter LLM",
                    parameters=[
                        Parameter(
                            name="prompt",
                            required=True,
                            type=str,
                            description="Text prompt for generation"
                        ),
                        Parameter(
                            name="system_prompt",
                            required=False,
                            type=str,
                            description="System context for generation"
                        )
                    ]
                )
            }
            logger.info(f"Initialized OpenRouter connection with model: {self.model}")
            if not self.api_key:
                logger.warning("No API key found for OpenRouter")
            else:
                # Log key format without revealing actual key
                masked_key = f"{self.api_key[:4]}...{self.api_key[-4:]}"
                logger.info(f"API key found (format: {masked_key})")
        except Exception as e:
            logger.error(f"Error in OpenRouter connection initialization: {str(e)}")
            logger.error(f"Detailed error: {traceback.format_exc()}")
            raise

    def _cleanup(self):
        """Cleanup handler for atexit"""
        try:
            if self.session and not self.session.closed:
                logger.info("Cleaning up OpenRouter session...")
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
                else:
                    loop.run_until_complete(self.close())
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    @property
    def is_llm_provider(self) -> bool:
        """Override to indicate this is an LLM provider"""
        return True

    async def connect(self) -> bool:
        """Initialize connection"""
        try:
            if self.is_connected and self.session and not self.session.closed:
                logger.debug("Session already exists")
                return True

            if not self.api_key:
                logger.error("Cannot connect: No API key configured")
                return False

            # Validate API key format
            if not self.api_key.startswith('sk-'):
                logger.error("Invalid API key format. Must start with 'sk-'")
                return False

            logger.info("Creating new session with OpenRouter API...")

            try:
                self.session = aiohttp.ClientSession(
                    timeout=self.connect_timeout,
                    headers={
                        'Authorization': f'Bearer {self.api_key}',
                        'Content-Type': 'application/json',
                        'HTTP-Referer': 'https://github.com/blorm-network/ZerePy',
                        'X-Title': 'ZerePy Framework'
                    }
                )
                logger.info("✅ Created new OpenRouter session")
            except Exception as e:
                logger.error(f"Failed to create session: {str(e)}")
                return False

            # Test connection with a minimal request
            try:
                test_data = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": "test"}],
                    "temperature": 0.7,
                    "max_tokens": 1
                }
                logger.debug(f"Test request data: {test_data}")

                async with asyncio.timeout(self.connect_timeout.total):
                    async with self.session.post(
                        f"{self.base_url}/chat/completions",
                        json=test_data
                    ) as response:
                        response_text = await response.text()
                        logger.debug(f"Test response (status={response.status}): {response_text}")

                        if response.status == 401:
                            logger.error("Authentication failed - invalid API key")
                            await self.close()
                            return False
                        elif response.status == 402:
                            logger.error("Insufficient credits - please check your OpenRouter account")
                            await self.close()
                            return False
                        elif response.status == 429:
                            logger.error("Rate limit exceeded")
                            await self.close()
                            return False
                        elif response.status not in (200, 400):  # 400 is OK for test request
                            logger.error(f"Connection test failed with status: {response.status}")
                            logger.error(f"Response text: {response_text}")
                            await self.close()
                            return False

            except asyncio.TimeoutError:
                logger.error("Connection test timed out")
                await self.close()
                return False
            except aiohttp.ClientError as e:
                logger.error(f"Connection test failed with error: {str(e)}")
                await self.close()
                return False

            self.is_connected = True
            logger.info("✅ Connection test successful")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize session: {str(e)}")
            logger.error(f"Detailed error: {traceback.format_exc()}")
            if self.session:
                await self.close()
            return False

    async def generate_text(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Generate text using OpenRouter API"""
        try:
            if not await self.is_configured():
                logger.error("API key not configured")
                return None

            if not self.session or not self.is_connected:
                logger.info("No active session, attempting to connect...")
                connected = await self.connect()
                if not connected:
                    logger.error("Failed to establish connection")
                    return None

            # Format messages for OpenRouter's chat completions API
            messages = []
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            messages.append({
                "role": "user",
                "content": prompt
            })

            # Prepare request data
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 300,
                "stream": False
            }

            logger.info(f"Making request to OpenRouter API with model: {self.model}")
            logger.debug(f"Request data: {data}")

            # Make request with retry
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"Request attempt {attempt + 1}/{self.max_retries}")
                    async with asyncio.timeout(self.request_timeout.total):
                        async with self.session.post(
                            f"{self.base_url}/chat/completions",
                            json=data
                        ) as response:
                            response_text = await response.text()
                            logger.debug(f"Response status: {response.status}")
                            logger.debug(f"Response text: {response_text}")

                            if response.status == 200:
                                try:
                                    result = await response.json()
                                    if result and "choices" in result:
                                        content = result["choices"][0].get("message", {}).get("content")
                                        if content:
                                            logger.info("Successfully generated text response")
                                            return content
                                        else:
                                            logger.error("Response missing content")
                                            logger.debug(f"Full response: {result}")
                                    else:
                                        logger.error("Unexpected response format")
                                        logger.debug(f"Full response: {result}")
                                except Exception as e:
                                    logger.error(f"Error parsing response: {str(e)}")
                                    logger.debug(f"Raw response text: {response_text}")
                                    return None
                            elif response.status == 401:
                                logger.error("Authentication failed - invalid API key")
                                return None
                            elif response.status == 402:
                                logger.error("Insufficient credits")
                                return None
                            elif response.status == 429:
                                logger.error("Rate limit exceeded")
                                if attempt < self.max_retries - 1:
                                    wait_time = 2 ** attempt
                                    logger.info(f"Waiting {wait_time} seconds before retry...")
                                    await asyncio.sleep(wait_time)
                                    continue
                            else:
                                logger.error(f"API error: {response.status} - {response_text}")

                except asyncio.TimeoutError:
                    logger.error(f"Request timed out (attempt {attempt + 1})")
                except aiohttp.ClientError as e:
                    logger.error(f"Network error: {str(e)}")
                    self.is_connected = False
                    # Try to reconnect for next attempt
                    if not await self.connect():
                        return None

                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)

            return None

        except Exception as e:
            logger.error(f"Error generating text: {str(e)}")
            logger.error(f"Detailed error: {traceback.format_exc()}")
            return None

    async def close(self) -> None:
        """Close the connection"""
        try:
            if self.session:
                await self.session.close()
                self.session = None
                self.is_connected = False
                logger.info("Closed OpenRouter session")
        except Exception as e:
            logger.error(f"Error closing session: {str(e)}")

    async def is_configured(self, verbose: bool = False) -> bool:
        """Check if connection is properly configured"""
        try:
            if not self.api_key:
                if verbose:
                    logger.warning("API key not found")
                return False

            # Verify we can make a connection
            if not self.session or not self.is_connected:
                success = await self.connect()
                if not success:
                    return False

            return True

        except Exception as e:
            logger.error(f"Error checking configuration: {str(e)}")
            return False

    async def perform_action(self, action_name: str, params: Dict[str, Any], **kwargs) -> Optional[str]:
        """Execute an action with the given parameters"""
        try:
            if not await self.is_configured():
                logger.error("Connection not configured")
                return None

            if action_name == "generate-text":
                return await self.generate_text(
                    prompt=params["prompt"],
                    system_prompt=params.get("system_prompt", "")
                )

            return None

        except Exception as e:
            logger.error(f"Error performing action {action_name}: {str(e)}")
            logger.error(f"Detailed error: {traceback.format_exc()}")
            return None