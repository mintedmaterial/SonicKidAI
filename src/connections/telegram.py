"""Telegram bot connection for handling user interactions"""
import logging
import asyncio
import os
from typing import Dict, Any, Optional, List, Callable
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes
)
from telegram.constants import ParseMode

# Local service imports
# Import helpers for handling data requests
# These functions will be automatically loaded from appropriate modules if available
handle_trending_command = None
handle_news_command = None

# Try to import data request handlers if available
try:
    from actions.telegram.data_requests import (
        handle_trending_command,
        handle_news_command
    )
except ImportError:
    try:
        from src.actions.telegram.data_requests import (
            handle_trending_command,
            handle_news_command
        )
    except ImportError:
        logging.warning("Telegram data request handlers not found, some commands may be unavailable")
# Import trading handler
# Will be automatically loaded from the appropriate module if available
handle_trade_execution = None

# Try to import trade execution handler
try:
    from actions.telegram.trading.swap import handle_trade_execution
except ImportError:
    try:
        from src.actions.telegram.trading.swap import handle_trade_execution
    except ImportError:
        logging.warning("Telegram trade execution handler not found, trade commands may be unavailable")
try:
    from utils.ai_processor import AIProcessor
    from services.market_service import MarketService
except ImportError:
    try:
        from src.utils.ai_processor import AIProcessor
        from src.services.market_service import MarketService
    except ImportError:
        logging.warning("AI processor or Market service imports failed, functionality may be limited")
        AIProcessor = None
        MarketService = None

logger = logging.getLogger(__name__)

# Authorized users for trading operations
AUTHORIZED_USERS = ["@CoLT_145"]

class TelegramConnection:
    """Handles Telegram bot interactions with dynamic action creation"""
    def __init__(self, config: Dict[str, Any]):
        """Initialize Telegram connection"""
        try:
            self.config = config
            self._initialized = False
            self.application = None
            self._running = True
            self._reconnect_delay = 5
            self._max_reconnect_attempts = 3
            self.development_mode = config.get('development_mode', False)

            # Initialize service references with proper type hints
            self.market_service: Optional[MarketService] = config.get('market_service')
            self.huggingface = config.get('huggingface')
            self.whale_tracker = config.get('whale_tracker')
            self.storage_service = config.get('storage_service')
            self.dexscreener_service = config.get('dexscreener')
            
            # Initialize AI processor only if available
            if AIProcessor:
                try:
                    self.ai_processor = AIProcessor({
                        'api_key': os.getenv('OPENROUTER_API_KEY')
                    })
                except Exception as e:
                    logger.error(f"Error initializing AI processor: {str(e)}")
                    self.ai_processor = None
            else:
                self.ai_processor = None

            # Log service initialization status
            if self.market_service:
                logger.info("✅ Market service initialized")
            else:
                logger.warning("Market service not provided in config")
                
            if self.huggingface:
                logger.info("✅ HuggingFace service initialized")
            else:
                logger.warning("HuggingFace service not provided in config")
                
            if self.whale_tracker:
                logger.info("✅ Whale tracker service initialized")
            else:
                logger.warning("Whale tracker service not provided in config")
                
            if self.storage_service:
                logger.info("✅ Storage service initialized")
            else:
                logger.warning("Storage service not provided in config")
                
            if self.dexscreener_service:
                logger.info("✅ DexScreener service initialized")
            else:
                logger.warning("DexScreener service not provided in config")

            # Initialize endpoint registry
            self.registry = EndpointRegistry()
            self._setup_handlers()

            logger.info("✅ Initialized Telegram connection")
        except Exception as e:
            logger.error(f"Error initializing Telegram connection: {str(e)}")
            raise

    async def _process_market_data(self, market_data: str) -> str:
        """Process market data through OpenRouter for enhanced insights"""
        try:
            logger.info("Processing market data through OpenRouter...")
            logger.debug(f"Incoming market data: {market_data[:200]}...")

            # Create context-aware prompt
            prompt = f"""As a crypto market expert, analyze this market data and provide insights:
        Market Data: {market_data}

        Focus on key trends, potential opportunities, and risks. Break down complex market movements 
        into clear, actionable insights. 

        Format your response with sections:
        - Current Market Status
        - Key Opportunities
        - Risk Factors
        - Trading Recommendation
        """

            logger.debug(f"Sending prompt to OpenRouter: {prompt[:200]}...")

            # Call OpenRouter through AIProcessor
            try:
                # Combine the system prompt and market data into the query
                context = {"market_data": market_data}
                full_prompt = f"You are a crypto market expert. Provide helpful insights.\n\n{prompt}"
                response = await self.ai_processor.generate_response(
                    full_prompt,
                    context
                )
                logger.info("Successfully received OpenRouter analysis")
                logger.debug(f"OpenRouter response: {response[:200]}...")
                return response
            except Exception as e:
                logger.error(f"Error calling OpenRouter: {str(e)}", exc_info=True)
                raise

        except Exception as e:
            logger.error(f"Error processing market data with OpenRouter: {str(e)}", exc_info=True)
            logger.warning("Falling back to original market data")
            return market_data  # Fallback to original data if processing fails

    async def _handle_market_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle messages related to market analysis"""
        try:
            if not update.effective_chat or not update.effective_message:
                return
            message_text = update.effective_message.text.strip()
            chat_id = update.effective_chat.id
            if self.market_service:
                try:
                    # Get market data using the updated market service
                    market_data = await self.market_service.get_llm_response(message_text)
                    logger.debug(f"Received market data: {market_data[:200]}...")

                    # Process with OpenRouter
                    enhanced_analysis = await self._process_market_data(market_data)
                    await self._send_analysis_response(chat_id, {'metrics': {'summary': enhanced_analysis}})
                except Exception as e:
                    logger.error(f"Error in market analysis: {str(e)}")
                    await self._send_message(
                        chat_id=chat_id,
                        text="❌ Error analyzing market data"
                    )
            else:
                await self._send_message(chat_id, "❌ Market analysis service unavailable")
        except Exception as e:
            logger.error(f"Error handling market message: {e}")
            await self._send_message(chat_id, "❌ Error analyzing market data")

    async def _handle_trade_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trade command with authorization check"""
        try:
            if not update.effective_chat or not update.effective_message:
                logger.warning("Trade command received without effective chat or message")
                return

            # Check if market service is available
            if not self.market_service:
                logger.warning("Trade command attempted but market service is not available")
                await self._send_message(
                    chat_id=update.effective_chat.id,
                    text="⚠️ Trading service is currently unavailable. Please try again later."
                )
                return

            username = update.effective_message.from_user.username
            authorized = f"@{username}" in AUTHORIZED_USERS
            logger.info(f"Trade command from user @{username} - Authorized: {authorized}")

            if not authorized:
                logger.warning(f"Unauthorized trade attempt from @{username}")
                await self._send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Unauthorized: Trading is restricted to authorized users"
                )
                return

            args = context.args
            if not args:
                logger.debug("Trade command received without arguments")
                await self._send_message(
                    chat_id=update.effective_chat.id,
                    text="Please provide trading parameters. Example: /trade buy BTC 100"
                )
                return

            logger.info(f"Processing trade command: {args}")
            response = await handle_trade_execution(
                username=username,
                args=args,
                market_service=self.market_service
            )

            await self._send_message(
                chat_id=update.effective_chat.id,
                text=response,
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Trade command processed successfully for @{username}")

        except Exception as e:
            logger.error(f"Error handling trade command: {str(e)}", exc_info=True)
            if update.effective_chat:
                await self._send_message(
                    update.effective_chat.id,
                    "❌ Error executing trade"
                )

    async def _handle_price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /price command"""
        try:
            if not update.effective_chat:
                return

            args = context.args
            symbol = args[0].upper() if args else "BTC"
            
            # Special case for Sonic token
            if symbol.upper() in ["SONIC", "SONIC.X"] or "WHAT'S SONIC AT" in update.message.text.upper():
                await self._handle_sonic_price(update)
                return

            if self.market_service:
                try:
                    # First try to get concise price data directly from database
                    price_data = await self.market_service.get_price_and_volume(symbol, "any")
                    
                    if price_data and price_data['price'] > 0:
                        # Format a concise response with real data
                        price = price_data['price']
                        change = price_data['priceChange24h']
                        volume = price_data['volume24h']
                        
                        # Format change with arrow
                        change_arrow = "🟢 ↗️" if change >= 0 else "🔴 ↘️"
                        
                        response = (
                            f"💰 <b>{symbol}</b> Price Update\n\n"
                            f"• Current Price: <b>${price:.6f}</b>\n"
                            f"• 24h Change: {change_arrow} <b>{change:+.2f}%</b>\n"
                            f"• 24h Volume: <b>${volume:,.2f}</b>\n"
                        )
                        
                        await self._send_message(
                            chat_id=update.effective_chat.id,
                            text=response,
                            parse_mode=ParseMode.HTML
                        )
                    else:
                        # Fallback to AI analysis if no direct price data
                        analysis = await self.market_service.get_llm_response(symbol)
                        await self._send_analysis_response(update.effective_chat.id, {'metrics': {'summary': analysis}})
                except Exception as e:
                    logger.error(f"Error in price analysis: {str(e)}")
                    await self._send_message(
                        chat_id=update.effective_chat.id,
                        text="❌ Error fetching price data"
                    )
            else:
                await self._send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Price analysis service unavailable"
                )
        except Exception as e:
            logger.error(f"Error handling price command: {str(e)}")
            if update.effective_chat:
                await self._send_message(
                    update.effective_chat.id,
                    "❌ Error fetching price data"
                )
                
    async def _handle_sonic_price(self, update: Update):
        """Handle specific Sonic price queries with concise, data-driven responses"""
        try:
            if not update.effective_chat:
                logger.warning("No effective chat found in update")
                return
                
            chat_id = update.effective_chat.id
            logger.info(f"Handling Sonic price query from chat_id: {chat_id}")
            
            # Get Sonic price from storage
            sonic_price = 0
            sonic_change = 0
            sonic_volume = 0
            sonic_tvl = 0
            
            try:
                # Try to get from database first
                logger.info("Attempting to fetch Sonic price from database")
                if self.storage_service:
                    logger.info("Using TelegramConnection's storage_service")
                    price_data = await self.storage_service.getLatestTokenData("SONIC", "sonic")
                    logger.info(f"Storage service returned: {price_data}")
                else:
                    logger.info("No storage_service in TelegramConnection, trying global storage")
                    from src.storage import storage
                    price_data = await storage.getLatestTokenData("SONIC", "sonic")
                    logger.info(f"Global storage returned: {price_data}")
                
                if price_data:
                    sonic_price = price_data["price"]
                    sonic_change = price_data.get("price_change_24h", 0)
                    sonic_volume = price_data.get("volume_24h", 0)
                    sonic_tvl = price_data.get("tvl", 0)
                    price_source = price_data.get("source", "database")
                    logger.info(f"Retrieved SONIC price from database: ${sonic_price} (source: {price_source})")
                    logger.info(f"Raw price data: {price_data}")
                else:
                    logger.warning("No price data returned from database, trying market service")
                    # Try market service as fallback
                    if self.market_service:
                        logger.info("Attempting to get price from market service")
                        price_data = await self.market_service.get_price_and_volume("SONIC", "sonic")
                        logger.info(f"Market service returned: {price_data}")
                        
                        if price_data:
                            sonic_price = price_data['price']
                            sonic_change = price_data['priceChange24h']
                            sonic_volume = price_data['volume24h']
                            logger.info(f"Retrieved SONIC price from market service: ${sonic_price}")
                        else:
                            logger.warning("Market service returned no data")
                    else:
                        logger.warning("No market service available")
            except Exception as e:
                logger.error(f"Error getting Sonic price data: {str(e)}", exc_info=True)
                
            logger.info(f"Values after retrieval - price: {sonic_price}, change: {sonic_change}, volume: {sonic_volume}, tvl: {sonic_tvl}")
                
            # Format a concise response similar to Discord
            change_arrow = "🟢 ↗️" if sonic_change >= 0 else "🔴 ↘️"
            
            # Format price properly with appropriate decimal places
            logger.info(f"Formatting price value: {sonic_price}, type: {type(sonic_price)}")
            price_str = f"${sonic_price:.6f}"
            logger.info(f"Initial formatted price: {price_str}")
            
            # Remove trailing zeros but keep at least 2 decimal places
            price_parts = price_str.split('.')
            if len(price_parts) > 1:
                decimals = price_parts[1].rstrip('0')
                if len(decimals) < 2:
                    decimals = decimals + '0' * (2 - len(decimals))
                price_str = f"${price_parts[0]}.{decimals}"
                
            logger.info(f"Final formatted price: {price_str}")
            
            response = (
                f"💰 <b>SONIC</b> Price Update\n\n"
                f"• Current Price: <b>{price_str}</b>\n"
                f"• 24h Change: {change_arrow} <b>{sonic_change:+.2f}%</b>\n"
            )
            
            if sonic_volume > 0:
                response += f"• 24h Volume: <b>${sonic_volume:,.2f}</b>\n"
                
            if sonic_tvl > 0:
                response += f"• Total TVL: <b>${sonic_tvl:,.2f}</b>\n"
            
            logger.info(f"Sending response: {response}")
            await self._send_message(
                chat_id=update.effective_chat.id,
                text=response,
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            logger.error(f"Error handling Sonic price: {str(e)}")
            if update.effective_chat:
                await self._send_message(
                    update.effective_chat.id,
                    "❌ Error fetching Sonic price data"
                )

    async def _handle_whale_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /whale command"""
        try:
            if not update.effective_chat:
                return

            if self.development_mode:
                logger.debug("[DEV] Processing whale command")

            if self.whale_tracker:
                whale_data = await self.whale_tracker.get_transaction_patterns()
                if "error" not in whale_data:
                    response = (
                        "🐋 Whale Activity Summary:\n\n"
                        f"Buys: {whale_data['buy_count']}\n"
                        f"Sells: {whale_data['sell_count']}\n"
                        f"Buy Volume: ${whale_data['buy_volume']:,.2f}\n"
                        f"Sell Volume: ${whale_data['sell_volume']:,.2f}"
                    )
                else:
                    response = "❌ No whale activity data available"
            else:
                response = "❌ Whale tracking service unavailable"

            await self._send_message(
                chat_id=update.effective_chat.id,
                text=response,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error handling whale command: {str(e)}")
            if update.effective_chat:
                await self._send_message(
                    update.effective_chat.id,
                    "❌ Error fetching whale data"
                )

    async def _handle_trending_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trending command"""
        try:
            if not update.effective_chat:
                return

            if self.development_mode:
                logger.debug("[DEV] Processing trending command")

            response = await handle_trending_command(
                crypto_panic=self.config.get('crypto_panic'),
                huggingface=self.huggingface,
                market_service=self.market_service
            )
            await self._send_message(
                chat_id=update.effective_chat.id,
                text=response,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error handling trending command: {str(e)}")
            if update.effective_chat:
                await self._send_message(
                    update.effective_chat.id,
                    "❌ Error fetching trending data"
                )

    async def _handle_news_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /news command"""
        try:
            if not update.effective_chat:
                return

            if self.development_mode:
                logger.debug("[DEV] Processing news command")

            response = await handle_news_command(
                crypto_panic=self.config.get('crypto_panic'),
                get_llm_response=self.market_service.get_llm_response if self.market_service else None
            )
            await self._send_message(
                chat_id=update.effective_chat.id,
                text=response,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error handling news command: {str(e)}")
            if update.effective_chat:
                await self._send_message(
                    update.effective_chat.id,
                    "❌ Error fetching news data"
                )


    async def _handle_price_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle messages related to price queries"""
        try:
            if not update.effective_chat or not update.effective_message:
                return
            message_text = update.effective_message.text.strip()
            chat_id = update.effective_chat.id
            if self.market_service:
                try:
                    analysis = await self.market_service.get_llm_response(message_text)
                    await self._send_analysis_response(chat_id, {'metrics': {'summary': analysis}})
                except Exception as e:
                    logger.error(f"Error in price analysis: {str(e)}")
                    await self._send_message(
                        chat_id=chat_id,
                        text="❌ Error fetching price data"
                    )
            else:
                await self._send_message(chat_id, "❌ Price analysis service unavailable")
        except Exception as e:
            logger.error(f"Error handling price message: {e}")
            await self._send_message(chat_id, "❌ Error fetching price data")

    async def _handle_analysis_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle messages requesting general analysis"""
        try:
            if not update.effective_chat or not update.effective_message:
                return
            message_text = update.effective_message.text.strip()
            chat_id = update.effective_chat.id
            if self.market_service:
                try:
                    analysis = await self.market_service.get_llm_response(message_text)
                    await self._send_analysis_response(chat_id, {'metrics': {'summary': analysis}})
                except Exception as e:
                    logger.error(f"Error in analysis: {str(e)}")
                    await self._send_message(
                        chat_id=chat_id,
                        text="❌ Error performing analysis"
                    )
            else:
                await self._send_message(chat_id, "❌ Analysis service unavailable")
        except Exception as e:
            logger.error(f"Error handling analysis message: {e}")
            await self._send_message(chat_id, "❌ Error performing analysis")

    async def _send_analysis_response(self, chat_id: int, analysis: Dict[str, Any]) -> None:
        """Format and send market analysis response - optimized for conciseness"""
        try:
            if "error" in analysis:
                await self._send_message(
                    chat_id=chat_id,
                    text=f"❌ Analysis error: {analysis['error']}"
                )
                return

            # Keep the formatting minimal and clean
            response = "⚡ SONIC Analysis:\n\n"

            if 'metrics' in analysis and 'summary' in analysis['metrics']:
                # Directly pass through the already formatted concise analysis
                response += f"{analysis['metrics']['summary']}"
            else:
                # Fallback for older format
                response += "No detailed analysis available."

            await self._send_message(
                chat_id=chat_id,
                text=response,
                parse_mode=ParseMode.HTML
            )

        except Exception as e:
            logger.error(f"Error formatting market analysis: {str(e)}", exc_info=True)
            await self._send_message(
                chat_id=chat_id,
                text="❌ Error formatting market analysis"
            )

    async def _send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = ParseMode.HTML,
    ) -> None:
        """Send message with basic error handling"""
        try:
            if not self.application or not self.application.bot:
                logger.error("Bot not initialized")
                return

            if self.development_mode:
                logger.debug(f"[DEV] Sending message to {chat_id}: {text[:100]}...")

            await self.application.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode
            )
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")

    async def start(self) -> bool:
        """Start the bot with keep-alive mechanism"""
        success = await self.connect()
        if success and self.development_mode:
            logger.info("Bot started in development mode")
            asyncio.create_task(self._monitor_health())
        return success

    async def _monitor_health(self):
        """Monitor bot health in development mode"""
        while self._running:
            try:
                if not self._initialized or not self.application.running:
                    logger.warning("[DEV] Bot connection lost, attempting to reconnect...")
                    await self.connect()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"[DEV] Health check error: {str(e)}")
                await asyncio.sleep(5)

    async def close(self):
        """Clean up resources"""
        self._running = False
        try:
            if self.application:
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
                logger.info("✅ Telegram connection closed")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")

    def _setup_handlers(self):
        """Set up command and message handlers"""
        try:
            # Register command handlers
            self.registry.register_command("trending", self._handle_trending_command)
            self.registry.register_command("news", self._handle_news_command)
            self.registry.register_command("trade", self._handle_trade_command)
            self.registry.register_command("price", self._handle_price_command)
            self.registry.register_command("whale", self._handle_whale_command)

            # Register message handlers
            self.registry.register_message_handler("market", self._handle_market_message)
            self.registry.register_message_handler("price", self._handle_price_message)
            self.registry.register_message_handler("analysis", self._handle_analysis_message)

            logger.info("✅ All handlers registered successfully")
        except Exception as e:
            logger.error(f"Error setting up handlers: {str(e)}")
            raise

    async def connect(self) -> bool:
        """Initialize bot application and setup handlers"""
        reconnect_attempts = 0
        while self._running and reconnect_attempts < self._max_reconnect_attempts:
            try:
                if not self.config.get('token'):
                    logger.error("Missing Telegram bot token")
                    return False

                if self.development_mode:
                    logger.debug("Building Telegram application in development mode...")
                else:
                    logger.info("Building Telegram application...")

                self.application = Application.builder().token(self.config['token']).build()

                # Set up command handlers
                for command, handler in self.registry.command_handlers.items():
                    self.application.add_handler(CommandHandler(command, handler))

                # Set up general message handler
                self.application.add_handler(
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self._handle_message
                    )
                )

                # Initialize and start application
                await self.application.initialize()
                await self.application.start()
                await self.application.updater.start_polling()

                self._initialized = True
                logger.info("✅ Successfully initialized bot application")
                return True

            except Exception as e:
                reconnect_attempts += 1
                logger.error(f"Connection attempt {reconnect_attempts} failed: {str(e)}")
                if reconnect_attempts < self._max_reconnect_attempts:
                    await asyncio.sleep(self._reconnect_delay * reconnect_attempts)
                else:
                    logger.error("Max reconnection attempts reached")
                    return False

        return False

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Route incoming messages to appropriate handlers"""
        try:
            if not update.effective_message or not update.effective_chat:
                logger.warning("Received update without effective message or chat")
                return

            message_text = update.effective_message.text.strip()
            chat_id = update.effective_chat.id

            if self.development_mode:
                logger.debug(f"[DEV] Processing message: {message_text[:50]}...")
                
            # Special case handling with improved intent detection
            message_lower = message_text.lower()
            logger.info(f"Processing message: '{message_text}' - checking intent")
            
            # Check if message is requesting analysis
            analysis_terms = ["analysis", "analyze", "review", "outlook", "predict", "forecast", "thoughts on"]
            asking_for_analysis = any(term in message_lower for term in analysis_terms)
            
            # Price query detection terms
            price_terms = ["price", "what's", "whats", "at", "how much", "worth", "value", "$"]
            asking_for_price = any(term in message_lower for term in price_terms)
            
            # Handle Sonic price query (only if seems like a price query and not analysis)
            sonic_mentioned = "sonic" in message_lower
            if sonic_mentioned:
                if asking_for_analysis:
                    logger.info(f"Detected Sonic analysis request: '{message_text}'")
                    # Will be handled by message handlers or default analysis path
                else:
                    if asking_for_price or len(message_lower.split()) <= 3:  # Short queries like "sonic?" are likely price queries
                        logger.info(f"Detected Sonic price query: '{message_text}'")
                        await self._handle_sonic_price(update)
                        return

            # Route to appropriate handler based on content
            for keyword, handler in self.registry.message_handlers.items():
                if keyword.lower() in message_lower:
                    await handler(update, context)
                    return

            # Default to market analysis if no specific handler found
            if self.market_service:
                try:
                    analysis = await self.market_service.get_llm_response(message_text)
                    await self._send_analysis_response(chat_id, {'metrics': {'summary': analysis}})
                except Exception as e:
                    logger.error(f"Error in market analysis: {str(e)}")
                    await self._send_message(
                        chat_id=chat_id,
                        text="❌ Error analyzing market data"
                    )

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            if update.effective_chat:
                await self._send_message(
                    update.effective_chat.id,
                    "❌ Internal error occurred"
                )

class EndpointRegistry:
    """Registry for command and message handlers"""
    def __init__(self):
        self.command_handlers: Dict[str, Callable] = {}
        self.message_handlers: Dict[str, Callable] = {}

    def register_command(self, command: str, handler: Callable):
        """Register a command handler"""
        logger.debug(f"Registering command handler for: {command}")
        self.command_handlers[command] = handler

    def register_message_handler(self, keyword: str, handler: Callable):
        """Register a message handler"""
        logger.debug(f"Registering message handler for keyword: {keyword}")
        self.message_handlers[keyword] = handler