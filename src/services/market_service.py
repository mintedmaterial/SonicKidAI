"""Market service implementation with unified sentiment analysis and OpenRouter integration"""
import logging
from typing import Dict, Any, Optional, List, Mapping
from services.huggingface_service import HuggingFaceService
from connections.dexscreener_connection import DexScreenerConnection
from services.market_data_service import MarketDataService
from storage import storage  # Updated import path
from utils.ai_processor import AIProcessor
from datetime import datetime
import aiohttp
import asyncio
import os

logger = logging.getLogger("services.market")

class MarketService:
    """Market service with enhanced data handling"""

    def __init__(self, config: Dict[str, Any], equalizer: Any, openrouter: Any, db_pool: Any):
        """Initialize market service with required components"""
        try:
            logger.info("Initializing market service components...")

            self.config = config
            self.equalizer = equalizer
            self.openrouter = openrouter
            self._db_pool = db_pool
            self._initialized = False
            self.storage = storage
            self._lock = asyncio.Lock()
            self._closing = False

            # Validate configuration
            if not isinstance(config, dict):
                raise ValueError("Config must be a dictionary")

            self.api_key = config.get('api_key')
            if not self.api_key:
                raise ValueError("API key not found in configuration")
                
            # Initialize AI processor - properly setting OpenRouter API
            # Check if the API key has the OpenRouter format
            is_openrouter = self.api_key and isinstance(self.api_key, str) and self.api_key.startswith('sk-or-')
            
            ai_config = {
                'openrouter_api_key': self.api_key if is_openrouter else None,
                'openai_api_key': None if is_openrouter else self.api_key,
                'default_provider': 'openrouter' if is_openrouter else 'openai',
                'model': 'anthropic/claude-3-sonnet-20240229'
            }
            
            logger.info(f"Initializing AI processor with provider: {'openrouter' if is_openrouter else 'openai'}")
            self.ai_processor = AIProcessor(ai_config)
            
            logger.info("Market service initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing market service: {str(e)}")
            raise

    async def get_market_data(self, chain: str, token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get market data from database with fallback to live DexScreener"""
        try:
            logger.info(f"Fetching market data for chain: {chain}, token: {token}")

            # Try to get data from database first
            pairs = await self.storage.getLatestPrices(chain)
            if pairs:
                logger.info(f"Retrieved {len(pairs)} pairs from database")

                # Filter by token if specified
                if token:
                    pairs = [p for p in pairs if token.lower() in p['baseToken'].lower()]
                    logger.info(f"Filtered to {len(pairs)} pairs matching token: {token}")

                # Sort by liquidity and volume
                pairs.sort(key=lambda x: (float(x.get('liquidity', 0)), float(x.get('volume24h', 0))), reverse=True)

                # Check if data is stale (older than 10 minutes)
                if pairs and (datetime.now() - pairs[0]['timestamp']).total_seconds() > 600:
                    logger.warning("Database data is stale, fetching fresh data")
                    return await self._fetch_live_data(chain, token)

                return pairs[:5]  # Return top 5 pairs

            return await self._fetch_live_data(chain, token)

        except Exception as e:
            logger.error(f"Error getting market data: {str(e)}")
            return []

    async def _fetch_live_data(self, chain: str, token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch fresh data from DexScreener"""
        try:
            if hasattr(self, 'dexscreener'):
                logger.info("Fetching fresh data from DexScreener")
                query = f"{chain} {token}" if token else chain
                return await self.dexscreener.get_pairs(query)

            logger.warning("No DexScreener service available")
            return []
        except Exception as e:
            logger.error(f"Error fetching live data: {str(e)}")
            return []

    async def get_price_and_volume(self, symbol: str, chain: str) -> Dict[str, Any]:
        """Get price and volume data from database"""
        try:
            logger.info(f"Fetching price data for {symbol} on {chain}")
            pairs = await self.storage.getLatestPrices(chain)

            if not pairs:
                logger.warning(f"No price data found for {symbol} on {chain}")
                return {
                    'price': 0,
                    'volume24h': 0,
                    'priceChange24h': 0,
                    'liquidity': 0
                }

            # Find matching pair
            for pair in pairs:
                if symbol.lower() in pair['baseToken'].lower():
                    logger.info(f"Found matching pair for {symbol}: {pair['pairSymbol']}")
                    return {
                        'price': float(pair['priceUsd']),
                        'volume24h': float(pair['volume24h']),
                        'priceChange24h': float(pair['priceChange24h']),
                        'liquidity': float(pair['liquidity'])
                    }

            logger.warning(f"No matching pair found for {symbol}")
            return {
                'price': 0,
                'volume24h': 0,
                'priceChange24h': 0,
                'liquidity': 0
            }

        except Exception as e:
            logger.error(f"Error getting price data: {str(e)}")
            return {
                'price': 0,
                'volume24h': 0,
                'priceChange24h': 0,
                'liquidity': 0
            }

    async def format_market_data(self, pairs: List[Dict[str, Any]]) -> str:
        """Format market data consistently for both Discord and Telegram"""
        try:
            if not pairs:
                return "No market data available"

            response = "📊 Market Data:\n\n"
            for pair in pairs[:5]:  # Show top 5 pairs
                try:
                    price = float(pair['priceUsd'])
                    change = float(pair.get('priceChange24h', 0))
                    volume = float(pair.get('volume24h', 0))
                    liquidity = float(pair.get('liquidity', 0))

                    # Add data age indicator if available
                    age_indicator = ""
                    if 'timestamp' in pair:
                        age_seconds = (datetime.now() - pair['timestamp']).total_seconds()
                        if age_seconds < 60:
                            age_indicator = "🟢"  # Fresh data
                        elif age_seconds < 300:
                            age_indicator = "🟡"  # Slightly aged
                        else:
                            age_indicator = "🔴"  # Stale data

                    response += (
                        f"**{pair['pairSymbol']}** {age_indicator}\n"
                        f"• Price: ${price:.8f}\n"
                        f"• 24h Change: {change:+.2f}%\n"
                        f"• Volume: ${volume:,.2f}\n"
                        f"• Liquidity: ${liquidity:,.2f}\n\n"
                    )

                    logger.debug(f"Formatted pair data: {pair['pairSymbol']}")
                except (ValueError, KeyError) as e:
                    logger.error(f"Error formatting pair data: {str(e)}")
                    continue

            return response

        except Exception as e:
            logger.error(f"Error formatting market data: {str(e)}")
            return "Error formatting market data"

    async def get_llm_response(self, query: str) -> str:
        """Generate market analysis using OpenRouter"""
        try:
            logger.info(f"Generating market analysis for query: {query}")

            # Create context-aware prompt with Sonic market context - optimized for concise responses
            prompt = f"""As a crypto analyst, provide a very brief analysis of this query:
            Query: {query}
            
            Context: Sonic is a Layer 2 blockchain on Cosmos with IBC support. SONIC token is used for gas, governance, and staking.
            Current metrics: ~$1B TVL, ~$70M daily DEX volume, rapidly expanding ecosystem.
            
            Be extremely concise - total response under 100 words. Focus on clear signals only.
            Format as brief bullet points:
            • Market Status: (1-2 sentence overview)
            • Outlook: (bullish/neutral/bearish + one key reason)
            • Action: (simple buy/hold/sell recommendation)
            
            Avoid disclaimers or overly detailed explanations.
            """

            logger.debug(f"Sending prompt to OpenRouter: {prompt[:200]}...")

            try:
                # Create context with system prompt enforcing brevity
                context = {
                    "system_prompt": "You are a crypto market expert. Provide extremely concise insights in under 100 words total. Focus on clarity and actionable information."
                }
                response = await self.ai_processor.generate_response(query=prompt, context=context)
                logger.info("Successfully generated market analysis")
                logger.debug(f"OpenRouter response preview: {str(response)[:200]}")
                return response
            except Exception as e:
                logger.error(f"Error calling OpenRouter: {str(e)}")
                return f"Error analyzing market data: {str(e)}"

        except Exception as e:
            logger.error(f"Error in get_llm_response: {str(e)}")
            return "Error processing market analysis request"

    async def connect(self) -> bool:
        """Initialize market service connection"""
        try:
            logger.info("Connecting market service...")
            async with self._lock:
                if not self._initialized:
                    # Initialize the required services
                    self.dexscreener = DexScreenerConnection(config={})
                    self.market_data = MarketDataService()
                    self.huggingface = HuggingFaceService(self.openrouter)

                    # Initialize market data service first
                    await self.market_data.initialize()
                    logger.info("Market data service initialized")

                    # Start DexScreener updates
                    success = await self.dexscreener.start_background_updates()
                    if not success:
                        logger.error("Failed to start DexScreener background updates")
                        return False
                    logger.info("DexScreener service started")

                    self._initialized = True
                    logger.info("Market service connected successfully")
            return True
        except Exception as e:
            logger.error(f"Error connecting market service: {str(e)}")
            return False

    async def close(self) -> None:
        """Cleanup market service resources"""
        try:
            if self._initialized:
                self._closing = True
                async with self._lock:
                    self._initialized = False

                    # Close DexScreener service
                    if hasattr(self, 'dexscreener'):
                        try:
                            await self.dexscreener.close()
                        except Exception as e:
                            logger.error(f"Error closing DexScreener service: {str(e)}")

                    # Close market data service
                    if hasattr(self, 'market_data'):
                        try:
                            await self.market_data.close()
                        except Exception as e:
                            logger.error(f"Error closing market data service: {str(e)}")

                    # Close HuggingFace service if it has a close method
                    if hasattr(self, 'huggingface') and hasattr(self.huggingface, 'close'):
                        try:
                            await self.huggingface.close()
                        except Exception as e:
                            logger.error(f"Error closing HuggingFace service: {str(e)}")

                    logger.info("Market service closed successfully")
        except Exception as e:
            logger.error(f"Error closing market service: {str(e)}")
        finally:
            self._closing = False

    async def get_token_info(self, token: str) -> Dict[str, Any]:
        """Get token information using database"""
        try:
            logger.info(f"Fetching token info for: {token}")

            #Attempt to get from database
            token_info = await self.get_market_data(chain='any', token=token)
            if token_info:
                return token_info[0] #Return the first result if found

            #Return mock data if database lookup failed.
            return {
                'price': 1.25,
                'change_24h': 5.5,
                'volume_24h': 1500000,
                'liquidity': 5000000,
                'sentiment': {
                    'sentiment': 'bullish',
                    'confidence': 75.5,
                    'source': 'mock'
                }
            }
        except Exception as e:
            logger.error(f"Error getting token info: {str(e)}")
            return {
                'error': str(e),
                'price': 0,
                'change_24h': 0,
                'volume_24h': 0,
                'liquidity': 0,
                'sentiment': {
                    'sentiment': 'neutral',
                    'confidence': 0,
                    'source': 'error'
                }
            }

    async def get_top_pairs(self, limit: int = 2) -> List[Dict[str, Any]]:
        """Get top trading pairs from database"""
        try:
            logger.info(f"Fetching top {limit} pairs")
            pairs = await self.get_market_data(chain='any')
            return pairs[:limit]
        except Exception as e:
            logger.error(f"Error getting top pairs: {str(e)}")
            return []

    async def get_trading_signals(self) -> str:
        """Get trading signals with sentiment analysis"""
        try:
            # Get market data from our market data service
            pairs = await self.get_token_info("SONIC")
            if not pairs:
                return "❌ Unable to fetch market data for trading signals"

            # Prepare market summary
            summary = (
                f"Price: ${pairs.get('price', 0)}, "
                f"24h Change: {pairs.get('change_24h', 0)}%, "
                f"Volume 24h: ${pairs.get('volume_24h', 0)}, "
                f"Liquidity: ${pairs.get('liquidity', 0)}"
            )

            # Get sentiment analysis
            sentiment = pairs.get('sentiment', {})
            if sentiment:
                return (
                    f"📊 Trading Signals:\n\n"
                    f"Market Data:\n{summary}\n\n"
                    f"Analysis:\n"
                    f"Sentiment: {sentiment.get('sentiment', 'neutral')}\n"
                    f"Confidence: {sentiment.get('confidence', 0)}%\n"
                    f"Source: {sentiment.get('source', 'unknown')}"
                )

            return f"📊 Market Summary:\n{summary}"

        except Exception as e:
            logger.error(f"Error getting trading signals: {str(e)}")
            return "❌ Error generating trading signals"

    async def _handle_api_error(self, error: Exception) -> Dict[str, Any]:
        """Handle API errors with proper type checking"""
        error_message = str(error)
        if isinstance(error, aiohttp.ClientError):
            return {"error": f"Connection error: {error_message}"}
        if isinstance(error, asyncio.TimeoutError):
            return {"error": "Request timed out"}
        return {"error": f"Unexpected error: {error_message}"}

    async def get_pair_by_id(self, pair_id: str) -> Optional[Dict[str, Any]]:
        """Get pair information by ID with proper type handling"""
        try:
            if not pair_id:
                return None
            pairs = await self.dexscreener.get_pairs(pair_id)
            if pairs and isinstance(pairs, list) and len(pairs) > 0:
                return pairs[0]
            return None
        except Exception as e:
            logger.error(f"Error getting pair by ID: {str(e)}")
            return None

    def _extract_contract_address(self, text: str) -> Optional[str]:
        """Extract Ethereum-style contract address from text"""
        import re
        address_pattern = r'0x[a-fA-F0-9]{40}'
        match = re.search(address_pattern, text)
        return match.group(0) if match else None

    async def analyze_market_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze market sentiment using AI processor"""
        try:
            sentiment_result = await self.huggingface.analyze_market_sentiment(text)
            logger.info(f"Market sentiment analysis completed: {sentiment_result}")
            return sentiment_result
        except Exception as e:
            logger.error(f"Error in market sentiment analysis: {str(e)}")
            return {
                'sentiment': 'neutral',
                'confidence': 0,
                'source': 'market_service'
            }

    #Chain mappings for DEX analytics 
    chain_mappings: Mapping[str, Dict[str, Any]] = {
        '$SONIC': {'name': 'Sonic', 'chain_id': '146'},
        '$ETH': {'name': 'Ethereum', 'chain_id': '1'}, 
        '$ARB': {'name': 'Arbitrum', 'chain_id': '42161'},
        '$OP': {'name': 'Optimism', 'chain_id': '10'}
    }