import logging
import asyncio
from typing import Dict, Any, Optional, List
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes
)
import os
from src.services.dexscreener_service import DexScreenerService
from src.actions.telegram_actions import handle_market_query, handle_token_lookup
from src.services.huggingface_service import HuggingFaceService
import asyncpg

logger = logging.getLogger(__name__)

class TelegramService:
    """Service for handling Telegram bot operations with BERT integration"""
    def __init__(self, pool: asyncpg.Pool, whale_tracker_service):
        """Initialize Telegram service"""
        self.dex_service = DexScreenerService()
        self.bert_service = HuggingFaceService()
        self.application = None
        self._initialized = False
        self._message_count = 0
        self._success_count = 0
        self._response_times = []
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._reconnect_delay = 5  # seconds
        self.pool = pool
        self.whale_tracker_service = whale_tracker_service

        # Get token from environment
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not set")
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable must be set")

        # Get chat IDs from environment
        env_chat_ids = os.getenv('TELEGRAM_CHAT_IDS', '').split(',')
        self._chat_ids = [cid.strip() for cid in env_chat_ids if cid.strip()]
        if not self._chat_ids:
            logger.warning("No chat IDs found in environment")
            self._chat_ids = []

        logger.info(f"Initialized with chat IDs: {self._chat_ids}")


    async def get_active_channels(self) -> List[Dict[str, Any]]:
        """Get active channels from database"""
        try:
            if not self.pool:
                logger.error("Database pool not available")
                return []

            async with self.pool.acquire() as conn:
                channels = await conn.fetch("""
                    SELECT channel_id, channel_name, metadata 
                    FROM telegram_channels 
                    WHERE is_active = true
                """)
                return [dict(channel) for channel in channels]
        except Exception as e:
            logger.error(f"Error fetching channels: {str(e)}")
            return []

    async def broadcast_message(self, text: str, parse_mode: Optional[str] = None, **kwargs) -> bool:
        """Send a message to all active channels"""
        try:
            if not self._initialized:
                await self.connect()

            if not self.application:
                logger.error("Cannot send message: Telegram application not initialized")
                return False

            # Get active channels from database
            channels = await self.get_active_channels()
            if not channels:
                logger.warning("No active channels found")
                return False

            success = True
            for channel in channels:
                try:
                    chat_id = channel['channel_id']
                    logger.info(f"Attempting to send message to chat ID: {chat_id}")

                    # Process message with BERT if needed
                    if kwargs.get('use_bert', False):
                        sentiment = await self.bert_service.analyze_sentiment(text)
                        if sentiment:
                            text = self._format_message_with_sentiment(text, sentiment)

                    response = await self.application.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode=parse_mode,
                        **{k: v for k, v in kwargs.items() if k not in ['chat_id', 'use_bert']}
                    )

                    if response:
                        logger.info(f"✅ Message sent successfully to chat {chat_id}")
                        await self._update_channel_last_message(chat_id)
                    else:
                        logger.warning(f"Message sent but no response received for chat {chat_id}")

                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Failed to send message to chat {chat_id}. Error: {error_msg}")
                    if "chat not found" in error_msg.lower():
                        await self._deactivate_channel(chat_id)
                    success = False

            if success:
                self._success_count += 1
            return success

        except Exception as e:
            logger.error(f"Failed to broadcast message: {str(e)}", exc_info=True)
            return False

    async def _update_channel_last_message(self, channel_id: str):
        """Update last message timestamp for channel"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE telegram_channels 
                    SET last_message_at = NOW() 
                    WHERE channel_id = $1
                """, channel_id)
        except Exception as e:
            logger.error(f"Error updating channel last message: {str(e)}")

    async def _deactivate_channel(self, channel_id: str):
        """Deactivate channel if it's not found"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE telegram_channels 
                    SET is_active = false 
                    WHERE channel_id = $1
                """, channel_id)
                logger.info(f"Deactivated channel {channel_id} due to not found error")
        except Exception as e:
            logger.error(f"Error deactivating channel: {str(e)}")

    def _format_message_with_sentiment(self, text: str, sentiment: Dict[str, Any]) -> str:
        """Format message with sentiment analysis"""
        sentiment_emoji = {
            'bullish': '📈',
            'bearish': '📉',
            'neutral': '➡️'
        }
        emoji = sentiment_emoji.get(sentiment.get('sentiment', 'neutral'), '💬')
        return f"{emoji} {text}\n\nSentiment: {sentiment.get('sentiment', 'neutral').title()} ({sentiment.get('confidence', 0):.1f}% confidence)"

    def set_chat_ids(self, chat_ids: List[str]):
        """Set the list of chat IDs to broadcast messages to"""
        # Clean and validate chat IDs
        valid_chat_ids = [
            chat_id.strip() for chat_id in chat_ids 
            if isinstance(chat_id, str) and chat_id.strip()
        ]
        if not valid_chat_ids:
            logger.error("No valid chat IDs provided")
            return
        self._chat_ids = valid_chat_ids
        logger.info(f"Updated chat IDs: {valid_chat_ids}")

    async def connect(self) -> bool:
        """Initialize and connect Telegram bot with retry logic"""
        try:
            if self._initialized:
                logger.info("Service already initialized")
                return True

            logger.info("Initializing Telegram service...")

            while self._reconnect_attempts < self._max_reconnect_attempts:
                try:
                    # Initialize bot application
                    logger.info("Creating Telegram application instance...")
                    self.application = Application.builder().token(self.bot_token).build()

                    # Set up message handlers
                    logger.info("Setting up message handlers...")
                    self.application.add_handler(
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND,
                            self._handle_message
                        )
                    )

                    # Initialize and start application
                    logger.info("Starting Telegram application...")
                    await self.application.initialize()
                    await self.application.start()
                    await self.application.updater.start_polling(
                        allowed_updates=["message", "callback_query"]
                    )

                    self._initialized = True
                    logger.info("✅ Telegram service initialized successfully")
                    return True

                except Exception as e:
                    self._reconnect_attempts += 1
                    logger.error(f"Connection attempt {self._reconnect_attempts} failed: {str(e)}")
                    if self._reconnect_attempts < self._max_reconnect_attempts:
                        logger.info(f"Retrying in {self._reconnect_delay} seconds...")
                        await asyncio.sleep(self._reconnect_delay)
                        self._reconnect_delay *= 2  # Exponential backoff
                    else:
                        logger.error("Max reconnection attempts reached")
                        return False

        except Exception as e:
            logger.error(f"Fatal error initializing Telegram service: {str(e)}", exc_info=True)
            return False

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming Telegram messages"""
        try:
            self._message_count += 1

            if not update.message or not update.message.text:
                logger.warning("Received update without message or text")
                return

            text = update.message.text.lower()
            chat_id = update.message.chat_id
            logger.info(f"Processing message from chat {chat_id}: {text[:50]}...")

            # Handle whale tracking queries
            if any(keyword in text for keyword in ['whale', 'movement', 'alert', 'tracker']):
                logger.info("Detected whale tracking query...")

                try:
                    # Get whale activity data
                    whale_data = await self.whale_tracker_service.query_whale_activity(text)
                    logger.info("Retrieved whale activity data")

                    if 'error' in whale_data:
                        response = f"❌ Error fetching whale data: {whale_data['error']}"
                    else:
                        if not whale_data['formatted_text'].strip():
                            response = "No recent whale activity detected."
                        else:
                            # Format response with whale activity
                            response = whale_data['formatted_text']

                except Exception as e:
                    logger.error(f"Error processing whale tracking query: {str(e)}", exc_info=True)
                    response = "❌ Error processing whale activity data"

            # Handle market queries
            elif any(keyword in text for keyword in ['market', 'price', 'pair', 'trading', 'sonic']):
                logger.info("Detected market query, fetching data...")
                response = await handle_market_query(self.bert_service, text)

            # Handle token lookups
            elif text.startswith('0x'):
                logger.info("Detected token lookup query...")
                response = await handle_token_lookup(self.bert_service, text[2:])
            else:
                response = (
                    "I don't understand that command. Try:\n"
                    "- Ask about market prices\n"
                    "- Look up token information\n"
                    "- Check whale movements\n"
                    "- View recent alerts"
                )

            if response:
                logger.info("Sending response to Telegram...")
                await update.message.reply_text(response, parse_mode='Markdown')
                self._success_count += 1
                logger.info(f"Successfully sent response for message type: {'whale' if 'whale' in text else 'market' if 'market' in text else 'token'}")
            else:
                logger.warning("No response generated for message")
                await update.message.reply_text("Sorry, I couldn't process your request at this time.")

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            await update.message.reply_text("Error processing your request")

    def get_metrics(self) -> Dict[str, Any]:
        """Get current service metrics"""
        return {
            "messages_processed": self._message_count,
            "success_rate": (self._success_count / self._message_count * 100) if self._message_count > 0 else 0,
            "dex_cache_ratio": self.dex_service._get_cache_hit_ratio() if hasattr(self.dex_service, '_get_cache_hit_ratio') else 0,
            "reconnect_attempts": self._reconnect_attempts
        }

    async def close(self):
        """Clean up resources"""
        try:
            if self.application:
                logger.info("Stopping Telegram bot...")
                try:
                    if self.application.updater and self.application.updater.running:
                        await self.application.updater.stop()
                    if self.application.running:
                        await self.application.stop()
                    await self.application.shutdown()
                except Exception as e:
                    logger.warning(f"Non-critical error during shutdown: {str(e)}")
                finally:
                    self._initialized = False
                logger.info("✅ Telegram service shut down successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")