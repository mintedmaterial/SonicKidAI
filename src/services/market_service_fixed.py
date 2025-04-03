"""Market service implementation with unified sentiment analysis"""
import logging
import json
import re
import os
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from asyncio import Lock
import aiohttp
from src.services.cryptopanic_service import CryptoPanicService
from src.services.huggingface_service import HuggingFaceService
from src.connections.openrouter import OpenRouterConnection
from src.connections.dexscreener_connection import DexScreenerConnection
from src.utils.ai_processor import AIProcessor

logger = logging.getLogger("services.market")

class MarketService:
    """Market service implementation with unified sentiment analysis"""
    def __init__(self, config: Dict[str, Any], equalizer):
        """Initialize market service with unified sentiment analysis"""
        try:
            logger.info("Initializing market service components...")

            # Initialize services and connections
            self._nft_lock = Lock()
            self._cached_news = []
            self._cached_nft_sales = []
            self._last_nft_fetch = 0
            self.price_cache = {}

            # Base URLs for different services
            self.dexscreener_base_url = "https://api.dexscreener.com/latest/dex"

            # Initialize AI processors
            self.ai_processor = AIProcessor({
                'api_key': os.getenv('OPENROUTER_API_KEY')
            })
            logger.info("✅ AI processor initialized with OpenRouter")

            # Initialize other components
            self.cryptopanic = CryptoPanicService()
            self.equalizer = equalizer

            # Initialize aiohttp session
            self.session = aiohttp.ClientSession()

            logger.info("Market service initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing market service: {str(e)}")
            raise

    async def get_llm_response(self, query: str) -> str:
        """Generate market analysis using OpenRouter"""
        try:
            logger.info(f"Generating market analysis for query: {query}")

            # Add context to the query
            market_data = await self._collect_market_data(query)
            formatted_data = self._format_data_for_analysis(market_data) if market_data else query

            # Generate analysis using OpenRouter
            system_prompt = """You are a crypto market expert. Analyze market data and provide clear insights.
            Format your response with sections:
            - Current Market Status
            - Key Opportunities
            - Risk Factors
            - Trading Recommendation
            """

            try:
                response = await self.ai_processor.generate_response(
                    system_prompt=system_prompt,
                    user_message=formatted_data,
                    market_data=market_data
                )
                logger.info("Successfully generated market analysis")
                return response
            except Exception as e:
                logger.error(f"Error calling OpenRouter: {str(e)}")
                return f"Error analyzing market data: {str(e)}"

        except Exception as e:
            logger.error(f"Error in get_llm_response: {str(e)}")
            return "Error processing market analysis request"

    async def analyze_market_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze market sentiment using OpenRouter"""
        try:
            if not text:
                logger.warning("Empty text provided for sentiment analysis")
                return {}
            
            try:
                response = await self.get_llm_response(text)
                if response:
                    logger.info("Successfully analyzed sentiment using OpenRouter")
                    #  Assuming OpenRouter returns a dictionary with sentiment
                    #  This part needs adjustment based on the actual OpenRouter response structure.
                    return {'sentiment': response, 'confidence': 100} # Placeholder, adjust as needed.
            except Exception as e:
                logger.error(f"OpenRouter analysis failed: {str(e)}")
                return {}
        except Exception as e:
            logger.error(f"Error in market sentiment analysis: {str(e)}")
            return {}

    def _format_data_for_analysis(self, data: Dict[str, Any]) -> str:
        """Format market data into text for sentiment analysis"""
        try:
            if 'price' in data:
                return (
                    f"Market update: Current price ${data['price']:.4f}, "
                    f"24h change {data.get('change_24h', 0):+.2f}%, "
                    f"Volume ${data.get('volume_24h', 0):,.2f}, "
                    f"Liquidity ${data.get('liquidity', 0):,.2f}"
                )
            elif 'news' in data:
                return data['news'].get('title', '')
            else:
                return json.dumps(data)
        except Exception as e:
            logger.error(f"Error formatting data for analysis: {str(e)}")
            return str(data)

    async def update_market_knowledge(self, data: Dict[str, Any]) -> str:
        """Update knowledge base with formatted market data"""
        try:
            if not data:
                return ""

            # Get text for sentiment analysis
            text = self._format_data_for_analysis(data)

            # Analyze market data using unified sentiment analysis
            sentiment_analysis = await self.analyze_market_sentiment(text)

            if not sentiment_analysis or "error" in sentiment_analysis:
                logger.error(f"Error analyzing market data: {sentiment_analysis.get('error') if sentiment_analysis else 'No analysis'}")
                return ""

            # Format updates based on data type
            updates = []

            if 'market_data' in data:
                market_update = self._format_market_update_for_knowledge(data['market_data'])
                if market_update:
                    updates.append(market_update)

            if 'price' in data:
                price_update = self._format_price_update(data)
                if price_update:
                    updates.append(price_update)

            if 'news' in data:
                news_update = self._format_news_update(data['news'])
                if news_update:
                    updates.append(news_update)

            # Add sentiment analysis
            if sentiment_analysis:
                sentiment_update = (
                    f"## Market Sentiment Analysis\n"
                    f"- Overall Sentiment: {sentiment_analysis['sentiment']}\n"
                    f"- Confidence: {sentiment_analysis['confidence']}%\n"
                    f"- Analysis: {sentiment_analysis.get('analysis', 'No detailed analysis available')}\n"
                )
                updates.append(sentiment_update)

            return "\n\n".join(updates) if updates else ""

        except Exception as e:
            logger.error(f"Error updating market knowledge: {str(e)}")
            return ""

    def _format_price_update(self, data: Dict[str, Any]) -> str:
        """Format price specific updates"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            return (
                f"# Market Price Update\n"
                f"Timestamp: {current_time}\n\n"
                f"## Price Analysis\n"
                f"Current Price: ${data['price']:,.2f}\n"
                f"24h Price Change: {data.get('change_24h', 0):+.2f}%\n"
                f"Trading Volume: ${data.get('volume_24h', 0):,.2f}\n"
                f"Market Liquidity: ${data.get('liquidity', 0):,.2f}\n\n"
                f"## Market Context\n"
                f"- Notable volume increase in the last 24 hours\n"
                f"- Price movement indicates {self._get_trend_description(data.get('change_24h', 0))}\n"
                f"- Current market sentiment: {self._get_market_sentiment(data)}"
            )
        except Exception as e:
            logger.error(f"Error formatting price update: {str(e)}")
            return ""

    def _format_news_update(self, news: Dict[str, Any]) -> str:
        """Format news specific updates"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            sentiment_result = asyncio.run(self.huggingface.analyze_sentiment(news.get('title', '')))

            return (
                f"# Market News Update\n"
                f"Timestamp: {current_time}\n\n"
                f"## Latest Development\n"
                f"Headline: {news.get('title', '')}\n"
                f"Source: {news.get('source', '')}\n"
                f"URL: {news.get('url', '')}\n\n"
                f"## Impact Analysis\n"
                f"- Sentiment: {sentiment_result.get('label', 'neutral')}\n"
                f"- Confidence: {sentiment_result.get('score', 0)*100:.1f}%\n"
                f"- Related market sectors: {', '.join(news.get('sectors', ['General']))}"
            )
        except Exception as e:
            logger.error(f"Error formatting news update: {str(e)}")
            return ""

    def _format_market_update_for_knowledge(self, data: Dict[str, Any]) -> str:
        """Format market data as a knowledge base prompt"""
        try:
            if not data:
                return ""

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

            # Format based on update type
            if 'price' in data:
                return (
                    f"# Market Price Update\n"
                    f"Timestamp: {current_time}\n\n"
                    f"## Price Analysis\n"
                    f"Current Price: ${data['price']:,.2f}\n"
                    f"24h Price Change: {data.get('change_24h', 0):+.2f}%\n"
                    f"Trading Volume: ${data.get('volume_24h', 0):,.2f}\n"
                    f"Market Liquidity: ${data.get('liquidity', 0):,.2f}\n\n"
                    f"## Market Context\n"
                    f"- Notable volume increase in the last 24 hours\n"
                    f"- Price movement indicates {self._get_trend_description(data.get('change_24h', 0))}\n"
                    f"- Current market sentiment: {self._get_market_sentiment(data)}"
                )
            elif 'results' in data:  # News update
                news = data['results'][0]  # Take first news item
                sentiment_result = asyncio.run(self.huggingface.analyze_sentiment(news.get('title', '')))

                return (
                    f"# Market News Update\n"
                    f"Timestamp: {current_time}\n\n"
                    f"## Latest Development\n"
                    f"Headline: {news.get('title', '')}\n"
                    f"Source: {news.get('source', '')}\n"
                    f"URL: {news.get('url', '')}\n\n"
                    f"## Impact Analysis\n"
                    f"- Sentiment: {sentiment_result.get('label', 'neutral')}\n"
                    f"- Confidence: {sentiment_result.get('score', 0)*100:.1f}%\n"
                    f"- Related market sectors: {', '.join(news.get('sectors', ['General']))}"
                )

            return ""
        except Exception as e:
            logger.error(f"Error formatting market update for knowledge: {str(e)}")
            return ""

    def _get_trend_description(self, change_24h: float) -> str:
        """Get descriptive trend based on price change"""
        if change_24h > 10:
            return "strong bullish momentum"
        elif change_24h > 5:
            return "moderate upward trend"
        elif change_24h > 0:
            return "slight positive movement"
        elif change_24h > -5:
            return "slight negative movement"
        elif change_24h > -10:
            return "moderate downward trend"
        else:
            return "strong bearish pressure"

    def _get_market_sentiment(self, data: Dict[str, Any]) -> str:
        """Analyze market sentiment based on multiple factors"""
        try:
            price_change = data.get('change_24h', 0)
            volume = data.get('volume_24h', 0)
            liquidity = data.get('liquidity', 0)

            # Simple sentiment analysis based on price and volume
            if price_change > 5 and volume > liquidity * 0.1:
                return "Strongly Bullish"
            elif price_change > 0 and volume > liquidity * 0.05:
                return "Moderately Bullish"
            elif price_change < -5 and volume > liquidity * 0.1:
                return "Strongly Bearish"
            elif price_change < 0 and volume > liquidity * 0.05:
                return "Moderately Bearish"
            else:
                return "Neutral"
        except Exception:
            return "Unknown"

    async def get_token_info_v1(self, query: str) -> str:
        """Compatibility layer for v1 consumers"""
        return await self.get_token_info(query)

    async def get_token_info(self, query: str) -> str:
        """Get token market data using DexScreener search endpoint"""
        try:
            # Extract chain identifier and contract address
            chain_match = re.search(r'\$[A-Z]+', query)
            address_match = re.search(r'0x[a-fA-F0-9]{40}', query)

            if not address_match:
                return "❌ Please provide contract address"

            contract_address = address_match.group()
            chain_name = 'sonic'  # Default to Sonic chain

            if chain_match:
                chain_name = chain_match.group().replace('$', '').lower()

            # Search using DexScreener search endpoint
            url = f"{self.dexscreener_base_url}/search"
            search_query = f"Sonic/USDC {contract_address}" if chain_name.lower() == 'sonic' else contract_address

            async with self.session.get(url, params={'q': search_query}) as response:
                if response.status != 200:
                    logger.error(f"DexScreener API error: {await response.text()}")
                    return "❌ Error fetching market data"

                data = await response.json()
                pairs = data.get('pairs', [])

            if not pairs:
                return f"❌ No pair data found for {contract_address} on {chain_name}"

            # Find pair with highest liquidity
            pair = max(pairs, key=lambda x: float(x.get('liquidity', {}).get('usd', 0) or 0))

            # Cache pair data
            self.price_cache[contract_address] = {
                'dex_price': float(pair.get('priceUsd', 0)),
                'volume': float(pair.get('volume', {}).get('h24', 0) or 0),
                'liquidity': float(pair.get('liquidity', {}).get('usd', 0) or 0),
                'timestamp': datetime.now()
            }

            # Format response
            indicator = "🟢" if float(pair.get('priceChange', {}).get('h24', 0) or 0) >= 0 else "🔴"
            return (
                f"📊 {pair.get('chainId', 'Unknown').upper()} - {pair.get('dexId', 'Unknown')}\n"
                f"{indicator} USD: ${float(pair.get('priceUsd', 0)):.8f}\n"
                f"💰 Native: {float(pair.get('priceNative', 0)):.8f}\n"
                f"📈 24h Change: {float(pair.get('priceChange', {}).get('h24', 0) or 0):+.2f}%\n"
                f"💫 24h Volume: ${float(pair.get('volume', {}).get('h24', 0) or 0):,.0f}\n"
                f"💎 Liquidity: ${float(pair.get('liquidity', {}).get('usd', 0) or 0):,.0f}"
            )

        except Exception as e:
            logger.error(f"Error fetching token info: {str(e)}")
            return "❌ Error processing market data"

    async def get_token_price(self, token_address: str) -> float:
        """Get token price in USD using DexScreener"""
        try:
            # Extract chain identifier and contract address
            chain_match = re.search(r'\$[A-Z]+', token_address)
            address_match = re.search(r'0x[a-fA-F0-9]{40}', token_address)

            if not address_match:
                logger.error("Invalid token address format")
                return 0.0

            contract_address = address_match.group()
            chain_name = 'sonic'  # Default to Sonic chain

            if chain_match:
                chain_name = chain_match.group().replace('$', '').lower()

            # Search using DexScreener search endpoint
            url = f"{self.dexscreener_base_url}/search"
            search_query = f"Sonic/USDC {contract_address}" if chain_name.lower() == 'sonic' else contract_address

            async with self.session.get(url, params={'q': search_query}) as response:
                if response.status != 200:
                    logger.error(f"DexScreener API error: {await response.text()}")
                    return 0.0

                data = await response.json()
                pairs = data.get('pairs', [])

            if not pairs:
                logger.warning(f"No pair data found for {contract_address}")
                return 0.0

            # Find pair with highest liquidity and return its price
            pair = max(pairs, key=lambda x: float(x.get('liquidity', {}).get('usd', 0) or 0))
            price = float(pair.get('priceUsd', 0))

            # Cache the price
            self.price_cache[contract_address] = {
                'price': price,
                'timestamp': datetime.now()
            }

            return price

        except Exception as e:
            logger.error(f"Error fetching token price: {str(e)}")
            return 0.0

    async def connect(self):
        """Initialize connections"""
        try:
            logger.info("Connecting to services...")
            #await self.tophat.connect()  Removed TopHat connection
            logger.info("Successfully connected all services")
            return True
        except Exception as e:
            logger.error(f"Error connecting market service: {str(e)}")
            return False

    async def get_latest_news(self, force_refresh=False) -> str:
        """Get latest market news with sentiment analysis"""
        try:
            # Get news from CryptoPanic service
            news_items: List[Dict[str, Any]] = await self.cryptopanic.get_news(limit=5)

            if not news_items:
                return "No recent news available"

            # Analyze news sentiment using HuggingFace
            analyzed_news = await self.huggingface.analyze_news_impact(news_items)

            # Format response
            response = ["📰 Latest Market News\n"]

            for item in analyzed_news:
                sentiment_icon = "🟢" if item['sentiment'] == 'bullish' else "🔴" if item['sentiment'] == 'bearish' else "⚪"
                response.append(
                    f"{sentiment_icon} {item['title']}\n"
                    f"Sentiment: {item['sentiment'].title()} ({item['confidence']}% confidence)\n"
                    f"Impact: {item['impact'].replace('_', ' ').title()}\n"
                )

            return "\n".join(response)

        except Exception as e:
            logger.error(f"Error getting latest news: {str(e)}")
            return "Error fetching market news"

    async def get_market_sentiment(self) -> str:
        """Get overall market sentiment analysis"""
        try:
            # Use SONIC token address as default for market sentiment
            default_token = "0xF5C4a9B6cF54913E0B94eB1bA3A730A6Bd0E6E97"  # SONIC token

            market_data = await self._collect_market_data(default_token)
            if not market_data:
                return "Unable to collect market data for analysis"

            # Convert market data to text
            text = self._format_data_for_analysis(market_data)

            # Get sentiment analysis
            analysis = await self.analyze_market_sentiment(text)

            if not analysis:
                return "Unable to analyze market sentiment"

            # Format response
            response = [
                "📊 Market Sentiment Analysis",
                f"Overall Sentiment: {analysis['sentiment']}",
                f"Confidence: {analysis['confidence']}%",
                "\nDetailed Analysis:",
                analysis.get('analysis', 'No detailed analysis available')
            ]

            # Add metrics if available
            if 'metrics' in analysis:
                metrics = analysis['metrics']
                response.extend([
                    "\nKey Metrics:",
                    f"Price Movement: {metrics.get('price_change', 0):+.2f}%",
                    f"Volume/Liquidity Ratio: {metrics.get('volume_liquidity_ratio', 0):.2f}",
                    f"Market Momentum: {metrics.get('momentum', 'neutral').replace('_', ' ').title()}"
                ])

            return "\n".join(response)

        except Exception as e:
            logger.error(f"Error getting market sentiment: {str(e)}")
            return "Error analyzing market sentiment"

    async def _collect_market_data(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Collect market data for sentiment analysis"""
        try:
            # Get token price and market data
            price_data = await self.get_token_price(token_address)

            market_data = {
                'price': price_data,
                'change_24h': 0.0,
                'volume_24h': 0.0,
                'liquidity': 0.0,
            }

            # Get additional market metrics from DexScreener
            try:
                url = f"{self.dexscreener_base_url}/search"
                async with self.session.get(url, params={'q': f"SONIC/USDC {token_address}"}) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('pairs'):
                            pair = data['pairs'][0]
                            market_data.update({
                                'change_24h': float(pair.get('priceChange', {}).get('h24', 0) or 0),
                                'volume_24h': float(pair.get('volume', {}).get('h24', 0) or 0),
                                'liquidity': float(pair.get('liquidity', {}).get('usd', 0) or 0)
                            })
            except Exception as e:
                logger.error(f"Error fetching additional market data: {str(e)}")

            return market_data

        except Exception as e:
            logger.error(f"Error collecting market data: {str(e)}")
            return None