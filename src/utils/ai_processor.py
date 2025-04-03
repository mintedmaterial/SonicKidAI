"""
AI Processor Utility

This module provides a wrapper for making AI requests to various providers
with retry logic, error handling, and proper resource management.
"""

import os
import json
import logging
import time
from typing import Dict, Any, List, Optional, Union
import asyncio

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIProcessor:
    """
    Handles AI processing using OpenAI, Anthropic Claude, or other providers
    with proper error handling and resource management.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the AI processor with configuration options
        
        Args:
            config: Configuration dictionary with provider options
        """
        # Get API keys from environment or config
        self.openai_api_key = config.get('openai_api_key') or os.getenv('OPENAI_API_KEY')
        self.anthropic_api_key = config.get('anthropic_api_key') or os.getenv('ANTHROPIC_API_KEY')
        self.openrouter_api_key = config.get('openrouter_api_key') or os.getenv('OPENROUTER_API_KEY')
        
        # Default provider settings - auto-detect OpenRouter if API key looks like OpenRouter
        provider = config.get('default_provider', 'openai')
        if self.openrouter_api_key and self.openrouter_api_key.startswith('sk-or-'):
            provider = 'openrouter'
            logger.info("Detected OpenRouter API key, setting provider to 'openrouter'")
        
        self.default_provider = provider
        self.default_model = config.get('default_model', {
            'openai': 'gpt-4o-mini',  # Default OpenAI model
            'anthropic': 'claude-3-sonnet-20240229',  # Default Anthropic model 
            'openrouter': 'anthropic/claude-3-sonnet-20240229'  # Up-to-date OpenRouter model ID
        })
        
        # Max tokens/response length settings
        self.max_tokens = config.get('max_tokens', 1000)
        
        # Retry settings
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 1.0)
        
        # Initialize clients as needed
        self.openai_client = None
        self.anthropic_client = None
        
        # Initialize the configured default provider
        self._initialize_default_provider()
        
        logger.info(f"AI Processor initialized with default provider: {self.default_provider}")
        
        # Track active provider for each request
        self.active_provider = None
    
    def _initialize_default_provider(self):
        """Initialize the default provider client"""
        if self.default_provider == 'openai' and self.openai_api_key:
            self.openai_client = AsyncOpenAI(api_key=self.openai_api_key)
            logger.info("OpenAI client initialized")
        elif self.default_provider == 'anthropic' and self.anthropic_api_key:
            self.anthropic_client = AsyncAnthropic(api_key=self.anthropic_api_key)
            logger.info("Anthropic client initialized")
        elif self.default_provider == 'openrouter' and self.openrouter_api_key:
            # OpenRouter uses the OpenAI client with a different base URL
            self.openai_client = AsyncOpenAI(
                api_key=self.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://github.com/sonicscanner/sonicscanner",
                    "X-Title": "SonicKid AI"
                }
            )
            logger.info("OpenRouter client initialized (via OpenAI client)")
        else:
            logger.warning(f"No API key available for {self.default_provider}. Some features may be limited.")
    
    async def generate_response(
        self, 
        query: str,
        context: Optional[Dict[str, Any]] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate a response using the configured AI provider
        
        Args:
            query: The prompt or query text
            context: Additional context for the query (like system prompts)
            provider: Override the default provider
            model: Override the default model
            max_tokens: Override the default max tokens
            
        Returns:
            Generated response text
        """
        # Set active provider for this request
        self.active_provider = provider or self.default_provider
        
        # Track metrics
        start_time = time.time()
        retry_count = 0
        
        # Get configuration for this request
        model_to_use = model or self.default_model.get(self.active_provider)
        tokens_to_use = max_tokens or self.max_tokens
        context_data = context or {}
        
        # Log request details
        logger.info(f"Generating response for query: {query[:50]}...")
        
        # Process based on the active provider with retries
        while retry_count <= self.max_retries:
            try:
                if self.active_provider == 'openai' or self.active_provider == 'openrouter':
                    # Ensure client is initialized
                    if not self.openai_client:
                        if self.active_provider == 'openrouter' and self.openrouter_api_key:
                            self.openai_client = AsyncOpenAI(
                                api_key=self.openrouter_api_key,
                                base_url="https://openrouter.ai/api/v1",
                                default_headers={
                                    "HTTP-Referer": "https://github.com/sonicscanner/sonicscanner",
                                    "X-Title": "SonicKid AI"
                                }
                            )
                        elif self.openai_api_key:
                            self.openai_client = AsyncOpenAI(api_key=self.openai_api_key)
                        else:
                            logger.error(f"No API key available for {self.active_provider}")
                            return "Error: API key not configured"
                    
                    # Construct messages including system prompt if provided
                    messages = []
                    if 'system_prompt' in context_data:
                        messages.append({
                            "role": "system", 
                            "content": context_data['system_prompt']
                        })
                    
                    # Add user message
                    messages.append({"role": "user", "content": query})
                    
                    # Make the API call - OpenRouter uses the OpenAI client with a different base URL,
                    # so the headers are set when initializing the client, not in the request
                    response = await self.openai_client.chat.completions.create(
                        model=model_to_use,
                        messages=messages,
                        max_tokens=tokens_to_use,
                        temperature=context_data.get('temperature', 0.7)
                    )
                    
                    # Extract and return the response text
                    result = response.choices[0].message.content
                    
                elif self.active_provider == 'anthropic':
                    # Ensure client is initialized
                    if not self.anthropic_client:
                        if self.anthropic_api_key:
                            self.anthropic_client = AsyncAnthropic(api_key=self.anthropic_api_key)
                        else:
                            logger.error("No Anthropic API key available")
                            return "Error: Anthropic API key not configured"
                    
                    # Construct system prompt and message
                    system_prompt = context_data.get('system_prompt', '')
                    
                    # Make the API call
                    response = await self.anthropic_client.messages.create(
                        model=model_to_use,
                        system=system_prompt,
                        messages=[{"role": "user", "content": query}],
                        max_tokens=tokens_to_use,
                        temperature=context_data.get('temperature', 0.7)
                    )
                    
                    # Extract and return the response text
                    result = response.content[0].text
                
                else:
                    logger.error(f"Unsupported AI provider: {self.active_provider}")
                    return f"Error: Unsupported AI provider: {self.active_provider}"
                
                # Successfully generated a response
                elapsed_time = time.time() - start_time
                logger.info(f"Response generated successfully. Length: {len(result)} characters")
                logger.debug(f"Response time: {elapsed_time:.2f}s, Retries: {retry_count}")
                
                return result
                
            except Exception as e:
                retry_count += 1
                if retry_count <= self.max_retries:
                    logger.warning(f"Error generating response (attempt {retry_count}): {str(e)}")
                    # Wait before retrying
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to generate response after {self.max_retries} attempts: {str(e)}")
                    return f"Error generating response: {str(e)}"
    
    async def close(self):
        """Clean up resources"""
        # OpenAI client doesn't have an explicit close method
        # Anthropic client doesn't have an explicit close method
        self.active_provider = None
        logger.debug("AI Processor closed")

    def __del__(self):
        """Destructor to ensure proper cleanup"""
        # This is a fallback - always prefer explicit closing with await close()
        logger.debug("AI Processor destroyed")