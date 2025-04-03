"""Telegram bot connection for handling user interactions"""
import logging
import asyncio
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes
)

logger = logging.getLogger(__name__)

class TelegramConnection:
    """Handles Telegram bot connection and message routing"""
    def __init__(self, config: Dict[str, Any], agent):
        """Initialize the Telegram connection"""
        try:
            self.config = config
            self.agent = agent
            self._initialized = False
            self.bot = None
            self._running = False
            self._stop_event = asyncio.Event()
            self.bot_username = None
            self.application = None
            self.allowed_chat_ids = config.get('allowed_chat_ids', [])
            logger.info("Initialized Telegram connection")
        except Exception as e:
            logger.error(f"Error initializing Telegram connection: {str(e)}")
            raise

    async def connect(self) -> bool:
        """Initialize bot application and setup handlers"""
        try:
            if not self.config.get('token'):
                logger.error("Missing Telegram bot token")
                return False

            logger.info("Initializing Telegram bot...")
            self.application = Application.builder().token(self.config['token']).build()

            try:
                bot = await self.application.bot.get_me()
                self.bot_username = bot.username
                logger.info(f"Retrieved bot username: {self.bot_username}")
            except Exception as e:
                logger.error(f"Failed to get bot username: {str(e)}")
                return False

            logger.info("Setting up message handlers...")
            self.application.add_handler(
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, 
                    self._handle_message
                )
            )

            self._initialized = True
            self._running = True
            logger.info(f"Successfully connected to Telegram as {self.bot_username}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect: {str(e)}", exc_info=True)
            return False

    async def start(self) -> bool:
        """Start the bot and begin polling"""
        try:
            if not self._initialized:
                success = await self.connect()
                if not success:
                    return False

            logger.info("Starting bot polling...")
            await self.application.initialize()
            await self.application.start()
            
            asyncio.create_task(self._polling_task())
            logger.info("Bot polling started successfully")
            return True

        except Exception as e:
            logger.error(f"Error starting bot: {str(e)}", exc_info=True)
            return False

    async def _polling_task(self):
        """Background task for handling polling"""
        try:
            logger.info("Starting polling task...")
            await self.application.updater.start_polling()
            logger.info("Polling task running...")

            while not self._stop_event.is_set():
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error in polling task: {str(e)}", exc_info=True)
            self._running = False
        finally:
            logger.info("Polling task stopped")

    async def close(self) -> None:
        """Stop the bot and cleanup resources"""
        try:
            self._running = False
            self._stop_event.set()

            if self._initialized and self.application:
                logger.info("Stopping Telegram bot...")
                await self.application.stop()
                await self.application.shutdown()
                self._initialized = False
                logger.info("Successfully stopped Telegram bot")

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            raise

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Route incoming messages to appropriate handlers"""
        try:
            if not update.message or not update.message.text:
                logger.debug("Received message without text, ignoring")
                return

            chat_id = update.message.chat_id
            if self.allowed_chat_ids and chat_id not in self.allowed_chat_ids:
                logger.warning(f"Unauthorized chat ID: {chat_id}")
                await update.message.reply_text("⚠️ Unauthorized chat")
                return

            text = update.message.text.strip()
            expected_prefix = f"@{self.bot_username}"

            if text.startswith(expected_prefix):
                command = text[len(expected_prefix):].strip()
                logger.info(f"Processing command: {command}")
                
                # Route message to action handler
                response = await self.agent.perform_action(
                    "handle-telegram-message",
                    message_text=command,
                    chat_id=chat_id
                )
                
                await update.message.reply_text(response)
            else:
                logger.debug(f"Message doesn't start with bot tag ({expected_prefix})")

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            await update.message.reply_text("❌ Error processing your request")

    async def send_message(self, chat_id: int, message: str) -> bool:
        """Send a message to a specific chat"""
        try:
            if not self._initialized:
                logger.error("Bot not initialized")
                return False

            await self.application.bot.send_message(chat_id, message)
            return True

        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return False
