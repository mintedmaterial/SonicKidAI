"""HuggingFace service for AI market analysis using CryptoBERT - Distributed Processing"""
import logging
import asyncio
from typing import Dict, Any, Optional, List
import json
from openai import AsyncOpenAI
from workers.sentiment_worker import SentimentWorker

logger = logging.getLogger(__name__)

class HuggingFaceService:
    """Service for HuggingFace model inference with worker offloading"""
    _instance = None
    _cache = {}
    _cache_ttl = 300  # 5 minutes
    _cache_size = 1000  # Maximum cache entries

    def __new__(cls, *args, **kwargs):
        """Ensure single instance - Singleton pattern"""
        if cls._instance is None:
            cls._instance = super(HuggingFaceService, cls).__new__(cls)
        return cls._instance

    def __init__(self, openrouter_service=None):
        """Initialize service with worker"""
        logger.info("Initializing HuggingFace service...")
        self.worker = SentimentWorker()
        
        # Handle dict or object for openrouter_service
        api_key = None
        if openrouter_service:
            if isinstance(openrouter_service, dict):
                api_key = openrouter_service.get('api_key')
            elif hasattr(openrouter_service, 'api_key'):
                api_key = openrouter_service.api_key
                
        self.openai_client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        ) if api_key else None
        
        logger.info("✅ HuggingFace service initialized")

    async def initialize(self):
        """Initialize the worker"""
        await self.worker.initialize()

    async def _openrouter_fallback(self, text: str) -> Dict[str, Any]:
        """Use OpenRouter for sentiment analysis"""
        try:
            if not self.openai_client:
                return {"error": "OpenRouter not available"}

            logger.info("Using OpenRouter for sentiment analysis")

            # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
            prompt = (
                "Analyze the following text for crypto market sentiment. "
                "Provide analysis in JSON format with: "
                "- sentiment: 'bullish' or 'bearish' "
                "- confidence: number between 0-100 "
                "- analysis: brief explanation\n\n"
                f"Text: {text}"
            )

            response = await self.openai_client.chat.completions.create(
                model="anthropic/claude-3-5-sonnet-20241022",  # Use latest Anthropic model
                messages=[
                    {"role": "system", "content": "You are a crypto market sentiment analyzer."},
                    {"role": "user", "content": text}
                ],
                response_format={"type": "json_object"}
            )

            try:
                result = json.loads(response.choices[0].message.content)
                result['source'] = 'openrouter'
                return result
            except Exception as e:
                logger.error(f"Error parsing OpenRouter response: {str(e)}")

            return {"error": "Failed to parse OpenRouter response"}

        except Exception as e:
            logger.error(f"OpenRouter analysis failed: {str(e)}")
            return {"error": str(e)}

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return f"sentiment_{hash(text)}"

    def _get_cached_result(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if valid"""
        from time import time
        if key in self._cache:
            result, timestamp = self._cache[key]
            if (time() - timestamp) < self._cache_ttl:
                return result
            del self._cache[key]
        return None

    def _cache_result(self, key: str, result: Dict[str, Any]):
        """Cache result with timestamp"""
        from time import time
        if len(self._cache) >= self._cache_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
        self._cache[key] = (result, time())

    async def analyze_market_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze market sentiment using worker with caching"""
        try:
            # Fast path for empty or invalid input
            if not text or not isinstance(text, str):
                logger.warning("Empty or invalid text provided for sentiment analysis")
                return {
                    "sentiment": "neutral",
                    "confidence": 50.0,
                    "source": "default",
                    "error": "No text provided"
                }

            cache_key = self._get_cache_key(text)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.debug("Using cached sentiment result")
                return cached_result

            # Create a future to store the result
            result_future = asyncio.Future()

            async def callback(result):
                if not result_future.done():
                    result_future.set_result(result)

            # Submit task to worker
            await self.worker.submit_task(text, callback)

            # Wait for result with timeout
            try:
                result = await asyncio.wait_for(result_future, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Sentiment analysis timed out, using fallback")
                return {
                    "sentiment": "neutral",
                    "confidence": 50.0,
                    "source": "timeout_fallback"
                }

            if "error" not in result:
                formatted_result = {
                    "sentiment": result["label"],
                    "confidence": round(result["score"] * 100, 2),
                    "raw_score": result["score"],
                    "source": result["source"]
                }
                self._cache_result(cache_key, formatted_result)
                return formatted_result

            return await self._openrouter_fallback(text)

        except Exception as e:
            logger.error(f"Error in market sentiment analysis: {str(e)}")
            return {
                "sentiment": "neutral",
                "confidence": 50.0,
                "source": "error_fallback",
                "error": str(e)
            }

    async def analyze_market_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market data using worker"""
        try:
            # Fast path for empty data during initialization
            if not data:
                logger.info("Empty data received during initialization")
                return {
                    "sentiment": "neutral",
                    "confidence": 50.0,
                    "metrics": {},
                    "source": "initialization",
                    "analysis": "No market data available"
                }

            text = self._format_market_data(data)
            sentiment_result = await self.analyze_market_sentiment(text)

            if "error" in sentiment_result:
                return {
                    "error": "Market analysis failed",
                    "details": sentiment_result["error"]
                }

            metrics = self._extract_market_metrics(data)

            return {
                "sentiment": sentiment_result["sentiment"],
                "confidence": sentiment_result["confidence"],
                "metrics": metrics,
                "source": sentiment_result.get("source", "cryptobert"),
                "analysis": self._generate_market_analysis(sentiment_result, metrics)
            }

        except Exception as e:
            logger.error(f"Error analyzing market data: {str(e)}")
            return {
                "error": str(e),
                "sentiment": "neutral",
                "confidence": 50.0,
                "metrics": {},
                "source": "error",
                "analysis": "Error analyzing market data"
            }

    def _format_market_data(self, data: Dict[str, Any]) -> str:
        """Format market data into analyzable text"""
        try:
            lines = [
                "Market Analysis Report",
                f"Current Price: ${data.get('price', 0):,.2f}",
                f"24h Change: {data.get('change_24h', 0):+.2f}%",
                f"Volume: ${data.get('volume_24h', 0):,.2f}",
                f"Liquidity: ${data.get('liquidity', 0):,.2f}"
            ]
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error formatting market data: {str(e)}")
            return str(data)

    def _extract_market_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and calculate key market metrics"""
        try:
            return {
                "price_change": data.get('change_24h', 0),
                "volume_liquidity_ratio": data.get('volume_24h', 0) / max(data.get('liquidity', 1), 1),
                "momentum": self._calculate_momentum(data),
                "volatility": abs(data.get('change_24h', 0)) > 5
            }
        except Exception as e:
            logger.error(f"Error extracting metrics: {str(e)}")
            return {}

    def _calculate_momentum(self, data: Dict[str, Any]) -> str:
        """Calculate market momentum indicator"""
        try:
            price_change = data.get('change_24h', 0)
            volume_change = data.get('volume_change_24h', 0)

            if price_change > 5 and volume_change > 10:
                return "strong_bullish"
            elif price_change > 2 and volume_change > 5:
                return "moderate_bullish"
            elif price_change < -5 and volume_change > 10:
                return "strong_bearish"
            elif price_change < -2 and volume_change > 5:
                return "moderate_bearish"
            return "neutral"
        except Exception:
            return "neutral"

    def _generate_market_analysis(self, sentiment: Dict[str, Any], metrics: Dict[str, Any]) -> str:
        """Generate comprehensive market analysis"""
        try:
            momentum = metrics.get('momentum', 'neutral')
            vol_liq_ratio = metrics.get('volume_liquidity_ratio', 0)

            analysis = []

            # Sentiment analysis
            if sentiment['confidence'] > 80:
                analysis.append(f"Strong {sentiment['sentiment']} sentiment with {sentiment['confidence']}% confidence")
            else:
                analysis.append(f"Moderate {sentiment['sentiment']} sentiment detected")

            # Momentum analysis
            if momentum != 'neutral':
                analysis.append(f"Showing {momentum.replace('_', ' ')} momentum")

            # Volume analysis
            if vol_liq_ratio > 0.5:
                analysis.append("High trading activity relative to liquidity")
            elif vol_liq_ratio > 0.2:
                analysis.append("Moderate trading activity")
            else:
                analysis.append("Low trading activity")

            return " | ".join(analysis)

        except Exception as e:
            logger.error(f"Error generating analysis: {str(e)}")
            return "Analysis unavailable"

    async def analyze_news_impact(self, news_articles: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Analyze the sentiment and market impact of news articles.

        Args:
            news_articles: List of dictionaries containing news articles with 'title' and 'description' keys

        Returns:
            List of dictionaries containing sentiment analysis for each article:
            - title: Original article title
            - sentiment: bullish/bearish/neutral
            - confidence: 0-100 confidence score
            - impact: high/medium/low based on confidence and content
            - source: Analysis source (bert_analysis/fallback)
        """
        try:
            results = []
            for article in news_articles:
                # Combine title and description for analysis
                text = f"{article['title']} {article.get('description', '')}"

                # Get sentiment analysis
                sentiment_result = await self.analyze_market_sentiment(text)

                # Determine impact based on confidence
                confidence = sentiment_result.get('confidence', 0)
                impact = 'high' if confidence > 85 else 'medium' if confidence > 70 else 'low'

                result = {
                    'title': article['title'],
                    'sentiment': sentiment_result.get('sentiment', 'neutral'),
                    'confidence': confidence,
                    'impact': impact,
                    'source': sentiment_result.get('source', 'unknown')
                }
                results.append(result)

            logger.info(f"Analyzed impact of {len(results)} news articles")
            return results

        except Exception as e:
            logger.error(f"Error analyzing news impact: {str(e)}")
            return [{
                'title': article.get('title', 'Unknown'),
                'sentiment': 'neutral',
                'confidence': 0,
                'impact': 'low',
                'source': 'error'
            } for article in news_articles]

    async def shutdown(self):
        """Shutdown the service and worker"""
        logger.info("Shutting down HuggingFace service...")
        await self.worker.shutdown()
        logger.info("✅ HuggingFace service shutdown complete")

    def __del__(self):
        """Cleanup resources"""
        try:
            if self._instance == self:
                asyncio.create_task(self.worker.shutdown())
        except Exception:
            pass