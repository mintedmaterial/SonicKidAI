"""Telegram action handlers for bot commands and LLM interactions"""
import logging
from typing import Dict, Any, Optional
from src.action_handler import register_action
from src.services.huggingface_service import HuggingFaceService

logger = logging.getLogger(__name__)

# Initialize shared services
huggingface_service = HuggingFaceService()

# Authorized users for trading operations
AUTHORIZED_USERS = ["@CoLT_145"]

@register_action("handle-telegram-message")
async def handle_telegram_message(agent, message_text: str, chat_id: int, username: Optional[str] = "") -> str:
    """Process incoming Telegram messages with LLM and market data integration"""
    try:
        logger.debug(f"[DEV] Processing message from {username} in chat {chat_id}: {message_text}")

        # Check if message is a command
        if message_text.startswith('/'):
            logger.debug("[DEV] Processing as command")
            return await handle_command(agent, message_text, chat_id, username)

        message_lower = message_text.lower()
        market_keywords = ['market', 'price', 'trend', 'trading', 'volume', 'sentiment']

        # Check if market-related
        if any(keyword in message_lower for keyword in market_keywords):
            logger.debug("[DEV] Processing as market query")
            return await handle_market_query(agent, message_text)

        # For all other queries, use LLM
        logger.debug("[DEV] Processing as general query")
        return await handle_general_query(agent, message_text)

    except Exception as e:
        logger.error(f"[DEV] Error handling Telegram message: {str(e)}", exc_info=True)
        return "❌ Error processing your request"

@register_action("handle-market-query") 
async def handle_market_query(agent, query: str) -> str:
    """Handle market-related queries and token lookups"""
    try:
        logger.info(f"Processing market query: {query[:50]}...")

        # Check for token lookup patterns
        token_patterns = [
            r'(?:0x[a-fA-F0-9]{40})',  # Ethereum address
            r'(?:price of|price for|about|lookup)\s+([A-Za-z0-9]+)',  # Natural language
            r'\$([A-Za-z0-9]+)',  # Dollar sign prefix
            r'([A-Za-z0-9]+) price',  # Price suffix
        ]

        # Try to extract token from query
        for pattern in token_patterns:
            import re
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                # For direct token queries, use token lookup
                token = match.group(1) if len(match.groups()) > 0 else match.group(0)
                return await handle_token_lookup(agent, token)

        # For general market queries, use market service
        response = await agent.market_service.get_llm_response(query)
        return f"📈 Market Analysis: {response}"

    except Exception as e:
        logger.error(f"Error in market query handler: {str(e)}", exc_info=True)
        return "❌ Error processing market request"

async def handle_token_lookup(agent, token: str) -> str:
    """Look up token information"""
    try:
        logger.info(f"Looking up token info for: {token}")
        info = await agent.market_service.get_token_info(token)
        return f"🔍 Token Info: {info}"
    except Exception as e:
        logger.error(f"Error in token lookup: {str(e)}", exc_info=True)
        return "❌ Error looking up token"

async def handle_command(agent, command: str, chat_id: int, username: Optional[str] = "") -> str:
    """Handle Telegram bot commands"""
    try:
        command = command[1:].lower()
        logger.info(f"Processing command: {command}")

        if command == "start":
            return "👋 Hi! I'm SonicKid, your Sonic chain market assistant. Ask me about token prices and market trends!"
        elif command == "help":
            return get_help_text()
        elif command == "price":
            # For /price command, get the current market analysis
            response = await agent.market_service.get_llm_response("What's the current market overview?")
            return f"📊 Market Update: {response}"
        elif command == "sentiment":
            return await handle_market_query(agent, "What's the current market sentiment?")

        return "❓ Unknown command. Type /help for available commands."

    except Exception as e:
        logger.error(f"Error in command handler: {str(e)}", exc_info=True)
        return "❌ Error processing command"

def get_help_text() -> str:
    """Get help text with available commands"""
    return """
📚 Available Commands:
/price - Check token prices
/sentiment - Get market sentiment analysis
/help - Show this help message

You can also ask me about:
- Market analysis and trends
- Trading sentiment
- Token price analysis
- Sonic chain updates
"""

async def handle_general_query(agent, query: str) -> str:
    """Process general queries through LLM"""
    try:
        logger.info(f"Processing general query: {query[:50]}...")
        response = await agent.equalizer.agent_completion(
            "You are a crypto market expert. Provide helpful insights.",
            query
        )
        return response.get('content', "I'm not sure how to help with that.")
    except Exception as e:
        logger.error(f"Error in general query handler: {str(e)}", exc_info=True)
        return "❌ Error processing your request"

async def handle_trading_signal(agent, signal: Dict[str, Any], chat_id: int, username: Optional[str] = "") -> str:
    """Handle trading signal from authorized users"""
    try:
        logger.error(f"Processing trading signal from {username}: {signal}")

        if username not in AUTHORIZED_USERS:
            return "❌ Unauthorized: Trading is restricted to authorized users"

        result = await agent.market_service.process_trading_signal(signal)
        if result.get('success'):
            return f"✅ Trading signal executed successfully! TX: {result.get('txHash')}"
        return "❌ Failed to execute trading signal"

    except Exception as e:
        logger.error(f"Error processing trading signal: {str(e)}", exc_info=True)
        return "❌ Error executing trading signal"