"""
Handler for Telegram market data queries
"""
import logging
import re
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

async def handle_market_query(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle market data queries
    
    Args:
        context: Command context with services and parameters
        
    Returns:
        Response with market data
    """
    logger.info("Processing market query")
    
    try:
        # Extract services from context
        market_service = context.get('market_service')
        if not market_service:
            return {"error": "Market service not available"}
        
        # Extract parameters and query
        params = context.get('params', {})
        query = params.get('query', '')
        
        # Try to extract token from query
        token_match = re.search(r'(?:price|chart|data|info)?\s+(?:for|of)?\s+([a-zA-Z0-9]+)', query, re.IGNORECASE)
        token = token_match.group(1).upper() if token_match else 'SONIC'  # Default to SONIC
        
        # Get token data
        token_data = await market_service.get_token_data(token)
        
        # Format response
        if not token_data:
            return {"text": f"No data available for {token}."}
        
        # Format token data for display
        price = token_data.get('price', 0)
        price_change_24h = token_data.get('price_change_24h', 0)
        volume_24h = token_data.get('volume_24h', 0)
        market_cap = token_data.get('market_cap', 0)
        liquidity = token_data.get('liquidity', 0)
        
        # Add emoji based on price change
        emoji = "🟢" if price_change_24h > 0 else "🔴" if price_change_24h < 0 else "⚪"
        
        formatted_response = f"*{token} Market Data* {emoji}\n\n"
        formatted_response += f"💲 *Price:* ${price:.6f}\n"
        formatted_response += f"📊 *24h Change:* {price_change_24h:+.2f}%\n"
        formatted_response += f"📈 *24h Volume:* ${volume_24h:,.2f}\n"
        
        if market_cap > 0:
            formatted_response += f"🏦 *Market Cap:* ${market_cap:,.2f}\n"
            
        if liquidity > 0:
            formatted_response += f"💧 *Liquidity:* ${liquidity:,.2f}\n"
        
        return {
            "text": formatted_response,
            "parse_mode": "Markdown"
        }
        
    except Exception as e:
        logger.error(f"Error in market query: {str(e)}")
        return {"text": f"⚠️ Error retrieving market data: {str(e)}"}

async def handle_token_lookup(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle token address lookup
    
    Args:
        context: Command context with services and parameters
        
    Returns:
        Response with token address info
    """
    logger.info("Processing token lookup query")
    
    try:
        # Extract services from context
        market_service = context.get('market_service')
        if not market_service:
            return {"error": "Market service not available"}
        
        # Extract parameters
        params = context.get('params', {})
        token = params.get('token')
        chain = params.get('chain', 'sonic')
        
        if not token:
            return {"text": "Please specify a token to look up."}
        
        # Get token info
        token_info = await market_service.get_token_info(token, chain)
        
        # Format response
        if not token_info:
            return {"text": f"No information found for {token} on {chain} chain."}
        
        # Format token info for display
        name = token_info.get('name', 'Unknown')
        symbol = token_info.get('symbol', token.upper())
        address = token_info.get('address', 'Unknown')
        decimals = token_info.get('decimals', 18)
        
        formatted_response = f"*Token Information: {symbol}*\n\n"
        formatted_response += f"📝 *Name:* {name}\n"
        formatted_response += f"🔣 *Symbol:* {symbol}\n"
        formatted_response += f"🔢 *Decimals:* {decimals}\n"
        formatted_response += f"📍 *Address:* `{address}`\n"
        formatted_response += f"⛓️ *Chain:* {chain.capitalize()}\n"
        
        return {
            "text": formatted_response,
            "parse_mode": "Markdown"
        }
        
    except Exception as e:
        logger.error(f"Error in token lookup: {str(e)}")
        return {"text": f"⚠️ Error looking up token: {str(e)}"}