"""
Handler for Telegram trending commands
"""
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

async def handle_trending_command(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle the /trending command to get trending tokens
    
    Args:
        context: Command context with services and parameters
        
    Returns:
        Response with trending tokens data
    """
    logger.info("Processing trending command")
    
    try:
        # Extract services from context
        market_service = context.get('market_service')
        if not market_service:
            return {"error": "Market service not available"}
        
        # Get trending tokens data
        trending_data = await market_service.get_trending_tokens()
        
        # Format response
        if not trending_data:
            return {"text": "No trending data available at the moment."}
        
        # Format trending tokens for display
        formatted_response = "🔥 *Trending Tokens* 🔥\n\n"
        
        for idx, token in enumerate(trending_data[:10], 1):
            symbol = token.get('symbol', 'UNKNOWN')
            name = token.get('name', 'Unknown')
            price_change = token.get('price_change_24h', 0)
            price = token.get('price', 0)
            
            # Add emoji based on price change
            emoji = "🟢" if price_change > 0 else "🔴" if price_change < 0 else "⚪"
            
            formatted_response += f"{idx}. {emoji} *{symbol}* ({name})\n"
            formatted_response += f"   💲 ${price:.6f} | {price_change:+.2f}%\n\n"
        
        return {
            "text": formatted_response,
            "parse_mode": "Markdown"
        }
        
    except Exception as e:
        logger.error(f"Error in trending command: {str(e)}")
        return {"text": f"⚠️ Error retrieving trending tokens: {str(e)}"}