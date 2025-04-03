"""Tool functions for Telegram bot function calling"""
import logging
import httpx
from typing import Dict, Any, Optional, List
from src.services.dexscreener_service import SONIC
from src.services.service_registry import service_registry

logger = logging.getLogger(__name__)

async def get_sonic_price() -> str:
    """Get the current price of Sonic token"""
    try:
        dex_service = service_registry.dex_service
        if not dex_service:
            return "DexScreener service unavailable"

        price_data = await dex_service.get_token_price("SONIC")
        if not price_data:
            return "Price data unavailable"

        return f"Current Sonic price: ${SONIC['price']:.6f} (24h change: {SONIC['priceChange24h']:+.2f}%)"
    except Exception as e:
        logger.error(f"Error fetching Sonic price: {str(e)}")
        return "Error fetching price data"

async def get_market_news(topic: Optional[str] = None) -> str:
    """Get latest market news, optionally filtered by topic"""
    try:
        crypto_panic = service_registry.crypto_panic
        if not crypto_panic:
            return "News service unavailable"

        news = await crypto_panic.get_latest_news(topic)  
        if not news:
            return "No news available"

        formatted_news = "\n\n".join([
            f"📰 {item['title']}\n🔗 {item['url']}"
            for item in news[:2]
        ])
        return formatted_news
    except Exception as e:
        logger.error(f"Error fetching news: {str(e)}")
        return "Error fetching news"

async def get_market_sentiment() -> str:
    """Analyze current market sentiment"""
    try:
        huggingface = service_registry.huggingface
        if not huggingface:
            return "Sentiment analysis service unavailable"

        sentiment = await huggingface.analyze_market_sentiment("Your txt here")
        if not sentiment:
            return "Sentiment data unavailable"

        return f"Current market sentiment: {sentiment['sentiment']} (confidence: {sentiment['confidence']:.2f})"
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}")
        return "Error analyzing market sentiment"

# Tool registry for easy access
TELEGRAM_TOOLS = {
    'get_sonic_price': get_sonic_price,
    'get_market_news': get_market_news,
    'get_market_sentiment': get_market_sentiment
}
