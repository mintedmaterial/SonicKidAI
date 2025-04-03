"""
Discord Tweet Handler - Processes tweets from specific Discord channels

This module provides a Discord client that processes messages from specific channels,
treating them as tweets and routing them to AI agents for analysis and response.
"""
import os
import asyncio
import logging
import psycopg2
import re
import aiohttp
from typing import Dict, Any, Optional, Callable, List, Union
import discord
from dotenv import load_dotenv
from discord import Client, Intents, Message, TextChannel, Embed

from src.utils.ai_processor import AIProcessor
from src.utils.database import DatabaseConnector
from src.connections.discord_connection import DiscordConnection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DiscordTweetHandler:
    """
    Handles tweets from specific Discord channels and processes them
    through a callback function or AI processing pipeline.
    """
    def __init__(
        self,
        channel_id: Union[int, str],
        on_tweet_callback: Optional[Callable[[str], str]] = None,
        token: Optional[str] = None,
        db_connector: Optional[DatabaseConnector] = None
    ):
        """
        Initialize the Discord tweet handler.
        
        Args:
            channel_id: The ID of the Discord channel to monitor (Twitter feed channel)
            on_tweet_callback: Optional callback function to process tweets
            token: Discord bot token (if not provided, will use DISCORD_BOT_TOKEN env var)
            db_connector: Optional database connector for storing tweets
        """
        # Convert channel_id to int if it's a string
        self.channel_id = int(channel_id) if isinstance(channel_id, str) else channel_id
        self.token = token or os.getenv('DISCORD_BOT_TOKEN')
        self.on_tweet_callback = on_tweet_callback
        self.db_connector = db_connector
        
        # Initialize Discord client with necessary intents
        intents = Intents.default()
        intents.messages = True
        intents.message_content = True
        
        self.client = Client(intents=intents)
        self._setup_event_handlers()
        
        # Flag to track connected status
        self.is_connected = False
        
        # Validate bot token
        if not self.token:
            logger.error("No Discord bot token provided. Set DISCORD_BOT_TOKEN env var or pass token parameter.")
            raise ValueError("Discord bot token is required")
            
        # Log initialization
        logger.info(f"Discord tweet handler initialized for channel ID: {self.channel_id}")
    
    def _setup_event_handlers(self) -> None:
        """Set up Discord event handlers"""
        
        @self.client.event
        async def on_ready() -> None:
            """Handle bot ready event"""
            self.is_connected = True
            logger.info(f'Logged in as {self.client.user} (ID: {self.client.user.id})')
            
            # Verify channel access
            channel = self.client.get_channel(self.channel_id)
            if not channel:
                logger.warning(f"Could not access channel with ID {self.channel_id}")
            else:
                logger.info(f"Successfully connected to channel: #{channel.name} (ID: {channel.id})")
        
        @self.client.event
        async def on_message(message: Message) -> None:
            """Handle message events"""
            # Don't respond to our own messages
            if message.author == self.client.user:
                return
                
            # Process the message through our handler
            await self.on_message(message)
    
    async def on_message(self, message: Message) -> None:
        """
        Process incoming Discord messages
        
        Args:
            message: The Discord message to process
        """
        try:
            # Only process messages from the specified Twitter feed channel
            if message.channel.id != self.channel_id:
                logger.debug(f"Ignoring message from non-monitored channel: {message.channel.id}")
                return
                
            logger.info(f"Processing message from monitored channel {self.channel_id}")
            
            # Check if message has embeds (typically how tweets appear in Discord)
            tweet_content = ""
            if message.embeds and len(message.embeds) > 0:
                embed = message.embeds[0]
                tweet_content = embed.description if embed.description else ""
                logger.info(f"Processing embedded tweet: {tweet_content[:50]}...")
            else:
                # Regular text message
                tweet_content = message.content
                logger.info(f"Processing text message as tweet: {tweet_content[:50]}...")
            
            # Skip empty messages
            if not tweet_content.strip():
                logger.debug("Skipping empty message")
                return
                
            # Process tweet through callback if provided
            if self.on_tweet_callback:
                try:
                    logger.info(f"Sending tweet to callback handler: {tweet_content[:50]}...")
                    response = await self.on_tweet_callback(tweet_content)
                    
                    # Send response back to the channel if we got one
                    if response:
                        channel = self.client.get_channel(self.channel_id)
                        if channel:
                            await channel.send(response)
                            logger.info(f"Sent response: {response[:50]}...")
                        else:
                            logger.error(f"Could not find channel {self.channel_id} to send response")
                    
                except Exception as e:
                    logger.error(f"Error in tweet callback processing: {str(e)}")
            
            # Store tweet in database if connector provided
            if self.db_connector and self.db_connector.is_connected:
                try:
                    # Store tweet details
                    await self.db_connector.store_tweet(
                        content=tweet_content,
                        channel_id=str(self.channel_id),
                        author=message.author.name if message.author else "Unknown",
                        message_id=str(message.id),
                        timestamp=message.created_at
                    )
                    logger.info(f"Stored tweet in database: ID {message.id}")
                except Exception as e:
                    logger.error(f"Error storing tweet in database: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error processing Discord message: {str(e)}")
    
    async def connect(self) -> None:
        """Connect to Discord and start processing messages"""
        try:
            logger.info("Connecting to Discord...")
            await self.client.start(self.token)
        except Exception as e:
            logger.error(f"Error connecting to Discord: {str(e)}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Discord"""
        try:
            if self.client:
                logger.info("Disconnecting from Discord...")
                await self.client.close()
                self.is_connected = False
        except Exception as e:
            logger.error(f"Error disconnecting from Discord: {str(e)}")
    
    async def send_message(self, content: str) -> bool:
        """
        Send a message to the monitored channel
        
        Args:
            content: The message to send
            
        Returns:
            bool: Whether the message was sent successfully
        """
        try:
            channel = self.client.get_channel(self.channel_id)
            if not channel:
                logger.error(f"Could not find channel {self.channel_id}")
                return False
                
            await channel.send(content)
            return True
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return False

async def run_discord_tweet_handler():
    """Run Discord tweet handler as a standalone service"""
    # Load environment variables
    load_dotenv()
    
    # Twitter feed channel ID
    TWITTER_FEED_CHANNEL_ID = "1333615004305330348"
    
    async def process_tweet(tweet_content: str) -> str:
        """Process tweets with AI"""
        try:
            # Initialize AI processor with explicit OpenRouter configuration and reduced max_tokens
            ai_processor = AIProcessor({
                'default_provider': 'openrouter',
                'default_model': {
                    'openrouter': 'anthropic/claude-3-sonnet',
                    'openai': 'gpt-4o-mini',
                    'anthropic': 'claude-3-sonnet-20240229'
                },
                'max_tokens': 200  # Reduced to make responses more concise (about 50-150 words)
            })
            
            # Generate response
            system_prompt = """You are SonicKid, the DeFi Mad King, known for your high energy, 
            cross-chain expertise, and strategic trading insights. Analyze this tweet from Crypto Twitter
            and provide your thoughts focusing on trading opportunities or market implications.
            BE EXTREMELY CONCISE! Keep your response UNDER 100 WORDS at most.
            Use emojis in your energetic style, but focus on brevity and impact."""
            
            response = await ai_processor.generate_response(
                query=tweet_content,
                context={"system_prompt": system_prompt}
            )
            
            # Close AI processor
            await ai_processor.close()
            
            if not response:
                return "🤖 Error: No response generated"
                
            return response
        except Exception as e:
            logger.error(f"Error processing tweet: {str(e)}")
            return f"🤖 Error processing tweet: {str(e)}"
    
    # Initialize handler
    handler = DiscordTweetHandler(
        channel_id=TWITTER_FEED_CHANNEL_ID,
        on_tweet_callback=process_tweet
    )
    
    try:
        # Connect and start processing messages
        await handler.connect()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt detected, shutting down...")
    except Exception as e:
        logger.error(f"Error in Discord tweet handler: {str(e)}")
    finally:
        # Clean disconnect
        await handler.disconnect()

class DiscordInstructorAgent:
    """
    Discord Instructor Agent - Discord client that processes messages and responds using AI.
    This class extends the functionality of DiscordTweetHandler by adding AI-powered responses.
    """
    def __init__(
        self,
        channel_id: Union[int, str],
        discord_connection: Optional[DiscordConnection] = None,
        token: Optional[str] = None
    ):
        """
        Initialize the Discord instructor agent.
        
        Args:
            channel_id: The ID of the Discord channel to monitor
            discord_connection: Optional DiscordConnection instance for API interactions
            token: Discord bot token (if not provided, will use DISCORD_BOT_TOKEN env var)
        """
        # Convert channel_id to int if it's a string
        self.channel_id = int(channel_id) if isinstance(channel_id, str) else channel_id
        self.token = token or os.getenv('DISCORD_BOT_TOKEN')
        self.discord_connection = discord_connection
        
        # Initialize Discord client with necessary intents
        intents = Intents.default()
        intents.messages = True
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True
        intents.guild_reactions = True
        intents.message_content = True
        
        self.client = Client(intents=intents)
        self._setup_event_handlers()
        
        # Flag to track initialization and connection status
        self._initialized = False
        self.is_connected = False
        
        # AI Processor for generating responses with explicit OpenRouter config and reduced max_tokens for concise responses
        self.ai_processor = AIProcessor({
            'default_provider': 'openrouter',
            'default_model': {
                'openrouter': 'anthropic/claude-3-sonnet',
                'openai': 'gpt-4o-mini',
                'anthropic': 'claude-3-sonnet-20240229'
            },
            'max_tokens': 200  # Reduced to make responses more concise (about 50-150 words)
        })
        
        # Validate bot token
        if not self.token:
            logger.error("No Discord bot token provided. Set DISCORD_BOT_TOKEN env var or pass token parameter.")
            raise ValueError("Discord bot token is required")
            
        # Log initialization
        logger.info(f"Discord instructor agent initialized for channel ID: {self.channel_id}")
    
    def _setup_event_handlers(self) -> None:
        """Set up Discord event handlers"""
        
        @self.client.event
        async def on_ready() -> None:
            """Handle bot ready event"""
            self.is_connected = True
            self._initialized = True
            logger.info(f'Logged in as {self.client.user} (ID: {self.client.user.id})')
            
            # Verify channel access
            channel = self.client.get_channel(self.channel_id)
            if not channel:
                logger.warning(f"Could not access channel with ID {self.channel_id}")
            else:
                logger.info(f"Successfully connected to channel: #{channel.name} (ID: {channel.id})")
        
        @self.client.event
        async def on_message(message: Message) -> None:
            """Handle message events"""
            # Don't respond to our own messages
            if message.author == self.client.user:
                return
                
            # Process the message through our handler
            await self._process_message(message)
    
    async def _process_message(self, message: Message) -> None:
        """
        Process incoming Discord messages
        
        Args:
            message: The Discord message to process
        """
        try:
            # Skip if message is from bot
            if message.author.bot:
                logger.debug(f"Ignoring message from bot: {message.author.name}")
                return
            
            # Check if the bot is mentioned or message is in a DM
            is_direct_message = isinstance(message.channel, discord.DMChannel)
            is_mentioned = self.client.user in message.mentions
            
            if is_mentioned:
                logger.info(f"Received mention with query: {message.content}")
                # Extract the actual query (remove the mention)
                # Handle both <@!id> and <@id> formats for mentions
                query = message.content
                query = query.replace(f"<@{self.client.user.id}>", "").strip()
                query = query.replace(f"<@!{self.client.user.id}>", "").strip()
                
                if query:
                    await self._process_query(message, query)
                else:
                    # If no query in mention, respond with help text
                    await message.channel.send("How can I help you? Try asking about market trends, token analysis, or trading strategies!")
            
            # Process direct messages
            elif is_direct_message:
                logger.info(f"Received DM: {message.content}")
                await self._process_query(message, message.content)
                
        except Exception as e:
            logger.error(f"Error processing Discord message: {str(e)}")
            
    def _get_sonic_price_from_db_sync(self) -> Optional[float]:
        """
        Get the latest Sonic price from the database (synchronous version)
        
        Returns:
            Float price or None if not found
        """
        conn = None
        cursor = None
        try:
            # Connect to the database using the DATABASE_URL from environment
            db_url = os.getenv('DATABASE_URL')
            if not db_url:
                logger.error("No DATABASE_URL environment variable found")
                return None
            
            logger.info(f"Connecting to database with URL: {db_url[:20]}***")
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Query for the most recent SONIC price from sonic_price_feed table
            query = """
            SELECT price_usd FROM sonic_price_feed
            WHERE chain = 'sonic'
            ORDER BY timestamp DESC LIMIT 1
            """
            
            logger.info("Executing database query for SONIC price")
            cursor.execute(query)
            result = cursor.fetchone()
            
            logger.info(f"Database query result: {result}")
            
            if result and result[0]:
                return float(result[0])
            
            return None
        except Exception as e:
            logger.error(f"Error fetching Sonic price from database: {str(e)}")
            return None
        finally:
            # Make sure to close connections
            try:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
            except Exception as e:
                logger.error(f"Error closing database connection: {str(e)}")
                pass
    
    async def _get_sonic_price_from_db(self) -> Optional[float]:
        """
        Get the latest Sonic price from the database (async wrapper)
        
        Returns:
            Float price or None if not found
        """
        # Use the synchronous method but in a thread pool
        return await asyncio.to_thread(self._get_sonic_price_from_db_sync)
    
    async def _process_query(self, message: Message, query: str) -> None:
        """
        Process user query and generate AI response
        
        Args:
            message: The original Discord message
            query: The cleaned query text to process
        """
        logger.info(f"Processing query type for: {query.lower()}")
        
        try:
            # Let the user know we're processing
            async with message.channel.typing():
                # Query type detection with detailed logging
                is_sonic_price_query = False
                is_sonic_analysis_query = False
                is_token_contract_query = False
                token_contract_address = None
                
                # Check for price queries
                has_price_regex_match = bool(re.search(r'what(?:\'s| is) sonic at', query.lower()))
                has_price_keyword_match = ('sonic' in query.lower() and 'price' in query.lower())
                
                # Check for analysis queries
                has_analysis_keyword_match = ('sonic' in query.lower() and 
                    any(word in query.lower() for word in ['analysis', 'analyze', 'review', 'thoughts', 'opinion', 'outlook']))
                
                # Check for token contract queries - look for addresses in the format 0x...
                contract_addresses = re.findall(r'0x[a-fA-F0-9]{40}', query)
                
                # Check for explicit mentions of tokens, contracts or addresses
                explicit_context = ('token' in query.lower() or 'contract' in query.lower() or 
                                    'address' in query.lower() or 'about' in query.lower())
                
                # Check for implicit context: any sentence with a contract address is likely asking about the token
                implicit_context = len(contract_addresses) > 0
                
                if contract_addresses and (explicit_context or implicit_context):
                    is_token_contract_query = True
                    token_contract_address = contract_addresses[0]  # This is guaranteed to be a string
                    logger.info(f"Found token contract query with address: {token_contract_address}")
                    logger.info(f"Context: {'Explicit' if explicit_context else 'Implicit'}")
                
                if has_price_regex_match or has_price_keyword_match:
                    is_sonic_price_query = True
                
                if has_analysis_keyword_match:
                    is_sonic_analysis_query = True
                
                logger.info(f"Query analysis: price_regex={has_price_regex_match}, price_keywords={has_price_keyword_match}, " + 
                           f"analysis_keywords={has_analysis_keyword_match}, token_contract={is_token_contract_query}, " +
                           f"is_price_query={is_sonic_price_query}, is_analysis_query={is_sonic_analysis_query}")
                
                # Handle different query types
                if is_token_contract_query and token_contract_address:
                    logger.info(f"Processing token contract query for address: {token_contract_address}")
                    response = await self._generate_token_contract_analysis(token_contract_address, query)
                
                elif is_sonic_price_query:
                    logger.info("Processing direct Sonic price query")
                    # Get price from database
                    price = await self._get_sonic_price_from_db()
                    logger.info(f"Retrieved price from database: {price}")
                    
                    if price:
                        response = f"🚀 SONIC is currently at ${price:.4f}! 💰 Ready to ride this rocket? 🔥"
                    else:
                        # Fallback if database fetch fails
                        response = "🔍 Hmm, couldn't grab the latest SONIC price from my database right now. The network's probably just being slow. Try again in a sec! ⏱️"
                
                # Sonic analysis handling (using real Sonic data)
                elif is_sonic_analysis_query:
                    logger.info("Processing Sonic analysis query")
                    response = await self._generate_sonic_analysis()
                
                # Market query handling
                elif any(keyword in query.lower() for keyword in ["market", "price", "chart", "trend"]):
                    logger.info("Processing market query")
                    response = await self._generate_market_response(query)
                
                # NFT query handling
                elif any(keyword in query.lower() for keyword in ["nft", "mint", "collection"]):
                    logger.info("Processing NFT query")
                    response = await self._generate_nft_response(query)
                
                # Trading signal handling
                elif any(keyword in query.lower() for keyword in ["trade", "signal", "buy", "sell", "opportunity"]):
                    logger.info("Processing trading signal query")
                    response = await self._generate_trading_response(query)
                
                # General query handling
                else:
                    logger.info("Processing general query with Sonic Kid AI")
                    logger.debug(f"Sending query to AIProcessor: {query}")
                    response = await self._generate_general_response(query)
                
                # Send the response
                if response:
                    await message.channel.send(response)
                else:
                    await message.channel.send("I couldn't generate a proper response. Please try again later.")
        
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            await message.channel.send(f"Sorry, I encountered an error while processing your request: {str(e)}")
    
    async def _generate_market_response(self, query: str) -> str:
        """Generate market analysis response"""
        system_prompt = """You are SonicKid, the DeFi Mad King, known for your high energy and bold market insights.
        Analyze this market query and provide actionable insights about cryptocurrency price trends and market conditions.
        Focus on recent movements, key resistance/support levels, and potential trend direction.
        BE EXTREMELY CONCISE! Keep your response UNDER 100 WORDS MAXIMUM.
        Use emojis in your high-energy style, but focus on brevity and impact."""
        
        return await self.ai_processor.generate_response(
            query=query,
            context={"system_prompt": system_prompt}
        )
    
    async def _generate_nft_response(self, query: str) -> str:
        """Generate NFT analysis response"""
        system_prompt = """You are SonicKid, the DeFi Mad King and NFT expert, known for your high energy and bold market insights.
        Analyze this NFT query and provide actionable insights about NFT collections, market trends, and opportunities.
        Focus on recent sales, volume trends, and potential upcoming mints.
        BE EXTREMELY CONCISE! Keep your response UNDER 100 WORDS MAXIMUM.
        Use emojis in your high-energy style, but focus on brevity and impact."""
        
        return await self.ai_processor.generate_response(
            query=query,
            context={"system_prompt": system_prompt}
        )
    
    async def _generate_trading_response(self, query: str) -> str:
        """Generate trading signal response"""
        system_prompt = """You are SonicKid, the DeFi Mad King, known for your trading expertise and strategic insights.
        Analyze this trading query and provide tactical insights about potential opportunities, risks, and market conditions.
        Include key price levels, potential entry/exit points, and risk management considerations.
        BE EXTREMELY CONCISE! Keep your response UNDER 100 WORDS MAXIMUM.
        Use emojis in your high-energy style, but focus on brevity and impact."""
        
        return await self.ai_processor.generate_response(
            query=query,
            context={"system_prompt": system_prompt}
        )
    
    async def _generate_sonic_analysis(self) -> str:
        """
        Generate analysis of Sonic based on real data from the database
        
        Returns:
            str: A detailed analysis of Sonic with real metrics
        """
        try:
            # Get current price
            current_price = await self._get_sonic_price_from_db()
            if not current_price:
                logger.error("Failed to retrieve Sonic price for analysis")
                return "🔍 I can't seem to access the latest Sonic data right now. Network might be congested. Try again in a moment! ⏱️"
            
            # Get more Sonic data from the database
            conn = None
            cursor = None
            try:
                # Connect to database
                db_url = os.getenv('DATABASE_URL')
                if not db_url:
                    logger.error("No DATABASE_URL environment variable found")
                    raise Exception("Database connection error")
                
                conn = psycopg2.connect(db_url)
                cursor = conn.cursor()
                
                # Get 24h metrics from sonic_price_feed
                query = """
                SELECT price_usd, volume_24h, price_change_24h, liquidity 
                FROM sonic_price_feed
                WHERE chain = 'sonic'
                ORDER BY timestamp DESC LIMIT 1
                """
                
                cursor.execute(query)
                result = cursor.fetchone()
                
                if result:
                    price_usd = float(result[0]) if result[0] else current_price
                    volume_24h = float(result[1]) if result[1] else "Unknown"
                    price_change_24h = float(result[2]) if result[2] else 0
                    liquidity = float(result[3]) if result[3] else "Unknown"
                else:
                    # Fallback to basic price if detailed metrics aren't available
                    price_usd = current_price
                    volume_24h = "Unknown"
                    price_change_24h = 0
                    liquidity = "Unknown"
                
                # Format 24h change as a percentage with sign
                if isinstance(price_change_24h, (int, float)):
                    price_change_formatted = f"{'+' if price_change_24h >= 0 else ''}{price_change_24h:.2f}%"
                else:
                    price_change_formatted = "Unknown"
                
                # Format numbers for display
                if isinstance(volume_24h, (int, float)):
                    volume_formatted = f"${volume_24h:,.0f}"
                else:
                    volume_formatted = "Unknown"
                    
                if isinstance(liquidity, (int, float)):
                    liquidity_formatted = f"${liquidity:,.0f}"
                else:
                    liquidity_formatted = "Unknown"
                
                # Format the response with authentic Sonic data
                response = (
                    f"🚀 **SONIC ANALYSIS** 🚀\n\n"
                    f"💰 Current Price: ${price_usd:.4f}\n"
                    f"📊 24h Change: {price_change_formatted}\n"
                    f"💧 Liquidity: {liquidity_formatted}\n"
                    f"📈 24h Volume: {volume_formatted}\n\n"
                    f"Sonic chain is a high-performance network focused on delivering fast and low-cost transactions. "
                    f"It's seeing growing adoption for DeFi applications with strong developer support. "
                    f"The ecosystem continues to expand with new protocols and platforms. "
                    f"As always, DYOR before investing! 💎🙌"
                )
                
                return response
                
            except Exception as e:
                logger.error(f"Error fetching Sonic metrics for analysis: {str(e)}")
                # Fall back to basic price info if detailed analysis fails
                return f"🔍 SONIC is currently at ${current_price:.4f} with some network hiccups preventing full analysis. The ecosystem looks active though! 🔥"
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
        except Exception as e:
            logger.error(f"Error generating Sonic analysis: {str(e)}")
            return "❌ Sorry, I encountered an error analyzing Sonic right now. Try again later!"
            
    async def _generate_token_contract_analysis(self, contract_address: str, query: str) -> str:
        """
        Generate analysis of a specific token contract using DexScreener API
        
        Args:
            contract_address: The token contract address to analyze
            query: The original user query for context
            
        Returns:
            str: A detailed analysis of the token with metrics from DexScreener
        """
        try:
            logger.info(f"Analyzing token contract: {contract_address}")
            
            # Determine if this is a Sonic-specific token
            is_sonic_token = 'sonic' in query.lower()
            chain_id = "sonic" if is_sonic_token else None
            
            # First, try to get pair information from DexScreener API
            dexscreener_url = f"https://api.dexscreener.com/latest/dex/tokens/{contract_address}"
            logger.info(f"Querying DexScreener API: {dexscreener_url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(dexscreener_url) as response:
                    if response.status != 200:
                        logger.error(f"DexScreener API error: {response.status}")
                        # Fallback to AI response if API call fails
                        return await self._generate_token_ai_fallback(contract_address, query)
                    
                    dex_data = await response.json()
                    logger.info(f"DexScreener API response received for {contract_address}")
                    
                    # Check if any pairs were found
                    if not dex_data.get('pairs') or len(dex_data['pairs']) == 0:
                        logger.warning(f"No pairs found for token {contract_address}")
                        return await self._generate_token_ai_fallback(contract_address, query, "No trading pairs found")
                    
                    # First, try to find Sonic chain pairs if the query mentioned Sonic
                    sonic_pairs = []
                    other_pairs = []
                    
                    for pair in dex_data['pairs']:
                        if pair.get('chainId', '').lower() == 'sonic':
                            sonic_pairs.append(pair)
                        else:
                            other_pairs.append(pair)
                    
                    # Determine which pairs to analyze based on query context
                    pairs_to_analyze = sonic_pairs if is_sonic_token and sonic_pairs else dex_data['pairs']
                    
                    if len(pairs_to_analyze) == 0:
                        logger.warning(f"No relevant pairs found for query context")
                        pairs_to_analyze = dex_data['pairs']  # Fallback to all pairs
                    
                    # Use the most active pair by volume for the analysis
                    pairs_to_analyze.sort(key=lambda x: float(x.get('volume', {}).get('h24', 0)), reverse=True)
                    main_pair = pairs_to_analyze[0]
                    
                    # Extract key information
                    token_name = main_pair.get('baseToken', {}).get('name', 'Unknown')
                    token_symbol = main_pair.get('baseToken', {}).get('symbol', 'Unknown')
                    chain = main_pair.get('chainId', 'Unknown')
                    dex_name = main_pair.get('dexId', 'Unknown')
                    
                    # Price information
                    price_usd = main_pair.get('priceUsd', 'Unknown')
                    price_native = main_pair.get('priceNative', 'Unknown')
                    price_change_24h = main_pair.get('priceChange', {}).get('h24', 'Unknown')
                    
                    # Volume and liquidity 
                    volume_24h = main_pair.get('volume', {}).get('h24', 'Unknown')
                    liquidity_usd = main_pair.get('liquidity', {}).get('usd', 'Unknown')
                    
                    # Format values for display
                    price_usd_formatted = f"${float(price_usd):.6f}" if price_usd and price_usd != 'Unknown' else "Unknown"
                    
                    # Format 24h change as a percentage with sign
                    if price_change_24h and price_change_24h != 'Unknown':
                        price_change = float(price_change_24h)
                        price_change_formatted = f"{'+' if price_change >= 0 else ''}{price_change:.2f}%"
                    else:
                        price_change_formatted = "Unknown"
                    
                    # Format volume for display
                    if volume_24h and volume_24h != 'Unknown':
                        volume_formatted = f"${float(volume_24h):,.0f}"
                    else:
                        volume_formatted = "Unknown"
                    
                    # Format liquidity for display
                    if liquidity_usd and liquidity_usd != 'Unknown':
                        liquidity_formatted = f"${float(liquidity_usd):,.0f}"
                    else:
                        liquidity_formatted = "Unknown"
                    
                    # Create the response with real token data
                    response = (
                        f"🔍 **TOKEN ANALYSIS: {token_symbol}** 🔍\n\n"
                        f"📌 **Name:** {token_name} ({token_symbol})\n"
                        f"⛓️ **Chain:** {chain}\n"
                        f"🏦 **DEX:** {dex_name}\n\n"
                        f"💰 **Current Price:** {price_usd_formatted}\n"
                        f"📊 **24h Change:** {price_change_formatted}\n"
                        f"💧 **Liquidity:** {liquidity_formatted}\n"
                        f"📈 **24h Volume:** {volume_formatted}\n\n"
                        f"This token is actively trading on {chain} with {len(pairs_to_analyze)} active pairs. "
                        f"The data shows {token_symbol} has {'strong' if float(liquidity_usd or 0) > 50000 else 'limited'} liquidity "
                        f"and {'high' if float(volume_24h or 0) > 10000 else 'moderate to low'} trading volume. "
                        f"Always DYOR and consider the risks before trading! 💎🤔"
                    )
                    
                    return response
                    
        except Exception as e:
            logger.error(f"Error generating token contract analysis: {str(e)}")
            return await self._generate_token_ai_fallback(contract_address, query, reason=str(e))
    
    async def _generate_token_ai_fallback(self, contract_address: str, query: str, reason: str = "API error") -> str:
        """Generate a fallback AI response for token contract queries when API fails"""
        logger.warning(f"Using AI fallback for token analysis due to: {reason}")
        
        system_prompt = f"""You are SonicKid, the DeFi Mad King, an expert in cryptocurrency analysis.
        The user has asked about token contract {contract_address}.
        We attempted to get market data from our APIs but encountered an issue: {reason}.
        
        Respond as a crypto expert with a disclaimer that you don't have current market data.
        Mention that the contract address format looks valid/invalid based on standard format checks.
        Don't make up specific price, volume, or market data since we couldn't retrieve it.
        BE EXTREMELY CONCISE! Keep your response UNDER 100 WORDS MAXIMUM.
        
        Keep your response high-energy and use some emojis, but be clear that you're not providing actual market data."""
        
        return await self.ai_processor.generate_response(
            query=query,
            context={"system_prompt": system_prompt,
                    "max_tokens": 200,
                    "temperature": 0.7}
        )
    
    async def _generate_general_response(self, query: str) -> str:
        """Generate general response"""
        system_prompt = """You are SonicKid, the DeFi Mad King, known for your high energy, 
        crypto expertise, and strategic insights. Answer this query with useful information
        and focus on being accurate, helpful, and EXTREMELY CONCISE.
        Keep your response under 100 words maximum and use emojis in your style.
        Your responses should be short, punchy, and to the point."""
        
        return await self.ai_processor.generate_response(
            query=query,
            context={"system_prompt": system_prompt,
                    "max_tokens": 200,
                    "temperature": 0.7}
        )
    
    async def start(self) -> None:
        """Start the Discord client"""
        if self.is_connected:
            logger.info("Discord client already connected")
            return
        
        try:
            logger.info("Starting Discord client...")
            # Start in non-blocking mode
            await self.client.start(self.token)
            self.is_connected = True
            logger.info("Discord client started")
        except Exception as e:
            logger.error(f"Error starting Discord client: {str(e)}")
            raise
    
    async def stop(self) -> None:
        """Stop the Discord client"""
        if not self.is_connected:
            logger.info("Discord client already disconnected")
            return
        
        try:
            logger.info("Stopping Discord client...")
            await self.client.close()
            self.is_connected = False
            self._initialized = False
            logger.info("Discord client stopped")
        except Exception as e:
            logger.error(f"Error stopping Discord client: {str(e)}")
    
    async def send_message(self, content: str) -> bool:
        """
        Send a message to the monitored channel
        
        Args:
            content: The message to send
            
        Returns:
            bool: Whether the message was sent successfully
        """
        try:
            channel = self.client.get_channel(self.channel_id)
            if not channel:
                logger.error(f"Could not find channel {self.channel_id}")
                return False
                
            await channel.send(content)
            return True
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return False

if __name__ == "__main__":
    # Run the handler
    asyncio.run(run_discord_tweet_handler())