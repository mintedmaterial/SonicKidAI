"""
OpenRouter connection for LLM capabilities
"""
import os
import logging
import aiohttp
import asyncio
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from .base_connection import BaseConnection

logger = logging.getLogger(__name__)

class OpenRouterConnection(BaseConnection):
    """OpenRouter API connection for LLM capabilities"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the Telegram connection"""
        # Load environment variables first
        load_dotenv()

        # Initialize API credentials before base class
        self.api_key = config.get('api_key', os.getenv("OPENROUTER_API_KEY", "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"))
        if not self.api_key:
            logger.warning("No OpenRouter API key found in environment")
        else:
            # Log only the format/prefix for security
            key_prefix = self.api_key[:8] if self.api_key else ""
            logger.info(f"API key found (format: {key_prefix}...)")

        self.base_url = "https://openrouter.ai/api/v1"
        # the newest Anthropic model is "claude-3-sonnet-20240229" 
        self.model = config.get('model', 'anthropic/claude-3-sonnet-20240229')
        self._session = None
        self._initialized = False

        # Initialize base class
        super().__init__(config)
        logger.info(f"Initialized OpenRouter connection with model: {self.model}")

    async def _ensure_session(self) -> None:
        """Ensure an active session exists"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            logger.debug("Created new aiohttp session for OpenRouter")

    async def connect(self) -> bool:
        """Initialize connection"""
        try:
            if not self.api_key:
                logger.error("Missing OpenRouter API key")
                return False

            await self._ensure_session()
            self._initialized = True
            logger.info("Created new aiohttp session for OpenRouter")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize OpenRouter session: {str(e)}")
            await self.close()  # Cleanup on failure
            return False

    async def generate_text(self, prompt: str) -> str:
        """Generate text using OpenRouter API"""
        try:
            result = await self.chat_completion("", prompt)
            return result.get('content', "Error generating response")
        except Exception as e:
            logger.error(f"Error in text generation: {str(e)}")
            return f"Error: {str(e)}"

    async def chat_completion(self, system_prompt: str, user_message: str) -> Dict[str, Any]:
        """Generate chat completion using OpenRouter API"""
        if not self.api_key:
            logger.error("API key not found")
            return {"content": "I apologize, but I'm not properly configured at the moment."}

        try:
            await self._ensure_session()

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "zerepy.replit.app",  # Required by OpenRouter
                "X-Title": "ZerePy Framework",  # Application identifier
                "Content-Type": "application/json"
            }

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_message})

            data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 4096,
                "temperature": 0.7
            }

            logger.debug(f"Making request to OpenRouter API with model {self.model}")
            async with self._session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30  # Add timeout to prevent hanging
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.debug("Received successful response from OpenRouter")
                    try:
                        content = result["choices"][0]["message"]["content"]
                        return {"content": content}
                    except (KeyError, IndexError) as e:
                        logger.error(f"Error parsing OpenRouter response: {e}")
                        return {"content": "Error parsing response"}
                else:
                    error_text = await response.text()
                    logger.error(f"OpenRouter API error: {response.status} - {error_text}")
                    return {"content": "I encountered an error while processing your request. Please try again."}

        except asyncio.TimeoutError:
            logger.error("OpenRouter request timed out")
            return {"content": "Request timed out. Please try again."}
        except Exception as e:
            logger.error(f"Error in chat completion: {str(e)}")
            return {"content": "I encountered an error while processing your request. Please try again."}

    async def close(self):
        """Close the aiohttp session and cleanup resources"""
        if self._session:
            if not self._session.closed:
                try:
                    await self._session.close()
                    logger.info("Closed OpenRouter aiohttp session")
                except Exception as e:
                    logger.error(f"Error closing OpenRouter session: {str(e)}")
            self._session = None  # Always set to None even if close fails
        self._initialized = False

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate connection configuration"""
        if not self.api_key:
            raise ValueError("API key not found in environment variables")
        return config

    @property
    def is_initialized(self) -> bool:
        """Check if the connection is properly initialized"""
        return self._initialized and bool(self._session and not self._session.closed)

    @property
    def is_llm_provider(self) -> bool:
        """This connection provides LLM capabilities"""
        return True

    async def is_configured(self, verbose: bool = False) -> bool:
        """Check if connection is properly configured"""
        is_configured = bool(self.api_key and self.model)
        if verbose and not is_configured:
            if not self.api_key:
                logger.warning("OpenRouter connection is not configured - missing API key")
            if not self.model:
                logger.warning("OpenRouter connection is not configured - missing model")
        return is_configured