"""Telegram trading command handlers for token swaps"""
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Mapping of command verbs to standardized actions
ACTION_MAPPING = {
    "buy": "buy",
    "purchase": "buy",
    "get": "buy",
    "acquire": "buy",
    "sell": "sell",
    "dump": "sell",
    "exit": "sell",
    "swap": "swap",
    "convert": "swap",
    "exchange": "swap",
    "trade": "swap"
}

async def handle_trade_execution(username: str, args: List[str], market_service=None) -> str:
    """Process trade execution commands from Telegram"""
    try:
        logger.info(f"Processing trade execution from @{username} with args: {args}")
        
        if not market_service:
            logger.warning("Trade execution attempted but market service is not available")
            return "⚠️ Trading service is currently unavailable."
            
        if len(args) < 2:
            return "❌ Insufficient parameters. Format: /trade <action> <token> [amount]"
            
        # Extract and normalize parameters
        action = args[0].lower()
        token = args[1].upper()
        amount = float(args[2]) if len(args) > 2 else None
        
        # Map action verbs to standardized actions
        normalized_action = ACTION_MAPPING.get(action)
        if not normalized_action:
            return f"❌ Unknown action: {action}. Please use buy, sell, or swap."
            
        # Perform market analysis
        try:
            # Construct analysis query
            analysis_query = f"Analyze {action.upper()} for trading opportunity"
            
            # Get market analysis
            analysis = await market_service.get_llm_response(analysis_query)
            logger.info(f"Retrieved analysis for {action.upper()}")
            
            # Format response with analysis
            response = f"🤖 <b>Trade Analysis for {token}</b> 🤖\n\n"
            
            if normalized_action == "buy":
                response += f"🟢 <b>BUY ORDER</b> for {token}"
            elif normalized_action == "sell":
                response += f"🔴 <b>SELL ORDER</b> for {token}"
            else:
                response += f"🔄 <b>SWAP ORDER</b> involving {token}"
                
            if amount:
                response += f" - Amount: {amount}\n\n"
            else:
                response += "\n\n"
                
            response += f"<b>Analysis:</b>\n{analysis}\n\n"
            
            # Add disclaimer
            response += "⚠️ <i>This is a simulated trade for information purposes only. No actual tokens were exchanged.</i>"
            
            return response
            
        except Exception as e:
            logger.error(f"Error in trade analysis: {str(e)}")
            return f"✅ {normalized_action.upper()} order for {token} acknowledged, but analysis failed."
        
    except Exception as e:
        logger.error(f"Error in handle_trade_execution: {str(e)}", exc_info=True)
        return "❌ Error processing trade execution"