"""SonicKid agent implementation for automated cross-chain trading"""
import logging
import asyncio
from typing import Dict, List, Any, Optional
from decimal import Decimal
import random
import time
import json
from dataclasses import dataclass

from ..connections.trading import TradingConnection
from ..utils.trade_processor import TradeProcessor
from ..utils.indicators import analyze_market_signals, load_historical_data
from ..services.rag_service import RAGService
from ..utils.ai_processor import AIProcessor
from ..connections.browser import BrowserConnection
from ..auth.trading_auth import trading_auth
from ..services.price_service import price_service

# Import database models
from server.db import db
from shared.schema import whaleKlineData, marketSentiment, TwitterData
from shared.schema_types import aiAnalysis as AiAnalysis, dashboardPosts as DashboardPost, marketUpdates as MarketUpdate, whaleAlerts, telegramChannels

logger = logging.getLogger(__name__)

@dataclass
class SonicKidAgent:
    """SonicKid agent for automated trading"""
    name: str
    config: Dict[str, Any]
    trading: TradingConnection
    processor: TradeProcessor
    rag_service: Optional[RAGService] = None
    browser: Optional[BrowserConnection] = None
    ai_processor: Optional[AIProcessor] = None

    def __init__(self, name: str, config: Dict[str, Any], trading: TradingConnection,
                 processor: TradeProcessor):
        """Initialize agent with configuration and dependencies"""
        self.name = name
        self.config = config
        self.trading = trading
        self.processor = processor

        # Initialize only essential services first
        self.rag_service = None
        self.browser = None
        self.ai_processor = None

        # Trading parameters
        self.min_confidence_threshold = 0.7
        self.max_position_size = Decimal("0.1")
        self.min_profit_threshold = Decimal("0.05")
        self.max_loss_threshold = Decimal("0.01")
        self.market_conditions = {}

        logger.info(f"Created {self.name} agent with base configuration")

    async def initialize(self, enable_browser: bool = False, enable_ai: bool = True):
        """Initialize agent connections and state"""
        try:
            logger.info(f"Initializing {self.name} agent...")

            # Initialize trading connection first
            logger.debug("Initializing trading connection...")
            await self.trading.connect()
            logger.info("✅ Trading connection initialized")

            # Initialize AI processor if enabled
            if enable_ai and 'ai' in self.config:
                logger.debug("Initializing AI processor...")
                self.ai_processor = AIProcessor(self.config['ai'])
                logger.info("✅ AI processor initialized")

            # Skip browser initialization by default
            if enable_browser and 'browser' in self.config:
                logger.debug("Initializing browser connection...")
                self.browser = BrowserConnection(self.config['browser'])
                await self.browser.connect()
                logger.info("✅ Browser connection initialized")
            else:
                logger.info("Browser connection skipped - will initialize on demand")

            # Initialize market conditions
            logger.debug("Analyzing market conditions...")
            await self.analyze_market_conditions()
            logger.info("✅ Market conditions initialized")

            logger.info(f"✅ {self.name} initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Error initializing agent: {str(e)}", exc_info=True)
            raise

    async def ensure_browser_initialized(self) -> bool:
        """Ensure browser is initialized when needed"""
        try:
            if not self.browser and 'browser' in self.config:
                logger.info("Initializing browser on demand...")
                self.browser = BrowserConnection(self.config['browser'])
                await self.browser.connect()
                logger.info("✅ Browser connection initialized")
            return True if self.browser else False
        except Exception as e:
            logger.error(f"Failed to initialize browser: {str(e)}")
            return False

    async def store_ai_analysis(self, agent_type: str, analysis_type: str, content: str, confidence: float) -> int:
        """Store AI analysis result in database"""
        try:
            logger.debug(f"Storing AI analysis: agent={agent_type}, type={analysis_type}, confidence={confidence}")
            [result] = await db.insert(AiAnalysis).values({
                'agentType': agent_type,
                'modelName': self.config['ai']['main_instructor']['model'] if agent_type == 'main_instructor' else 'helper',
                'analysisType': analysis_type,
                'content': content,
                'confidence': confidence,
                'metadata': {}
            }).returning()
            logger.info(f"Stored AI analysis with ID: {result.id}")
            return result.id
        except Exception as e:
            logger.error(f"Error storing AI analysis: {str(e)}")
            return None

    async def store_market_sentiment(self, sentiment: str, score: float, symbol: str = None) -> None:
        """Store market sentiment in database"""
        try:
            logger.debug(f"Storing market sentiment: {sentiment}, score={score}, symbol={symbol}")
            await db.insert(MarketSentiment).values({
                'source': 'ai_analysis',
                'sentiment': sentiment,
                'score': score,
                'symbol': symbol,
                'content': '',
                'metadata': {}
            })
            logger.info("Successfully stored market sentiment")
        except Exception as e:
            logger.error(f"Error storing market sentiment: {str(e)}")

    async def store_dashboard_post(self, type: str, content: str, title: str = None, source_id: str = None, metadata: Dict[str, Any] = None) -> None:
        """Store post for dashboard display"""
        try:
            logger.debug(f"Storing dashboard post: type={type}, title={title}")
            [result] = await db.insert(DashboardPost).values({
                'type': type,
                'content': content,
                'title': title,
                'sourceId': source_id,
                'metadata': metadata or {}
            }).returning()
            logger.info(f"✅ Successfully stored dashboard post (ID: {result.id})")
        except Exception as e:
            logger.error(f"Error storing dashboard post: {str(e)}")

    async def store_tweet(self, content: str, analysis_id: int, sentiment: str, confidence: float) -> None:
        """Store tweet with AI analysis reference"""
        try:
            logger.debug(f"Storing tweet: analysis_id={analysis_id}, sentiment={sentiment}, confidence={confidence}")
            # Store tweet in twitter_data table
            [tweet_result] = await db.insert(TwitterData).values({
                'tweetId': f"ai_generated_{int(time.time())}",
                'content': content,
                'author': self.config.get('twitter', {}).get('username', '@SonicKid'),
                'sentiment': sentiment,
                'category': 'market_analysis',
                'tradeRelated': True,
                'confidence': confidence,
                'aiAnalysisId': analysis_id,
                'metadata': {}
            }).returning()
            logger.info("Successfully stored tweet")

            # Also store as dashboard post
            await self.store_dashboard_post(
                type='tweet',
                content=content,
                title='AI Generated Tweet',
                source_id=tweet_result.tweetId,
                metadata={
                    'sentiment': sentiment,
                    'confidence': confidence,
                    'analysis_id': analysis_id
                }
            )

        except Exception as e:
            logger.error(f"Error storing tweet: {str(e)}")

    async def process_trade_command(
        self,
        amount: float,
        token_address: str,
        trade_type: str = "buy",
        to_address: Optional[str] = None,
        chain_id: Optional[int] = None,
        user_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process trade command with destination handling and authentication
        
        Args:
            amount: Amount to trade in token's base units
            token_address: Token contract address
            trade_type: Type of trade ('buy', 'sell', or 'swap')
            to_address: Destination address for tokens
            chain_id: Target chain ID (optional)
            user_address: Address of user initiating the trade (for authorization)
            
        Returns:
            Trade result dictionary with success status
        """
        try:
            logger.debug(f"Processing trade command: type={trade_type}, amount={amount}, token={token_address}, to={to_address}, chain={chain_id}, user={user_address}")

            # Validate trade parameters
            if trade_type.lower() not in ["buy", "sell", "swap"]:
                logger.error(f"Invalid trade type: {trade_type}")
                return {"success": False, "error": "Invalid trade type"}

            if not to_address:
                logger.error("Destination address required for trades")
                return {"success": False, "error": "Missing destination address"}
                
            # Check authorization if user_address is provided
            if user_address:
                # Verify user is authorized to execute trades
                if not trading_auth.is_account_authorized(user_address):
                    logger.warning(f"Unauthorized trade attempt from user: {user_address}")
                    return {
                        "success": False, 
                        "error": "Unauthorized: Your account is not approved for executing trades"
                    }
                logger.info(f"Authorization check passed for user: {user_address}")
            else:
                # If no user_address is provided, assume it's an internal call (e.g., automated trading)
                logger.info("No user authentication provided, assuming internal agent execution")

            # Get default source and target chains from config
            source_chain = self.config.get('default_source_chain', 'SONIC')
            target_chain = chain_id if chain_id else self.config.get('default_target_chain', source_chain)

            # Get price data from reliable sources
            chain_id_value = None
            if source_chain and source_chain.lower() in self.config.get('trading', {}).get('networks', {}):
                chain_id_value = self.config['trading']['networks'][source_chain.lower()].get('chain_id')
            
            price_data = None
            if chain_id_value:
                # Connect to price service if not already connected
                if not price_service._session:
                    await price_service.connect()
                
                # Get accurate token price data
                price_data = await price_service.get_token_price(token_address, chain_id_value)
                if not price_data:
                    logger.warning(f"Could not retrieve price data for {token_address}")
                else:
                    logger.info(f"Retrieved price data from {price_data.get('source', 'unknown')}: " +
                                f"Price: {price_data.get('price')}, Symbol: {price_data.get('symbol')}")
            
            # Prepare trade parameters for swap
            trade_params = {
                "source_chain": source_chain,
                "target_chain": target_chain,
                "token_address": token_address,
                "amount": float(amount),
                "trade_type": trade_type,
                "to_address": to_address,
                "networks": self.config.get('trading', {}).get('networks', {}),
                "price_data": price_data  # Add retrieved price data
            }

            # Get analysis from main instructor (Anthropic)
            if self.ai_processor:
                main_analysis = await self.ai_processor.generate_response(
                    f"Analyze trading opportunity: {json.dumps(trade_params, default=str)}",
                    context={"market_conditions": self.market_conditions}
                )

                # Store main instructor analysis
                main_analysis_id = await self.store_ai_analysis(
                    'main_instructor',
                    'trade',
                    main_analysis,
                    self._extract_confidence(main_analysis)
                )

                trade_params['main_analysis'] = {
                    'source': 'anthropic',
                    'analysis': main_analysis,
                    'weight': 0.6,
                    'id': main_analysis_id
                }
                logger.info(f"Main instructor analysis: {main_analysis}")

            # Get analysis from helper agents
            if self.ai_processor and self.config.get('ai', {}).get('helper_agents'):
                helper_analyses = []
                for helper in self.config['ai']['helper_agents']:
                    analysis = await self.ai_processor.generate_response(
                        f"Analyze trading opportunity: {json.dumps(trade_params, default=str)}",
                        context={"model": helper['model']}
                    )

                    # Store helper analysis
                    helper_analysis_id = await self.store_ai_analysis(
                        helper['name'],
                        helper['type'],
                        analysis,
                        self._extract_confidence(analysis)
                    )

                    helper_analyses.append({
                        'source': helper['name'],
                        'analysis': analysis,
                        'weight': 0.2,
                        'id': helper_analysis_id
                    })
                    logger.info(f"Helper agent {helper['name']} analysis: {analysis}")
                trade_params['helper_analyses'] = helper_analyses

            # Calculate combined confidence score
            analyses = [trade_params.get('main_analysis')] + trade_params.get('helper_analyses', [])
            combined_confidence = sum(
                float(a.get('weight', 0)) * self._extract_confidence(a.get('analysis', ''))
                for a in analyses if a
            )
            trade_params['combined_confidence'] = combined_confidence
            logger.info(f"Combined confidence score: {combined_confidence}")

            # Store overall market sentiment
            await self.store_market_sentiment(
                'bullish' if combined_confidence > 0.6 else 'bearish',
                combined_confidence,
                token_address
            )

            # Only proceed with trade if confidence meets threshold
            if combined_confidence < self.min_confidence_threshold:
                logger.warning(f"Trade confidence {combined_confidence} below threshold {self.min_confidence_threshold}")
                return {"success": False, "error": "Insufficient confidence in trade opportunity"}

            # Execute trade using trading connection
            result = await self.trading.execute_cross_chain_swap(trade_params)

            if result and result.get('success'):
                # Update history and parameters
                self._update_trade_history(trade_params, result)
                self._adjust_parameters()

                # Generate and post trade update
                tweet_content = await self.generate_trade_update_post({
                    **result,
                    'analyses': analyses,
                    'confidence': combined_confidence
                })

                if tweet_content:
                    # Store tweet with analysis reference
                    await self.store_tweet(
                        tweet_content,
                        trade_params['main_analysis']['id'],
                        'bullish' if combined_confidence > 0.6 else 'bearish',
                        combined_confidence
                    )
                    # Only post to Twitter if browser is configured
                    if self.browser:
                        await self.post_to_twitter(tweet_content)

                return {"success": True, "result": result}
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'Trade execution failed'
                logger.error(f"Trade execution failed: {error_msg}")
                return {"success": False, "error": error_msg}

        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def generate_trade_update_post(self, trade_result: Dict[str, Any]) -> str:
        """Generate a trade update post using AI processor"""
        try:
            if not self.ai_processor:
                return "Trade executed successfully"

            # Create context for the AI
            context = {
                "trade_details": trade_result,
                "market_conditions": self.market_conditions,
                "timestamp": time.time()
            }

            prompt = f"""
            Generate a concise trade update tweet about this successful trade:
            - Trade: {json.dumps(trade_result, default=str)}
            - Market Conditions: {json.dumps(self.market_conditions, default=str)}

            Keep it engaging but professional. Include:
            1. Trade action (buy/sell)
            2. Asset pair
            3. Key reason if available
            4. Relevant emojis
            """

            response = await self.ai_processor.generate_response(prompt, context)
            return response

        except Exception as e:
            logger.error(f"Error generating trade update: {str(e)}")
            return "Trade executed successfully"

    async def generate_market_insight_post(self) -> str:
        """Generate a market insight post using AI processor"""
        try:
            if not self.ai_processor:
                return None

            # Get market analysis
            market_analysis = await self.analyze_market_conditions()

            prompt = f"""
            Create an insightful market analysis tweet based on:
            - Market Analysis: {json.dumps(market_analysis, default=str)}
            - Current Conditions: {json.dumps(self.market_conditions, default=str)}

            Format:
            1. Key market observation
            2. Important metrics/signals
            3. Potential opportunities
            4. Relevant cashtags/emojis
            """

            response = await self.ai_processor.generate_response(prompt)

            if response:
                # Store as dashboard post
                await self.store_dashboard_post(
                    type='market_insight',
                    content=response,
                    title='Market Analysis Update',
                    metadata={'market_conditions': self.market_conditions}
                )

            return response

        except Exception as e:
            logger.error(f"Error generating market insight: {str(e)}")
            return None

    async def post_to_twitter(self, content: str) -> bool:
        """Post content to Twitter using browser connection"""
        try:
            # Initialize browser if needed
            if not await self.ensure_browser_initialized():
                logger.warning("Cannot post to Twitter - browser not available")
                return False

            if not content:
                return False

            result = await self.browser.execute_action(
                action="post_tweet",
                params={"content": content}
            )

            return result.get('success', False)

        except Exception as e:
            logger.error(f"Error posting to Twitter: {str(e)}")
            return False

    async def analyze_market_conditions(self) -> Dict[str, Any]:
        """Analyze current market conditions"""
        try:
            conditions = {}

            # Get market analysis for key tokens
            token_symbols = ['ETH', 'WBTC', 'USDC', 'USDT']

            for symbol in token_symbols:
                try:
                    # Get current prices and technical indicators
                    prices = await self.trading.get_token_prices([symbol])
                    if prices and symbol in prices:
                        price = prices[symbol]
                        await self.trading.update_price_history(symbol, price)

                        indicators = await self.trading.calculate_technical_indicators(symbol)
                        if indicators:
                            conditions[symbol] = {
                                'price': price,
                                'volatility': indicators['volatility'],
                                'trend_strength': indicators['trend_strength'],
                                'last_update': time.time()
                            }

                except Exception as e:
                    logger.error(f"Error analyzing {symbol}: {str(e)}")
                    continue

            self.market_conditions = conditions
            return conditions

        except Exception as e:
            logger.error(f"Error analyzing market conditions: {str(e)}")
            return {}

    async def get_router_documentation(self, router_name: str) -> Optional[Dict[str, Any]]:
        """Get documentation for a specific router"""
        try:
            if not self.rag_service:
                logger.warning("RAG service not initialized")
                return None

            docs = await self.rag_service.get_router_specific_content(router_name)
            if docs:
                logger.info(f"Retrieved {len(docs)} documentation items for {router_name}")
                return {
                    "success": True,
                    "documentation": docs
                }
            return None
        except Exception as e:
            logger.error(f"Error getting router documentation: {str(e)}")
            return None

    async def search_documentation(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search through documentation and Twitter data"""
        try:
            if not self.rag_service:
                logger.warning("RAG service not initialized")
                return []

            results = await self.rag_service.search_all_content(query, filters)
            logger.info(f"Found {len(results)} relevant documents for query: {query}")
            return results
        except Exception as e:
            logger.error(f"Error searching documentation: {str(e)}")
            return []

    async def get_relevant_tweets(self, topic: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get relevant tweets for a given topic"""
        try:
            if not self.rag_service:
                logger.warning("RAG service not initialized")
                return []

            # Use RAG service to search specifically for Twitter content
            tweets = await self.rag_service.search_all_content(
                topic,
                filters={"source": "twitter"},
                limit=limit
            )
            logger.info(f"Found {len(tweets)} relevant tweets for topic: {topic}")
            return tweets
        except Exception as e:
            logger.error(f"Error getting relevant tweets: {str(e)}")
            return []

    async def analyze_router_sentiment(self, router_name: str) -> Dict[str, Any]:
        """Analyze sentiment around a specific router"""
        try:
            # Get recent tweets about the router
            tweets = await self.get_relevant_tweets(f"{router_name} router")

            # Calculate overall sentiment
            if tweets:
                sentiments = [tweet.get('sentiment', 'neutral') for tweet in tweets]
                sentiment_counts = {
                    'positive': sentiments.count('positive'),
                    'negative': sentiments.count('negative'),
                    'neutral': sentiments.count('neutral')
                }

                # Determine dominant sentiment
                dominant_sentiment = max(sentiment_counts.items(), key=lambda x: x[1])[0]
                confidence = sentiment_counts[dominant_sentiment] / len(tweets)

                return {
                    'sentiment': dominant_sentiment,
                    'confidence': confidence,
                    'tweet_count': len(tweets),
                    'sentiment_breakdown': sentiment_counts
                }
            return {
                'sentiment': 'neutral',
                'confidence': 0.0,
                'tweet_count': 0,
                'sentiment_breakdown': {'positive': 0, 'negative': 0, 'neutral': 0}
            }
        except Exception as e:
            logger.error(f"Error analyzing router sentiment: {str(e)}")
            return {
                'sentiment': 'neutral',
                'confidence': 0.0,
                'error': str(e)
            }

    def _combine_signals(self, ai_analysis: Dict[str, Any], tech_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Combine AI and technical analysis signals"""
        try:
            if not ai_analysis or not tech_analysis:
                return {
                    'signal': 'neutral',
                    'confidence': 0.0,
                    'symbol': '',
                    'volatility': 0.0
                }

            # Weight the confidence scores (65% AI, 20% Technical)
            ai_confidence = float(ai_analysis.get('confidence', 0))
            tech_confidence = float(tech_analysis.get('confidence', 0))
            combined_confidence = (ai_confidence * 0.7) + (tech_confidence * 0.3)

            # Only proceed if signals align
            ai_signal = ai_analysis.get('signal', 'neutral')
            tech_signal = tech_analysis.get('signal', 'neutral')

            if ai_signal == tech_signal and ai_signal != 'neutral':
                return {
                    'signal': ai_signal,
                    'confidence': combined_confidence,
                    'symbol': ai_analysis.get('symbol', ''),
                    'volatility': tech_analysis.get('volatility', 0.0),
                    'rsi': tech_analysis.get('rsi', 50),
                    'market_trend': tech_analysis.get('market_trend', 'neutral'),
                    'ai_analysis': ai_analysis,
                    'tech_analysis': tech_analysis
                }

            return {
                'signal': 'neutral',
                'confidence': 0.0,
                'symbol': ai_analysis.get('symbol', ''),
                'volatility': 0.0
            }

        except Exception as e:
            logger.error(f"Error combining signals: {str(e)}")
            return {
                'signal': 'neutral',
                'confidence': 0.0,
                'symbol': '',
                'volatility': 0.0
            }

    async def check_opportunities(self) -> List[Dict[str, Any]]:
        """Check for trading opportunities across chains"""
        opportunities = []

        try:
            # Monitor base token pairs and apply technical analysis
            token_symbols = ['Whale', 'Goglz', 'Equal', 'Metro', 'Toona', 'Hedgy', 'wS', 'Froq', 'SWPx', 'Sonic', 'ECO', 'scUSD']

            for symbol in token_symbols:
                try:
                    # Get current prices and update history
                    prices = await self.trading.get_token_prices([symbol])
                    if prices and isinstance(prices, dict) and symbol in prices:
                        price = prices[symbol]
                        await self.trading.update_price_history(symbol, price)

                        # Combine AI and technical analysis
                        ai_analysis = await self.trading.analyze_trading_opportunity(symbol)

                        # Perform technical analysis if historical data is available
                        if self.historical_data is not None:
                            tech_analysis = analyze_market_signals(self.historical_data)

                            # Combine signals
                            combined_signal = self._combine_signals(ai_analysis, tech_analysis)
                            if combined_signal and self._validate_opportunity(combined_signal):
                                opportunities.append(self._prepare_trade_from_analysis(combined_signal))

                        elif ai_analysis and self._validate_opportunity(ai_analysis):
                            opportunities.append(self._prepare_trade_from_analysis(ai_analysis))

                except Exception as e:
                    logger.error(f"Error processing symbol {symbol}: {str(e)}")
                    continue

            # Update market conditions
            await self._update_market_conditions(token_symbols)

        except Exception as e:
            logger.error(f"Error checking opportunities: {str(e)}")

        return opportunities

    def _validate_opportunity_from_analysis(self, analysis: str) -> bool:
        """Validate if an opportunity from analysis meets criteria"""
        try:
            if not analysis or not isinstance(analysis, str):
                return False

            analysis = analysis.lower()

            # Check for strong buy/sell signals
            if not any(signal in analysis for signal in ['buy', 'sell', 'long', 'short']):
                return False

            # Look for confidence indicators
            confidence_indicators = ['strong', 'confident', 'clear', 'definite']
            if not any(indicator in analysis for indicator in confidence_indicators):
                return False

            # Add randomness for exploration
            if random.random() < self.exploration_rate:
                logger.info("Exploring new opportunity from analysis")
                return True

            return True
        except Exception as e:
            logger.error(f"Error validating opportunity from analysis: {str(e)}")
            return False

    def _validate_opportunity(self, analysis: Dict[str, Any]) -> bool:
        """Validate if an opportunity meets trading criteria"""
        try:
            if not analysis or not isinstance(analysis, dict):
                return False

            # Check confidence threshold
            if not analysis.get('confidence') or analysis['confidence'] < self.min_confidence_threshold:
                return False

            # Check technical indicators if available
            if 'rsi' in analysis:
                rsi = float(analysis['rsi'])
                if analysis.get('signal') == 'buy' and rsi > self.rsi_overbought:
                    return False
                if analysis.get('signal') == 'sell' and rsi < self.rsi_oversold:
                    return False

            # Check market conditions
            symbol = analysis.get('symbol')
            if not symbol or not self._check_market_conditions(symbol):
                return False

            # Add exploration factor
            if random.random() < self.exploration_rate:
                logger.info("Exploring opportunity despite lower confidence")
                return True

            return True
        except Exception as e:
            logger.error(f"Error validating opportunity: {str(e)}")
            return False

    async def _update_market_conditions(self, symbols: List[str]):
        """Update market conditions assessment"""
        try:
            for symbol in symbols:
                indicators = await self.trading.calculate_technical_indicators(symbol)
                if indicators:
                    self.market_conditions[symbol] = {
                        'volatility': indicators['volatility'],
                        'trend_strength': indicators['trend_strength'],
                        'last_update': time.time()
                    }
        except Exception as e:
            logger.error(f"Error updating market conditions: {str(e)}")

    def _check_market_conditions(self, symbol: str) -> bool:
        """Check if market conditions are favorable"""
        try:
            conditions = self.market_conditions.get(symbol)
            if not conditions:
                return False

            # Check if conditions are fresh (within last hour)
            if time.time() - conditions['last_update'] > 3600:
                return False

            # Avoid extremely volatile markets
            if conditions['volatility'] > 0.4:  # 40% annualized volatility
                return False

            return True
        except Exception as e:
            logger.error(f"Error checking market conditions: {str(e)}")
            return False

    def _prepare_trade_from_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare trade parameters from analysis"""
        return {
            'source_chain': self.config['default_source_chain'],
            'target_chain': self._select_target_chain(analysis),
            'token_in': analysis['symbol'],
            'token_out': 'USDC',  # Default to stable coin for safety
            'amount': self._calculate_position_size(analysis),
            'slippage': self._calculate_slippage(analysis['volatility']),
            'analysis': analysis
        }

    def _select_target_chain(self, analysis: Dict[str, Any]) -> str:
        """Select best target chain based on analysis"""
        # Implementation depends on available chains and their characteristics
        return "Sonic"  # Default to Sonic for now

    def _calculate_position_size(self, analysis: Dict[str, Any]) -> Decimal:
        """Calculate appropriate position size based on confidence and conditions"""
        base_size = self.max_position_size * Decimal(str(analysis['confidence']))
        return min(base_size, self.max_position_size)

    def _calculate_slippage(self, volatility: float) -> Decimal:
        """Calculate appropriate slippage tolerance based on volatility"""
        return Decimal(str(min(volatility * 2, 0.03)))  # Max 3% slippage

    def _update_trade_history(self, trade: Dict[str, Any], result: Dict[str, Any]):
        """Update trade history and adjust parameters based on success"""
        try:
            self.success_history.append({
                'timestamp': time.time(),
                'trade': trade,
                'result': result
            })

            # Keep only recent history
            if len(self.success_history) > 100:
                self.success_history = self.success_history[-100:]

            # Adjust parameters based on success
            self._adjust_parameters()

        except Exception as e:
            logger.error(f"Error updating trade history: {str(e)}")

    def _adjust_parameters(self):
        """Adjust trading parameters based on recent performance"""
        try:
            if len(self.success_history) < 10:
                return

            recent_trades = self.success_history[-10:]
            success_rate = sum(1 for trade in recent_trades if trade['result']['success']) / len(recent_trades)

            # Adjust confidence threshold
            if success_rate < 0.5:
                self.min_confidence_threshold = min(0.9, self.min_confidence_threshold + self.learning_rate)
            else:
                self.min_confidence_threshold = max(0.6, self.min_confidence_threshold - self.learning_rate)

            # Adjust exploration rate
            self.exploration_rate = max(0.1, min(0.3, (1 - success_rate) * 0.5))

        except Exception as e:
            logger.error(f"Error adjusting parameters: {str(e)}")

    async def run_loop(self):
        """Main agent loop"""
        try:
            logger.info(f"Starting {self.name} agent loop")
            
            # Check if there are any authorized accounts configured
            if not trading_auth.has_authorized_accounts():
                logger.warning("No authorized trading accounts configured. Agent will monitor but not execute trades.")
                authorized_mode = False
            else:
                logger.info(f"Authorized trading accounts: {', '.join(trading_auth.get_authorized_accounts())}")
                authorized_mode = True
            
            # Connect to price service
            if not price_service._session:
                logger.info("Connecting to price service...")
                await price_service.connect()
                logger.info("✅ Price service connected")
            
            while True:
                try:
                    # Check for opportunities
                    opportunities = await self.check_opportunities()
    
                    for opp in opportunities:
                        # Get combined analysis from all agents
                        analysis = await self._get_combined_agent_analysis(opp)
    
                        if analysis.get('confidence', 0) >= self.min_confidence_threshold:
                            opp['analysis'] = analysis
                            
                            # If we're in authorized mode, proceed with trade
                            if authorized_mode:
                                # First verify price data
                                token_address = opp.get('token_address')
                                chain_id = opp.get('chain_id')
                                
                                if token_address and chain_id:
                                    # Get accurate price data
                                    price_data = await price_service.get_token_price(token_address, chain_id)
                                    if price_data:
                                        opp['price_data'] = price_data
                                        logger.info(f"Verified price for {token_address}: ${price_data.get('price')}")
                                
                                # Execute trade with agent wallet
                                if await self.execute_trade(opp):
                                    logger.info(f"Successfully executed trade: {opp}")
                            else:
                                # Just log the opportunity but don't execute
                                logger.info(f"Found trading opportunity but no authorized accounts: {opp}")
                                await self.store_dashboard_post(
                                    type='trading_opportunity',
                                    content=f"Potential trade identified: {opp.get('token', 'Unknown Token')}",
                                    title='Trading Opportunity',
                                    metadata={
                                        'token': opp.get('token', 'Unknown'),
                                        'confidence': analysis.get('confidence', 0),
                                        'analysis': analysis
                                    }
                                )
    
                    # Post market insight to Twitter
                    market_insight = await self.generate_market_insight_post()
                    if market_insight and self.browser:
                        await self.post_to_twitter(market_insight)
    
                    # Wait for configured delay
                    await asyncio.sleep(self.config.get('loop_delay', 300))
    
                except Exception as e:
                    logger.error(f"Error in main loop: {str(e)}")
                    await asyncio.sleep(60)  # Error cooldown
        
        except Exception as e:
            logger.error(f"Critical error in run_loop: {str(e)}", exc_info=True)
            # Try to reconnect services and continue
            try:
                await price_service.connect()
                await self.trading.connect()
                logger.info("Reconnected services after critical error")
            except:
                logger.error("Failed to reconnect services", exc_info=True)

    async def _get_combined_agent_analysis(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Get combined analysis from main instructor and helper agents"""
        try:
            analyses = []

            # Get main instructor (Anthropic) analysis
            if self.ai_processor:
                main_analysis = await self.ai_processor.generate_response(
                    f"Analyze trading opportunity: {json.dumps(opportunity, default=str)}",
                    context={"market_conditions": self.market_conditions}
                )
                analyses.append({"source": "main_instructor", "weight": 0.6, "analysis": main_analysis})

            # Get helper agent analyses
            if self.config.get('ai', {}).get('helper_agents'):
                for helper in self.config['ai']['helper_agents']:
                    helper_analysis = await self.ai_processor.generate_response(
                        f"Analyze trading opportunity: {json.dumps(opportunity, default=str)}",
                        context={"model": helper['model']}
                    )
                    analyses.append({
                        "source": helper['name'],
                        "weight": 0.2,
                        "analysis": helper_analysis
                    })

            # Combine analyses
            combined_confidence = sum(
                float(a.get('weight', 0)) * self._extract_confidence(a.get('analysis', ''))
                for a in analyses
            )

            return {
                "confidence": combined_confidence,
                "analyses": analyses
            }

        except Exception as e:
            logger.error(f"Error getting combined agent analysis: {str(e)}")
            return {"confidence": 0, "analyses":[]}

    def _extract_confidence(self, analysis: str) -> float:
        """Extract confidence score from analysis text"""
        try:
            if not analysis:
                return 0.0

            analysis = analysis.lower()

            # Check for explicit confidence mentions
            if "high confidence" in analysis or "very confident" in analysis:
                return 0.8
            elif "medium confidence" in analysis or "moderately confident" in analysis:
                return 0.6
            elif "low confidence" in analysis or "uncertain" in analysis:
                return 0.4

            # Check for strong positive/negative indicators
            positive_indicators = ["strongly recommend", "clear opportunity", "optimalconditions"]
            negative_indicators = ["risky", "uncertain", "volatile", "caution"]

            confidence = 0.5  # Default neutral confidence

            # Adjust based on indicators
            for indicator in positive_indicators:
                if indicator in analysis:
                    confidence += 0.1

            for indicator in negative_indicators:
                if indicator in analysis:
                    confidence -= 0.1

            # Ensure confidence stays within bounds
            return max(0.1, min(0.9, confidence))

        except Exception as e:
            logger.error(f"Error extracting confidence: {str(e)}")
            return 0.5  # Return neutral confidence on error

    async def execute_trade(self, opportunity: Dict[str, Any]) -> bool:
        """Execute trade based on opportunity"""
        try:
            trade_params = self._prepare_trade_from_analysis(opportunity['analysis'])
            
            # Get agent wallet from config if available
            agent_wallet = self.config.get("agent_wallet_address")
            
            # In automated mode, agent wallet should be one of the authorized wallets
            if agent_wallet and not trading_auth.is_account_authorized(agent_wallet):
                logger.warning(f"Agent wallet {agent_wallet} is not in authorized list - cannot execute trade")
                return False
                
            result = await self.process_trade_command(
                amount=trade_params['amount'],
                token_address=trade_params['token_in'],
                trade_type='buy' if opportunity.get('analysis', {}).get('signal') == 'buy' else 'sell',
                to_address=self.config.get("default_recipient_address"),
                chain_id=trade_params['target_chain'],
                user_address=agent_wallet  # Pass agent wallet for authorization
            )
            
            if result and result.get('success'):
                logger.info(f"Trade executed successfully: {result}")
                # Add to successful trades data
                await self.store_dashboard_post(
                    type='executed_trade',
                    content=f"Successfully executed trade for {trade_params.get('token_in')}",
                    title='Trade Executed',
                    metadata={
                        'token': trade_params.get('token_in'),
                        'amount': trade_params.get('amount'),
                        'chain_id': trade_params.get('target_chain'),
                        'price_data': opportunity.get('price_data'),
                        'tx_hash': result.get('result', {}).get('tx_hash')
                    }
                )
                return True
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'Trade execution failed'
                logger.error(f"Trade execution failed: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}", exc_info=True)
            return False


class MockTradingConnection(TradingConnection):
    """Mock trading connection for testing"""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize with config"""
        super().__init__(config or {})
        self.test_data = []
        self.networks = NETWORKS

    async def connect(self) -> bool:
        """Initialize mock connection"""
        logger.debug("MockTradingConnection.connect() called")
        return True

    async def get_token_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get mock token prices"""
        logger.debug(f"MockTradingConnection.get_token_prices({symbols}) called")
        return {
            'ETH': 2450.00,
            'USDC': 1.00,
            'USDT': 1.00,
            'WBTC': 48000.00
        }

    async def calculate_technical_indicators(self, symbol: str) -> Dict[str, float]:
        """Calculate mock technical indicators"""
        logger.debug(f"MockTradingConnection.calculate_technical_indicators({symbol}) called")
        return {
            'volatility': 0.2,
            'trend_strength': 0.8,
        }

    async def analyze_trading_opportunity(self, symbol: str) -> Dict[str, Any]:
        """Analyze mock trading opportunity"""
        logger.debug(f"MockTradingConnection.analyze_trading_opportunity({symbol}) called")
        return {
            'confidence': 0.85,
            'signal': 'buy',
            'symbol': symbol,
            'volatility': 0.2
        }

    async def execute_cross_chain_swap(self, trade_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a mock cross-chain swap"""
        logger.debug(f"MockTradingConnection.execute_cross_chain_swap() called with params: {json.dumps(trade_params, indent=2)}")

        # Store execution result for test verification
        result = {
            "success": True,
            "tx_hash": "0x123...abc",
            "status": "completed",
            "amount": trade_params.get('amount'),
            "source_chain": trade_params.get('source_chain'),
            "target_chain": trade_params.get('target_chain')
        }
        self.test_data.append(result)

        return {"success": True, "result": result}