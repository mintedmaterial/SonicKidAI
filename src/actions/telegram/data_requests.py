"""Handlers for Telegram data request commands"""
import logging
from typing import Dict, Any, Optional, List, Callable

logger = logging.getLogger(__name__)

async def handle_trending_command(
    crypto_panic=None,
    huggingface=None,
    market_service=None
) -> str:
    """Handle trending command to get popular market topics"""
    try:
        if not crypto_panic:
            logger.warning("Trending command attempted but CryptoPanic service is not available")
            return "⚠️ Trending data service is currently unavailable."

        trending_data = await crypto_panic.get_trending_topics()
        
        if not trending_data or "error" in trending_data:
            logger.warning(f"Error fetching trending data: {trending_data.get('error') if trending_data else 'No data'}")
            return "❌ Could not fetch trending topics. Please try again later."
        
        # Format the response with emoji indicators based on sentiment
        formatted_response = "🔥 <b>Trending Crypto Topics</b> 🔥\n\n"
        
        for topic in trending_data[:5]:  # Limit to top 5 topics
            symbol = topic.get("symbol", "")
            title = topic.get("title", "Unknown Topic")
            sentiment = topic.get("sentiment", "neutral")
            
            # Add sentiment emoji
            if sentiment.lower() == "bullish":
                emoji = "🟢"
            elif sentiment.lower() == "bearish":
                emoji = "🔴"
            else:
                emoji = "⚪"
                
            formatted_response += f"{emoji} <b>{symbol}</b>: {title}\n"
            
        return formatted_response
        
    except Exception as e:
        logger.error(f"Error in handle_trending_command: {str(e)}", exc_info=True)
        return "❌ Error processing trending data"

async def handle_news_command(
    crypto_panic=None,
    get_llm_response=None
) -> str:
    """Handle news command to get latest crypto news"""
    try:
        if not crypto_panic:
            logger.warning("News command attempted but CryptoPanic service is not available")
            return "⚠️ News data service is currently unavailable."

        news_data = await crypto_panic.get_latest_news(limit=5)
        
        if not news_data or "error" in news_data:
            logger.warning(f"Error fetching news data: {news_data.get('error') if news_data else 'No data'}")
            return "❌ Could not fetch latest news. Please try again later."
        
        # Format the response
        formatted_response = "📰 <b>Latest Crypto News</b> 📰\n\n"
        
        for article in news_data:
            title = article.get("title", "Unknown Title")
            source = article.get("source", {}).get("title", "Unknown Source")
            url = article.get("url", "")
            published = article.get("published_at", "Unknown Date")
            
            # Format date if available
            date_str = published.split("T")[0] if "T" in published else published
            
            formatted_response += f"<b>{title}</b>\n"
            formatted_response += f"Source: {source} | {date_str}\n"
            formatted_response += f"<a href='{url}'>Read more</a>\n\n"
            
        return formatted_response
        
    except Exception as e:
        logger.error(f"Error in handle_news_command: {str(e)}", exc_info=True)
        return "❌ Error processing news data"

async def handle_token_lookup(token: str, market_service=None) -> str:
    """Look up token information from market service"""
    try:
        if not market_service:
            logger.warning("Token lookup attempted but market service is not available")
            return "⚠️ Token lookup service is currently unavailable."
            
        token_info = await market_service.get_token_info(token)
        
        if not token_info or "error" in token_info:
            logger.warning(f"Error fetching token info: {token_info.get('error') if token_info else 'No data'}")
            return f"❌ Could not find information for token: {token}. Please try again with a different token symbol."
        
        # Format the response
        name = token_info.get("name", "Unknown")
        symbol = token_info.get("symbol", token.upper())
        price = token_info.get("price", 0)
        change_24h = token_info.get("price_change_24h", 0)
        market_cap = token_info.get("market_cap", 0)
        volume_24h = token_info.get("volume_24h", 0)
        
        # Add emoji based on price change
        if change_24h > 0:
            emoji = "🟢"
        elif change_24h < 0:
            emoji = "🔴"
        else:
            emoji = "⚪"
            
        formatted_response = f"🪙 <b>{name} ({symbol})</b>\n\n"
        formatted_response += f"💵 Price: ${price:,.8f}\n"
        formatted_response += f"{emoji} 24h Change: {change_24h:,.2f}%\n"
        formatted_response += f"💰 Market Cap: ${market_cap:,.2f}\n"
        formatted_response += f"📊 24h Volume: ${volume_24h:,.2f}\n"
        
        return formatted_response
        
    except Exception as e:
        logger.error(f"Error in handle_token_lookup: {str(e)}", exc_info=True)
        return f"❌ Error looking up token: {token}"