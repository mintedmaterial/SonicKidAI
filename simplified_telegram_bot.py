"""
Simplified Telegram Bot with Instructor Agent Integration

This is a simplified version of the Telegram bot that uses the instructor agent
to query the database. It avoids the circular import issues in the original code.
"""
import logging
import asyncio
import os
import json
import sys
import re
from typing import Dict, Any, Optional, List
from pathlib import Path
import asyncpg
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes
)
from telegram.constants import ParseMode
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
AUTHORIZED_USERS = ["@CoLT_145"]  # Users authorized for special commands
SONIC_CHAIN_ID = 146  # Sonic Chain ID as integer
SONIC = "sonic"  # Sonic Chain ID as string

class DatabaseConnector:
    """Handle PostgreSQL database connections and queries"""
    def __init__(self):
        self.conn = None
        self.url = os.getenv("DATABASE_URL")
        if not self.url:
            logger.error("DATABASE_URL environment variable not set")
            
    async def connect(self) -> bool:
        """Connect to PostgreSQL database"""
        try:
            if not self.url:
                return False
                
            self.conn = await asyncpg.connect(self.url)
            logger.info("✅ Connected to database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            return False
            
    async def close(self) -> None:
        """Close database connection"""
        if self.conn:
            await self.conn.close()
            self.conn = None
            
    async def query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dictionaries"""
        try:
            if not self.conn:
                await self.connect()
                
            if not self.conn:
                logger.error("No database connection available")
                return []
                
            # Execute query and convert to list of dictionaries
            rows = await self.conn.fetch(query, *args)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Query error: {str(e)}")
            return []
    
    async def get_token_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get token price data from database"""
        try:
            if not self.conn:
                await self.connect()
                
            if not self.conn:
                return None
                
            # Query the latest price data for the token
            query = """
            SELECT * FROM token_prices 
            WHERE symbol = $1 
            ORDER BY updated_at DESC 
            LIMIT 1
            """
            
            rows = await self.conn.fetch(query, symbol.upper())
            if not rows:
                return None
                
            # Convert to dictionary
            return dict(rows[0])
        except Exception as e:
            logger.error(f"Error getting token price: {str(e)}")
            return None
    
    async def get_market_data(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent market data from database"""
        try:
            if not self.conn:
                await self.connect()
                
            if not self.conn:
                return []
                
            # Query recent market data
            query = """
            SELECT * FROM market_data 
            ORDER BY timestamp DESC 
            LIMIT $1
            """
            
            rows = await self.conn.fetch(query, limit)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting market data: {str(e)}")
            return []


class InstructorAgent:
    """Handler for instructor agent interactions"""
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            logger.warning("OpenRouter API key not set")
        
        # AI configuration
        self.default_model = "anthropic/claude-3-sonnet-20240229"
        self.max_tokens = 200  # Reduced to make responses more concise (about 50-150 words)
            
    async def generate_response(self, query: str, context: Dict[str, Any] = None) -> str:
        """Generate a response using OpenRouter API"""
        try:
            if not self.api_key:
                return "API key not configured. Please set OPENROUTER_API_KEY."
                
            import aiohttp
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Get system prompt from context or use default
            system_prompt = "You are SonicKid, the DeFi Mad King, known for your high energy, crypto expertise, and strategic insights. Answer this query with useful information and focus on being accurate, helpful, and EXTREMELY CONCISE. Keep your response under 100 words maximum and use emojis in your style. Your responses should be short, punchy, and to the point."
            
            if context and "system_prompt" in context:
                system_prompt = context["system_prompt"]
                
            # Get max tokens from context or use default  
            max_tokens = context.get("max_tokens", self.max_tokens) if context else self.max_tokens
            
            # Get temperature from context or use default
            temperature = context.get("temperature", 0.7) if context else 0.7
            
            # Prepare payload
            payload = {
                "model": self.default_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            # Add market data context if provided
            if context and "market_data" in context:
                market_context = "Here's the current market data:\n"
                for item in context["market_data"]:
                    market_context += f"- {item.get('symbol', 'Unknown')}: ${item.get('price', 0):.4f}, 24h Change: {item.get('price_change_24h', 0):.2f}%\n"
                payload["messages"][0]["content"] += f"\n\nMarket Context: {market_context}"
            
            logger.info(f"Sending request to OpenRouter API for query: {query[:50]}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        logger.error(f"API error: {response.status}")
                        return f"API error: {response.status}"
                        
                    data = await response.json()
                    response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "No response")
                    logger.info(f"Received response from OpenRouter: {response_text[:50]}...")
                    return response_text
                    
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"Error: {str(e)}"
            
    async def generate_market_response(self, query: str) -> str:
        """Generate market analysis response"""
        system_prompt = """You are SonicKid, the DeFi Mad King, known for your high energy and bold market insights.
        Analyze this market query and provide actionable insights about cryptocurrency price trends and market conditions.
        Focus on recent movements, key resistance/support levels, and potential trend direction.
        BE EXTREMELY CONCISE! Keep your response UNDER 100 WORDS MAXIMUM.
        Use emojis in your high-energy style, but focus on brevity and impact."""
        
        return await self.generate_response(
            query=query,
            context={
                "system_prompt": system_prompt,
                "max_tokens": 200,
                "temperature": 0.7
            }
        )
        
    async def generate_nft_response(self, query: str) -> str:
        """Generate NFT-related response"""
        system_prompt = """You are SonicKid, the DeFi Mad King with expertise in NFTs and digital collectibles.
        Respond to this NFT-related query with insights about collections, market trends, or minting strategies.
        Focus on being accurate, helpful, and EXTREMELY CONCISE.
        Keep your response UNDER 100 WORDS MAXIMUM.
        Use emojis in your energetic style, but be brief and impactful."""
        
        return await self.generate_response(
            query=query,
            context={
                "system_prompt": system_prompt,
                "max_tokens": 200,
                "temperature": 0.7
            }
        )
        
    async def generate_trading_response(self, query: str) -> str:
        """Generate trading signal response"""
        system_prompt = """You are SonicKid, the DeFi Mad King and trading strategist.
        Respond to this trading query with strategic insights, potential setups, or risk management tips.
        Be careful not to make specific price predictions or financial advice.
        Focus on being educational, helpful, and EXTREMELY CONCISE.
        Keep your response UNDER 100 WORDS MAXIMUM.
        Use emojis in your energetic style, but be brief and impactful."""
        
        return await self.generate_response(
            query=query,
            context={
                "system_prompt": system_prompt,
                "max_tokens": 200,
                "temperature": 0.7
            }
        )


class SimplifiedTelegramBot:
    """Simplified Telegram bot with database querying capability"""
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
            return
        
        self.application = None
        self.db = DatabaseConnector()
        self.instructor = InstructorAgent()
        
        # Define authorized users
        self.authorized_users = ["@CoLT_145"]
        
        # Communities
        self.bandit_kidz_chat_id = os.getenv("TELEGRAM_BANDIT_KIDZ_CHAT_ID")
        self.sonic_lidz_chat_id = os.getenv("TELEGRAM_SONIC_LIDZ_CHAT_ID")
        
        # Track processing metrics
        self._message_count = 0
        self._success_count = 0
        
        # Chat IDs from environment
        env_chat_ids = os.getenv('TELEGRAM_CHAT_IDS', '').split(',')
        self._chat_ids = [cid.strip() for cid in env_chat_ids if cid.strip()]
        
    async def connect(self) -> bool:
        """Initialize the bot and connect to services"""
        try:
            if not self.token:
                return False
                
            # Connect to database
            db_connected = await self.db.connect()
            if not db_connected:
                logger.warning("Database connection failed")
            
            # Create application
            self.application = Application.builder().token(self.token).build()
            
            # Register handlers
            self.application.add_handler(CommandHandler("start", self._handle_start_command))
            self.application.add_handler(CommandHandler("price", self._handle_price_command))
            self.application.add_handler(CommandHandler("market", self._handle_market_command))
            self.application.add_handler(CommandHandler("query", self._handle_query_command))
            self.application.add_handler(CommandHandler("help", self._handle_help_command))
            
            # Advanced commands
            self.application.add_handler(CommandHandler("nft", self._handle_nft_command))
            self.application.add_handler(CommandHandler("trade", self._handle_trade_command))
            self.application.add_handler(CommandHandler("token", self._handle_token_command))
            self.application.add_handler(CommandHandler("sonic", self._handle_sonic_command))
            
            # General message handler
            self.application.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND, 
                self._handle_message
            ))
            
            logger.info("✅ Telegram bot initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Telegram bot: {str(e)}")
            return False
    
    async def start(self) -> None:
        """Start the bot"""
        if not self.application:
            logger.error("Cannot start bot: application not initialized")
            return
            
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("🚀 Telegram bot started")
        
    async def stop(self) -> None:
        """Stop the bot and clean up resources"""
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            
        await self.db.close()
        logger.info("✅ Telegram bot stopped")
    
    async def _handle_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        if not update.effective_chat:
            return
            
        welcome_message = (
            "👋 Welcome to the SonicKid AI Bot!\n\n"
            "I'm SonicKid, the DeFi Mad King! 🚀 Ready to help you navigate the crypto markets with high-energy insights.\n\n"
            "Commands:\n"
            "/price <symbol> - Get token price data\n"
            "/market - Get recent market data\n"
            "/sonic - Get Sonic chain insights\n"
            "/token <address> - Analyze any token contract\n"
            "/nft <collection> - Get NFT collection insights\n"
            "/trade <pair> - Get trading signals\n"
            "/help - Show this help message\n\n"
            "Or just chat with me about crypto! 💬"
        )
        
        await self._send_message(update.effective_chat.id, welcome_message)
    
    async def _handle_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command"""
        if not update.effective_chat:
            return
            
        help_message = (
            "📚 SonicKid AI Bot Commands:\n\n"
            "/price <symbol> - Get token price data\n"
            "Example: /price SONIC\n\n"
            "/market - Get recent market data\n\n"
            "/sonic - Get Sonic chain insights\n\n"
            "/token <address> - Analyze any token contract\n"
            "Example: /token 0x59524D5667B299c0813Ba3c99a11C038a3908fBC\n\n"
            "/nft <collection> - Get NFT collection insights\n"
            "Example: /nft SonicPunks\n\n"
            "/trade <pair> - Get trading signals\n"
            "Example: /trade SONIC/USDC\n\n"
            "/query <question> - Ask a question about market data\n"
            "Example: /query What's the current price of SONIC?\n\n"
            "/help - Show this help message"
        )
        
        await self._send_message(update.effective_chat.id, help_message)
    
    async def _handle_price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /price command"""
        if not update.effective_chat:
            return
            
        # Get token symbol from args
        args = context.args
        symbol = args[0].upper() if args else "SONIC"
        
        # Get price data from database
        price_data = await self.db.get_token_price(symbol)
        
        if price_data:
            # Format response
            message = (
                f"💰 <b>{symbol} Price Data</b>\n\n"
                f"Price: ${price_data.get('price_usd', 0):.4f}\n"
                f"24h Change: {price_data.get('price_change_24h', 0):.2f}%\n"
                f"Volume: ${price_data.get('volume_24h', 0):,.2f}\n"
                f"Last Updated: {price_data.get('updated_at').strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            # If we don't have price data, use a more energetic fallback message
            message = f"🔍 I don't have data for {symbol} in my database yet! Try SONIC or another major token instead! 🚀"
        
        await self._send_message(update.effective_chat.id, message, parse_mode=ParseMode.HTML)
    
    async def _handle_market_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /market command"""
        if not update.effective_chat:
            return
            
        # Get market data from database
        market_data = await self.db.get_market_data(limit=5)
        
        if market_data:
            # Format response
            message = "📊 <b>Recent Market Data</b>\n\n"
            
            for item in market_data:
                message += (
                    f"<b>{item.get('symbol', 'Unknown')}</b>\n"
                    f"Price: ${item.get('price', 0):.4f}\n"
                    f"24h Change: {item.get('price_change_24h', 0):.2f}%\n"
                    f"Volume: ${item.get('volume', 0):,.2f}\n"
                    f"Timestamp: {item.get('timestamp').strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                )
        else:
            # Query for specialized market analysis from instructor
            market_query = "Give a brief overview of the current crypto market conditions"
            message = await self.instructor.generate_market_response(market_query)
        
        await self._send_message(update.effective_chat.id, message, parse_mode=ParseMode.HTML)
    
    async def _handle_sonic_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /sonic command for Sonic chain insights"""
        if not update.effective_chat:
            return
        
        # First check if we have SONIC price data
        price_data = await self.db.get_token_price("SONIC")
        
        if price_data:
            # Format basic price info
            sonic_price = price_data.get('price_usd', 0)
            price_change = price_data.get('price_change_24h', 0)
            
            # Query for specialized SONIC analysis
            sonic_query = "Give a brief analysis of Sonic blockchain and token performance"
            analysis = await self.instructor.generate_response(
                query=sonic_query,
                context={
                    "system_prompt": """You are SonicKid, the DeFi Mad King and Sonic chain expert.
                    Provide insights about Sonic blockchain ecosystem and token performance.
                    Include relevant info about TVL, volume, and ecosystem growth.
                    BE EXTREMELY CONCISE! Keep your response UNDER 100 WORDS MAXIMUM.
                    Use emojis in your energetic style.""",
                    "max_tokens": 200
                }
            )
            
            message = (
                f"🚀 <b>SONIC Insights</b>\n\n"
                f"Current Price: ${sonic_price:.4f}\n"
                f"24h Change: {price_change:.2f}%\n\n"
                f"{analysis}"
            )
        else:
            # Fallback SONIC analysis
            sonic_query = "Give a detailed analysis of Sonic blockchain and token performance. Include recent developments, TVL, and ecosystem growth."
            message = await self.instructor.generate_response(
                query=sonic_query,
                context={
                    "system_prompt": """You are SonicKid, the DeFi Mad King and Sonic chain expert.
                    Provide detailed insights about Sonic blockchain ecosystem and token performance.
                    Include relevant info about TVL, volume, and ecosystem growth.
                    BE EXTREMELY CONCISE! Keep your response UNDER 150 WORDS MAXIMUM.
                    Use emojis in your energetic style.""",
                    "max_tokens": 250
                }
            )
        
        await self._send_message(update.effective_chat.id, message, parse_mode=ParseMode.HTML)
    
    async def _handle_token_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /token command for token contract analysis"""
        if not update.effective_chat:
            return
            
        # Get token address from args
        args = context.args
        if not args:
            await self._send_message(
                update.effective_chat.id, 
                "Please provide a token contract address. Example: /token 0x59524D5667B299c0813Ba3c99a11C038a3908fBC"
            )
            return
            
        token_address = args[0]
        
        # Check if it looks like a valid address (simple check)
        if not (token_address.startswith("0x") and len(token_address) == 42):
            await self._send_message(
                update.effective_chat.id, 
                "That doesn't look like a valid token address. Please provide a valid Ethereum-format address starting with 0x."
            )
            return
            
        # Generate token analysis
        token_query = f"Analyze this token contract: {token_address}"
        response = await self.instructor.generate_response(
            query=token_query,
            context={
                "system_prompt": """You are SonicKid, the DeFi Mad King and token analyst.
                Analyze this token contract address and provide insights.
                If you have real data about the token, include it, otherwise be honest that you don't have specific data.
                Focus on being accurate, helpful, and EXTREMELY CONCISE.
                Keep your response UNDER 100 WORDS MAXIMUM.
                Use emojis in your energetic style, but be brief and impactful.""",
                "max_tokens": 200
            }
        )
        
        await self._send_message(update.effective_chat.id, response)
    
    async def _handle_nft_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /nft command for NFT collection insights"""
        if not update.effective_chat:
            return
            
        # Get collection name from args
        args = context.args
        if not args:
            await self._send_message(
                update.effective_chat.id, 
                "Please provide an NFT collection name. Example: /nft SonicPunks"
            )
            return
            
        collection_name = " ".join(args)
        
        # Generate NFT analysis
        nft_query = f"Provide insights about the NFT collection: {collection_name}"
        response = await self.instructor.generate_nft_response(nft_query)
        
        await self._send_message(update.effective_chat.id, response)
    
    async def _handle_trade_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /trade command for trading signals"""
        if not update.effective_chat:
            return
            
        # Get trading pair from args
        args = context.args
        if not args:
            await self._send_message(
                update.effective_chat.id, 
                "Please provide a trading pair. Example: /trade SONIC/USDC"
            )
            return
            
        trading_pair = " ".join(args)
        
        # Generate trading signals
        trading_query = f"Provide trading insights for the pair: {trading_pair}"
        response = await self.instructor.generate_trading_response(trading_query)
        
        await self._send_message(update.effective_chat.id, response)
    
    async def _handle_query_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /query command"""
        if not update.effective_chat:
            return
            
        # Get query from args
        query = " ".join(context.args) if context.args else ""
        
        if not query:
            await self._send_message(
                update.effective_chat.id, 
                "Please provide a query. Example: /query What's the current price of SONIC?"
            )
            return
            
        # Process the query through our message processor
        await self._process_query(update, query)
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle general text messages"""
        if not update.effective_chat or not update.effective_message:
            return
        
        self._message_count += 1
        message_text = update.effective_message.text.strip()
        
        if not message_text:
            return
            
        # Process the message text as a query
        await self._process_query(update, message_text)
    
    async def _process_query(self, update: Update, query: str) -> None:
        """
        Process user query with specialized handling based on query type
        
        Args:
            update: The Telegram update object
            query: The query text to process
        """
        if not update.effective_chat:
            return
            
        logger.info(f"Processing query: {query[:50]}...")
        chat_id = update.effective_chat.id
        
        try:
            # Query type detection
            is_sonic_price_query = False
            is_sonic_analysis_query = False
            is_token_contract_query = False
            is_market_query = False
            is_nft_query = False
            is_trading_query = False
            
            # Convert to lowercase for case-insensitive matching
            query_lower = query.lower()
            
            # Check for price queries
            has_price_regex_match = bool(re.search(r'what(?:\'s| is) sonic at', query_lower))
            has_price_keyword_match = ('sonic' in query_lower and 'price' in query_lower)
            
            # Check for analysis queries
            has_analysis_keyword_match = ('sonic' in query_lower and 
                any(word in query_lower for word in ['analysis', 'analyze', 'review', 'thoughts', 'opinion', 'outlook']))
            
            # Check for token contract queries - look for addresses in the format 0x...
            contract_addresses = re.findall(r'0x[a-fA-F0-9]{40}', query)
            
            # Check for market queries
            has_market_keywords = any(keyword in query_lower for keyword in ["market", "chart", "trend"])
            
            # Check for NFT queries
            has_nft_keywords = any(keyword in query_lower for keyword in ["nft", "mint", "collection"])
            
            # Check for trading queries
            has_trading_keywords = any(keyword in query_lower for keyword in ["trade", "signal", "buy", "sell", "opportunity"])
            
            # Set query types based on matches
            if has_price_regex_match or has_price_keyword_match:
                is_sonic_price_query = True
            
            if has_analysis_keyword_match:
                is_sonic_analysis_query = True
                
            if contract_addresses:
                is_token_contract_query = True
                
            if has_market_keywords:
                is_market_query = True
                
            if has_nft_keywords:
                is_nft_query = True
                
            if has_trading_keywords:
                is_trading_query = True
                
            # Log query analysis
            logger.info(f"Query analysis: sonic_price={is_sonic_price_query}, sonic_analysis={is_sonic_analysis_query}, " +
                       f"token_contract={is_token_contract_query}, market={is_market_query}, nft={is_nft_query}, trading={is_trading_query}")
            
            response = None
            
            # Handle different query types
            if is_sonic_price_query:
                logger.info("Processing direct Sonic price query")
                # Get price from database
                price_data = await self.db.get_token_price("SONIC")
                
                if price_data:
                    price = price_data.get('price_usd', 0)
                    response = f"🚀 SONIC is currently at ${price:.4f}! 💰 Ready to ride this rocket? 🔥"
                else:
                    # Fallback if database fetch fails
                    response = "🔍 I don't have the latest SONIC price data yet. Let me analyze the market for you instead!"
                    # Get market data and generate a response
                    market_data = await self.db.get_market_data(limit=5)
                    response = await self.instructor.generate_response(
                        query="What is the current state of the crypto market?",
                        context={"market_data": market_data}
                    )
            
            elif is_sonic_analysis_query:
                logger.info("Processing Sonic analysis query")
                # Call /sonic command handler functionality
                price_data = await self.db.get_token_price("SONIC")
                
                if price_data:
                    # Format basic price info
                    sonic_price = price_data.get('price_usd', 0)
                    price_change = price_data.get('price_change_24h', 0)
                    
                    # Query for specialized SONIC analysis
                    sonic_query = "Give a brief analysis of Sonic blockchain and token performance"
                    analysis = await self.instructor.generate_response(
                        query=sonic_query,
                        context={
                            "system_prompt": """You are SonicKid, the DeFi Mad King and Sonic chain expert.
                            Provide insights about Sonic blockchain ecosystem and token performance.
                            Include relevant info about TVL, volume, and ecosystem growth.
                            BE EXTREMELY CONCISE! Keep your response UNDER 100 WORDS MAXIMUM.
                            Use emojis in your energetic style.""",
                            "max_tokens": 200
                        }
                    )
                    
                    response = (
                        f"🚀 <b>SONIC Insights</b>\n\n"
                        f"Current Price: ${sonic_price:.4f}\n"
                        f"24h Change: {price_change:.2f}%\n\n"
                        f"{analysis}"
                    )
                else:
                    # Call the instructor for an analysis
                    response = await self.instructor.generate_response(
                        query="Give an analysis of Sonic blockchain and token",
                        context={
                            "system_prompt": """You are SonicKid, the DeFi Mad King and Sonic chain expert.
                            Provide detailed insights about Sonic blockchain ecosystem and token performance.
                            Include relevant info about TVL, volume, and ecosystem growth.
                            BE EXTREMELY CONCISE! Keep your response UNDER 150 WORDS MAXIMUM.
                            Use emojis in your energetic style.""",
                            "max_tokens": 250
                        }
                    )
            
            elif is_token_contract_query and contract_addresses:
                logger.info(f"Processing token contract query for address: {contract_addresses[0]}")
                token_address = contract_addresses[0]
                
                # Generate token analysis
                token_query = f"Analyze this token contract: {token_address}"
                response = await self.instructor.generate_response(
                    query=token_query,
                    context={
                        "system_prompt": """You are SonicKid, the DeFi Mad King and token analyst.
                        Analyze this token contract address and provide insights.
                        If you have real data about the token, include it, otherwise be honest that you don't have specific data.
                        Focus on being accurate, helpful, and EXTREMELY CONCISE.
                        Keep your response UNDER 100 WORDS MAXIMUM.
                        Use emojis in your energetic style, but be brief and impactful.""",
                        "max_tokens": 200
                    }
                )
            
            elif is_market_query:
                logger.info("Processing market query")
                response = await self.instructor.generate_market_response(query)
                
            elif is_nft_query:
                logger.info("Processing NFT query")
                response = await self.instructor.generate_nft_response(query)
                
            elif is_trading_query:
                logger.info("Processing trading signal query")
                response = await self.instructor.generate_trading_response(query)
                
            else:
                logger.info("Processing general query with Sonic Kid AI")
                # Get market data for context
                market_data = await self.db.get_market_data(limit=5)
                
                # Generate response using instructor agent
                response = await self.instructor.generate_response(
                    query=query, 
                    context={"market_data": market_data}
                )
            
            # Send the response
            if response:
                await self._send_message(chat_id, response, parse_mode=ParseMode.HTML)
                self._success_count += 1
            else:
                await self._send_message(chat_id, "I couldn't generate a proper response. Please try again later.")
                
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            await self._send_message(
                chat_id, 
                "Sorry, I encountered an error while processing your request. Please try again later."
            )
    
    async def _send_message(self, chat_id: int, text: str, parse_mode: Optional[str] = None) -> None:
        """Send a message to the specified chat"""
        try:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode
            )
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current service metrics"""
        return {
            "messages_processed": self._message_count,
            "success_rate": (self._success_count / self._message_count * 100) if self._message_count > 0 else 0,
        }


async def main():
    """Main entry point"""
    try:
        # Initialize bot
        bot = SimplifiedTelegramBot()
        
        # Connect and start bot
        connected = await bot.connect()
        if not connected:
            logger.error("Failed to initialize bot")
            return
            
        await bot.start()
        
        # Keep the bot running until interrupted
        try:
            while True:
                await asyncio.sleep(10)
        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Bot interrupted")
        finally:
            await bot.stop()
            
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")