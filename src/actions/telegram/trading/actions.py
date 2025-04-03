"""Dynamic trading actions for Telegram bot"""
import logging
from typing import Dict, Any, Optional
from .swap import handle_trade_execution
from ....services.market_service import MarketService


logger = logging.getLogger(__name__)

async def create_trading_action(
    action_type: str,
    market_service: Optional[MarketService],
    user: str,
    contract: str,
    get_llm_response
) -> Dict[str, Any]:
    """Handle trade execution requests from authorized users"""
    if user != "@CoLT_145":
        return {"success": False, "error": "Unauthorized trading request"}
    
    """Create trading action based on request type"""
    try:
        # Create action only when request comes in
        if action_type in ["trade", "sell"]:
            response = await handle_trade_execution(
                market_service,
                user,
                contract,
                action_type,
                get_llm_response
            )
            return {
                "text": response,
                "image": None
            }
        else:
            logger.error(f"Unknown trading action type: {action_type}")
            return {
                "text": "❌ Invalid trading action type",
                "image": None
            }
    except Exception as e:
        logger.error(f"Error creating trading action: {str(e)}")
        return {
            "text": "❌ Error processing trading request",
            "image": None
        }