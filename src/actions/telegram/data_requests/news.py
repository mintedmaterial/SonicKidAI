"""
Handler for Telegram news commands
"""
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

async def handle_news_command(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle the /news command to get latest crypto news
    
    Args:
        context: Command context with services and parameters
        
    Returns:
        Response with latest news data
    """
    logger.info("Processing news command")
    
    try:
        # Extract services from context
        market_service = context.get('market_service')
        if not market_service:
            return {"error": "Market service not available"}
        
        # Extract parameters
        params = context.get('params', {})
        limit = params.get('limit', 5)
        token = params.get('token')
        
        # Get news data
        news_data = await market_service.get_news(token=token, limit=limit)
        
        # Format response
        if not news_data or len(news_data) == 0:
            return {"text": "No news available at the moment."}
        
        # Format news for display
        formatted_response = "📰 *Latest Crypto News* 📰\n\n"
        
        for idx, article in enumerate(news_data[:limit], 1):
            title = article.get('title', 'No title')
            url = article.get('url', '#')
            source = article.get('source', {}).get('title', 'Unknown')
            published_at = article.get('published_at', 'Unknown date')
            
            # Clean up the title for Markdown
            title = title.replace('*', '').replace('_', '').replace('`', '')
            
            formatted_response += f"{idx}. *{title}*\n"
            formatted_response += f"   Source: {source} | [Read more]({url})\n\n"
        
        # Add a source attribution
        formatted_response += "_Data powered by CryptoPanic_"
        
        return {
            "text": formatted_response,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True  # Don't preview the news links
        }
        
    except Exception as e:
        logger.error(f"Error in news command: {str(e)}")
        return {"text": f"⚠️ Error retrieving crypto news: {str(e)}"}