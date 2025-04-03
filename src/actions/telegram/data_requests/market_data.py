"""
Telegram market data handlers
"""
import logging
from typing import Dict, Any, Optional, List, Callable

logger = logging.getLogger(__name__)

async def handle_trending_command(
    crypto_panic=None,
    huggingface=None,
    market_service=None,
    get_llm_response=None
) -> str:
    """
    Handle /trending command to show trending market topics
    """
    try:
        logger.info("Handling trending command...")
        
        # Check if services are available
        if not crypto_panic:
            logger.warning("CryptoPanic service not available")
            return "❌ Trending data service not available"
        
        # Get trending data from CryptoPanic
        try:
            trending_data = await crypto_panic.get_trending_topics()
            if not trending_data or "error" in trending_data:
                logger.error(f"Error fetching trending data: {trending_data.get('error') if trending_data else 'No data'}")
                return "❌ Error fetching trending data"
                
            # Format trending topics
            response = "🔥 Trending Market Topics:\n\n"
            
            # Add trending currencies
            if "currencies" in trending_data and trending_data["currencies"]:
                response += "💰 <b>Top Currencies:</b>\n"
                for idx, currency in enumerate(trending_data["currencies"][:5], 1):
                    response += f"{idx}. {currency['title']} (${currency['code']})\n"
                response += "\n"
            
            # Add trending hashtags/topics
            if "hashtags" in trending_data and trending_data["hashtags"]:
                response += "📊 <b>Trending Topics:</b>\n"
                for idx, tag in enumerate(trending_data["hashtags"][:5], 1):
                    response += f"{idx}. #{tag}\n"
                response += "\n"
                
            # Add sentiment analysis if available
            if huggingface and "summary" in trending_data:
                try:
                    sentiment = await huggingface.analyze_sentiment(trending_data["summary"])
                    response += f"🎯 <b>Market Sentiment:</b> {sentiment['sentiment'].title()} ({sentiment['confidence']*100:.1f}%)\n\n"
                except Exception as e:
                    logger.error(f"Error analyzing sentiment: {str(e)}")
            
            # Add AI analysis if market service is available
            if market_service and get_llm_response:
                try:
                    prompt = f"Analyze these trending crypto topics and provide a brief market outlook: {trending_data}"
                    analysis = await get_llm_response(prompt)
                    response += f"🤖 <b>Market Outlook:</b>\n{analysis}\n"
                except Exception as e:
                    logger.error(f"Error getting AI analysis: {str(e)}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing trending data: {str(e)}")
            return "❌ Error processing trending data"
            
    except Exception as e:
        logger.error(f"Unexpected error in handle_trending_command: {str(e)}")
        return "❌ Internal error fetching trending data"


async def handle_news_command(
    crypto_panic=None,
    get_llm_response=None
) -> str:
    """
    Handle /news command to show latest crypto news
    """
    try:
        logger.info("Handling news command...")
        
        # Check if CryptoPanic service is available
        if not crypto_panic:
            logger.warning("CryptoPanic service not available")
            return "❌ News service not available"
        
        # Get news from CryptoPanic
        try:
            news_data = await crypto_panic.get_news_articles(limit=5)
            if not news_data or "error" in news_data:
                logger.error(f"Error fetching news: {news_data.get('error') if news_data else 'No data'}")
                return "❌ Error fetching news data"
                
            # Format news articles
            response = "📰 Latest Crypto News:\n\n"
            
            for idx, article in enumerate(news_data[:5], 1):
                title = article.get("title", "Untitled")
                source = article.get("source", {}).get("title", "Unknown Source")
                url = article.get("url", "#")
                currencies = ", ".join([f"${c['code']}" for c in article.get("currencies", [])[:3]])
                
                response += f"{idx}. <b>{title}</b>\n"
                response += f"   Source: {source}\n"
                if currencies:
                    response += f"   Related: {currencies}\n"
                response += f"   <a href='{url}'>Read more</a>\n\n"
            
            # Add AI summary if available
            if get_llm_response:
                try:
                    prompt = f"Summarize these crypto news articles in 2-3 sentences: {str(news_data)[:1000]}"
                    summary = await get_llm_response(prompt)
                    response += f"\n🤖 <b>News Summary:</b>\n{summary}\n"
                except Exception as e:
                    logger.error(f"Error getting AI summary: {str(e)}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing news data: {str(e)}")
            return "❌ Error processing news data"
            
    except Exception as e:
        logger.error(f"Unexpected error in handle_news_command: {str(e)}")
        return "❌ Internal error fetching news data"