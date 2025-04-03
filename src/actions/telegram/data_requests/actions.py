"""Dynamic data request actions for Telegram bot"""
import logging
from typing import Dict, Any, Optional
from src.utils.telegram_tools import TELEGRAM_TOOLS
from src.services.service_registry import service_registry

logger = logging.getLogger(__name__)

async def create_data_request_action(
    action_type: str,
    args: str,
    services: Any
) -> Dict[str, Any]:
    """Create data request action based on request type"""
    try:
        logger.info(f"Processing data request action: {action_type} with args: {args}")

        # Initialize response format
        response = {
            "text": "",
            "image": None
        }

        # Get required services
        dex_service = services.dex_service
        crypto_panic = services.crypto_panic
        huggingface = services.huggingface

        # Process different action types
        if action_type == "price":
            if not args:
                response["text"] = "❌ Please specify a token symbol (e.g. 'price SONIC')"
                return response

            if not dex_service:
                logger.error("DexScreener service not available")
                response["text"] = "❌ Price service temporarily unavailable"
                return response

            try:
                token_price = await TELEGRAM_TOOLS['get_sonic_price']()
                response["text"] = token_price
                return response
            except Exception as e:
                logger.error(f"Error fetching price: {str(e)}")
                response["text"] = "❌ Error fetching price data"
                return response

        elif action_type == "news":
            try:
                news = await TELEGRAM_TOOLS['get_market_news'](args if args else None)
                response["text"] = news
                return response
            except Exception as e:
                logger.error(f"Error fetching news: {str(e)}")
                response["text"] = "❌ Error fetching news"
                return response

        elif action_type == "market":
            try:
                sentiment = await TELEGRAM_TOOLS['get_market_sentiment']()
                response["text"] = sentiment
                return response
            except Exception as e:
                logger.error(f"Error analyzing market: {str(e)}")
                response["text"] = "❌ Error analyzing market data"
                return response

        elif action_type == "trending":
            try:
                # Use DexScreener service to get trending pairs
                if not dex_service:
                    response["text"] = "❌ Trading data service unavailable"
                    return response

                pairs = await dex_service.get_pairs("SONIC")
                if not pairs:
                    response["text"] = "❌ No trending data available"
                    return response

                # Format trending data
                trending_text = "📈 Trending on Sonic Chain\n\n"
                for pair in pairs[:5]:  # Show top 5 pairs
                    token_symbol = pair.get('pair', '').split('/')[0]
                    trending_text += (
                        f"🔸 {token_symbol}\n"
                        f"Price: ${float(pair.get('price', 0)):.6f}\n"
                        f"24h Change: {float(pair.get('priceChange24h', 0)):+.2f}%\n"
                        f"Volume: ${float(pair.get('volume24h', 0)):,.2f}\n\n"
                    )

                response["text"] = trending_text
                return response

            except Exception as e:
                logger.error(f"Error getting trending data: {str(e)}")
                response["text"] = "❌ Error fetching trending data"
                return response

        else:
            logger.warning(f"Unrecognized action type: {action_type}")
            response["text"] = "❌ Command not recognized"
            return response

    except Exception as e:
        logger.error(f"Error creating data request action: {str(e)}")
        return {
            "text": "❌ Error processing request",
            "image": None
        }