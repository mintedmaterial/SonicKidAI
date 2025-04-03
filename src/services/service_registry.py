"""Service registry for managing service instances"""
import logging
import asyncio
import time
from typing import Dict, Any, Optional, List
from src.services.market_service import MarketService
from src.services.dexscreener_service import DexScreenerService, SONIC, BASE, ETH
from src.services.cryptopanic_service import CryptoPanicService 
from src.services.historical_price_service import HistoricalPriceService
from src.services.equalizer_service import EqualizerService
from src.services.huggingface_service import HuggingFaceService
from src.services.market_visualization_service import MarketVisualizationService
from src.utils.ai_processor import AIProcessor
from src.connections.openrouter import OpenRouterConnection

logger = logging.getLogger(__name__)

# Shared AI model configuration
DEFAULT_AI_CONFIG = {
    'model': 'anthropic/claude-3-7-sonnet-20250219',  # Latest stable model
    'base_url': 'https://openrouter.ai/api/v1',
    'headers': {
        'HTTP-Referer': 'https://github.com/ZerePy/sonic-kid',  # Required by OpenRouter
        'X-Title': 'Sonic Kid Agent',  # Optional, helps OpenRouter track our app
    }
}

class ServiceRegistry:
    """Service registry for managing service instances"""
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServiceRegistry, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize service registry"""
        if not self._initialized:
            self.market_service: Optional[MarketService] = None
            self.dex_service: Optional[DexScreenerService] = None
            self.crypto_panic: Optional[CryptoPanicService] = None
            self.historical_price: Optional[HistoricalPriceService] = None
            self.equalizer: Optional[EqualizerService] = None
            self.huggingface: Optional[HuggingFaceService] = None
            self.visualization: Optional[MarketVisualizationService] = None
            self.ai_processor: Optional[AIProcessor] = None
            self.openrouter: Optional[OpenRouterConnection] = None
            self._initialized = True
            self._monitor_task = None
            self._cache: Dict[str, Any] = {}
            self._last_request_time = 0
            self._rate_limit_delay = 0.2  # 200ms between requests
            logger.info("Service registry initialized")

    # Agent Interface Methods

    async def get_market_analysis(self, chain_id: Optional[str] = None, 
                                include_historical: bool = False) -> Dict[str, Any]:
        """Get comprehensive market analysis for agent consumption"""
        try:
            # Get latest analysis
            analysis = await self.get_latest_analysis(chain_id)
            if not analysis:
                return {"error": "No analysis available"}

            response = {
                "analysis": analysis,
                "latest_alert": await self.get_latest_alert(),
                "timestamp": analysis.get("timestamp"),
                "chains_monitored": [SONIC, BASE, ETH]
            }

            # Add historical data if requested
            if include_historical and self.historical_price:
                for chain in [SONIC, BASE, ETH]:
                    history = await self.historical_price.get_price_history(chain)
                    if history:
                        response[f"{chain}_history"] = history

            return response

        except Exception as e:
            logger.error(f"Error getting market analysis for agents: {str(e)}")
            return {"error": str(e)}

    async def get_formatted_pair_data(self, chain_id: str = SONIC) -> List[Dict[str, Any]]:
        """Get formatted pair data for agent consumption"""
        try:
            # Check cache first
            cache_key = f"formatted_pairs_{chain_id}"
            cached = self._get_cached_data(cache_key)
            if cached:
                return cached

            # Get fresh data
            pairs = await self.dex_service.get_pairs(chain_id)
            if not pairs:
                return []

            # Format data for agents
            formatted = []
            for pair in pairs:
                formatted_pair = {
                    "symbol": pair.get("pair", ""),
                    "price_usd": float(pair.get("priceUsd", 0)),
                    "price_change_24h": float(pair.get("priceChange24h", 0)),
                    "volume_24h": float(pair.get("volume24h", 0)),
                    "liquidity": float(pair.get("liquidity", 0)),
                    "chain": chain_id,
                    "address": pair.get("pairAddress", "")
                }
                formatted.append(formatted_pair)

            # Cache the formatted data
            self._cache_data(cache_key, formatted)
            return formatted

        except Exception as e:
            logger.error(f"Error formatting pair data: {str(e)}")
            return []

    async def get_chain_metrics(self, chain_id: str) -> Dict[str, Any]:
        """Get chain-specific metrics for agent consumption"""
        try:
            analysis = await self.get_latest_analysis(chain_id)
            if not analysis:
                return {"error": "No metrics available"}

            metrics = analysis.get("metrics", {})
            metrics.update({
                "chain": chain_id,
                "timestamp": analysis.get("timestamp"),
                "sentiment": analysis.get("sentiment", "neutral")
            })

            return metrics

        except Exception as e:
            logger.error(f"Error getting chain metrics: {str(e)}")
            return {"error": str(e)}

    def _get_cached_data(self, key: str) -> Optional[Any]:
        """Get cached data with rate limiting"""
        try:
            now = time.time()
            if now - self._last_request_time < self._rate_limit_delay:
                asyncio.sleep(self._rate_limit_delay - (now - self._last_request_time))
            self._last_request_time = now

            return self._cache.get(key)
        except Exception as e:
            logger.error(f"Error accessing cached data: {str(e)}")
            return None

    def _cache_data(self, key: str, data: Any) -> None:
        """Cache data with timestamp"""
        self._cache[key] = data

    async def get_dexscreener(self) -> Optional[DexScreenerService]:
        """Get or initialize DexScreener service"""
        if not self.dex_service:
            self.dex_service = DexScreenerService()
            success = await self.dex_service.connect()
            if success:
                logger.info("✅ DexScreener service initialized with WebSocket connection")
                # Start monitoring after successful connection
                await self.start_market_monitoring()
            else:
                logger.error("❌ Failed to initialize DexScreener service")
                return None
        return self.dex_service

    async def start_market_monitoring(self):
        """Start background market monitoring"""
        if not self._monitor_task:
            self._monitor_task = asyncio.create_task(self._run_market_monitor())
            logger.info("✅ Market monitoring started")

    async def _run_market_monitor(self):
        """Run continuous market monitoring"""
        try:
            while True:
                try:
                    # Monitor all supported chains
                    for chain_id in [SONIC, BASE, ETH]:
                        # Get latest market data
                        market_data = await self.get_market_data(chain_id)

                        if market_data and not "error" in market_data:
                            # Analyze price movements
                            if self.ai_processor:
                                analysis = await self.analyze_market_data(market_data)

                                if analysis:
                                    # Cache analysis results with chain context
                                    cache_key = f"latest_analysis_{chain_id}"
                                    self._cache[cache_key] = {
                                        "timestamp": market_data.get("timestamp"),
                                        "analysis": analysis,
                                        "pairs": market_data.get("pairs", [])[:5]  # Cache top 5 pairs
                                    }
                                    logger.info(f"Market analysis updated for {chain_id}")

                                    # Check for significant price movements
                                    await self._check_price_alerts(chain_id, analysis)

                    await asyncio.sleep(60)  # Update every minute
                except Exception as e:
                    logger.error(f"Error in market monitor: {str(e)}")
                    await asyncio.sleep(5)  # Brief delay on error

        except asyncio.CancelledError:
            logger.info("Market monitoring stopped")

    async def _check_price_alerts(self, chain_id: str, analysis: Dict[str, Any]):
        """Check for significant price movements and generate alerts"""
        try:
            metrics = analysis.get("metrics", {})
            sentiment = analysis.get("sentiment")

            # Define alert thresholds
            VOLUME_THRESHOLD = 100000  # $100k volume
            PRICE_CHANGE_THRESHOLD = 10  # 10% change

            if (metrics.get("total_volume", 0) > VOLUME_THRESHOLD or 
                abs(metrics.get("avg_change", 0)) > PRICE_CHANGE_THRESHOLD):

                alert = {
                    "chain": chain_id,
                    "timestamp": analysis.get("timestamp"),
                    "sentiment": sentiment,
                    "metrics": metrics,
                    "analysis": analysis.get("analysis"),
                }

                # Cache the alert
                self._cache["latest_alert"] = alert
                logger.info(f"Generated market alert for {chain_id}: {sentiment} movement detected")

        except Exception as e:
            logger.error(f"Error checking price alerts: {str(e)}")

    async def analyze_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market data using AI processor"""
        try:
            if not self.ai_processor:
                return None

            # Format data for analysis
            pairs = market_data.get("pairs", [])
            if not pairs:
                return None

            # Create analysis prompt
            prompt = (
                f"Analyze these market metrics for {len(pairs)} pairs:\n"
                f"- Price changes: {[p.get('priceChange24h', 0) for p in pairs[:3]]}\n"
                f"- Volume: {[p.get('volume24h', 0) for p in pairs[:3]]}\n"
                f"- Liquidity: {[p.get('liquidity', 0) for p in pairs[:3]]}\n"
                "Provide market sentiment and key insights focusing on trading opportunities "
                "and potential risks. Also analyze the relationship between these metrics."
            )

            # Get AI analysis
            analysis = await self.ai_processor.generate_response(prompt)

            # Calculate advanced metrics
            price_changes = [p.get('priceChange24h', 0) for p in pairs]
            volumes = [p.get('volume24h', 0) for p in pairs]
            liquidities = [p.get('liquidity', 0) for p in pairs]

            sentiment = "bullish" if any(pc > 5 for pc in price_changes) else "neutral"
            if any(pc < -5 for pc in price_changes):
                sentiment = "bearish"

            return {
                "timestamp": market_data.get("timestamp"),
                "sentiment": sentiment,
                "analysis": analysis,
                "metrics": {
                    "total_volume": sum(volumes),
                    "avg_change": sum(price_changes) / len(pairs) if pairs else 0,
                    "total_liquidity": sum(liquidities),
                    "volume_change": sum(volumes) / sum(liquidities) if sum(liquidities) > 0 else 0,
                    "volatility": max(abs(pc) for pc in price_changes) if price_changes else 0
                }
            }

        except Exception as e:
            logger.error(f"Error analyzing market data: {str(e)}")
            return None

    async def get_market_data(self, query: str, chain_id: Optional[str] = None) -> Dict[str, Any]:
        """Get market data using DexScreener service"""
        try:
            dex_service = await self.get_dexscreener()
            if not dex_service:
                return {"error": "DexScreener service unavailable"}

            # Get pairs data
            pairs = await dex_service.get_pairs(query)
            if not pairs:
                return {"error": f"No pairs found for {query}"}

            # Format response
            response = {
                "pairs": pairs,
                "chain_ids": [SONIC, BASE, ETH],
                "timestamp": pairs[0].get("timestamp") if pairs else None
            }

            # Add AI analysis if processor available
            if self.ai_processor:
                context = f"Analyze these market pairs: {str(pairs[:3])}..."
                analysis = await self.ai_processor.generate_response(context)
                response["analysis"] = analysis

            return response

        except Exception as e:
            logger.error(f"Error getting market data: {str(e)}")
            return {"error": str(e)}

    async def get_latest_analysis(self, chain_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get latest market analysis for specified chain"""
        try:
            if chain_id:
                return self._cache.get(f"latest_analysis_{chain_id}")
            return {chain: self._cache.get(f"latest_analysis_{chain}") 
                   for chain in [SONIC, BASE, ETH] 
                   if self._cache.get(f"latest_analysis_{chain}")}
        except Exception as e:
            logger.error(f"Error getting latest analysis: {str(e)}")
            return None

    async def get_latest_alert(self) -> Optional[Dict[str, Any]]:
        """Get most recent market alert"""
        return self._cache.get("latest_alert")

    async def initialize_services(self, config: Dict[str, Any], db_pool: Any = None) -> bool:
        """Initialize all services with proper error handling and retries"""
        try:
            logger.info("Initializing core AI services...")

            # Configure OpenRouter
            api_key = config.get('openrouter_api_key')
            if not api_key:
                logger.error("OpenRouter API key not found in configuration")
                return False

            # Initialize OpenRouter with proper configuration
            openrouter_config = {
                **DEFAULT_AI_CONFIG,
                'api_key': api_key,
                'name': 'openrouter'
            }
            logger.info("Configuring OpenRouter with Anthropic access...")

            # Initialize OpenRouter with retry logic
            retry_count = 0
            max_retries = 3
            while retry_count < max_retries:
                try:
                    self.openrouter = OpenRouterConnection(openrouter_config)
                    await self.openrouter.connect()
                    logger.info("✅ OpenRouter initialized successfully")
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        logger.error(f"❌ Failed to initialize OpenRouter after {max_retries} attempts: {str(e)}")
                        return False
                    logger.warning(f"OpenRouter initialization attempt {retry_count} failed, retrying...")
                    await asyncio.sleep(1)

            # Initialize AI Processor with configuration
            ai_config = {
                **DEFAULT_AI_CONFIG,
                'api_key': api_key,
            }
            self.ai_processor = AIProcessor(config=ai_config)
            logger.info("✅ AI Processor initialized")

            # Initialize DexScreener service
            self.dex_service = await self.get_dexscreener()
            if not self.dex_service:
                logger.error("❌ Failed to initialize DexScreener service")
                return False
            logger.info("✅ DexScreener service initialized")

            # Initialize other services as needed...
            self.historical_price = HistoricalPriceService() # Initialize historical price service
            await self.historical_price.connect() # Assuming it has a connect method

            logger.info("✅ All services initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Error initializing services: {str(e)}", exc_info=True)
            return False

    async def close_services(self):
        """Close all services properly with validation"""
        try:
            # Stop monitoring task first
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
                logger.info("Market monitoring stopped")

            services_to_close = [
                ('DexScreener', self.dex_service),
                ('OpenRouter', self.openrouter),
                ('HuggingFace', self.huggingface),
                ('Market Service', self.market_service),
                ('Historical Price Service', self.historical_price) # Add historical price service
            ]

            for service_name, service in services_to_close:
                if service:
                    try:
                        await service.close()
                        logger.info(f"✅ {service_name} closed successfully")
                    except Exception as e:
                        logger.error(f"❌ Error closing {service_name}: {str(e)}")

            # Clear cache
            self._cache.clear()
            logger.info("✅ All services closed successfully")

        except Exception as e:
            logger.error(f"❌ Error during service cleanup: {str(e)}")
            raise

    def get_service_statuses(self) -> Dict[str, bool]:
        """Get initialization status of all services"""
        return {
            'dex_service': bool(self.dex_service and getattr(self.dex_service, '_initialized', False)),
            'openrouter': bool(self.openrouter and getattr(self.openrouter, '_initialized', False)),
            'ai_processor': bool(self.ai_processor),
            'market_service': bool(self.market_service and getattr(self.market_service, '_initialized', False)),
            'market_monitor': bool(self._monitor_task and not self._monitor_task.done()),
            'historical_price': bool(self.historical_price and getattr(self.historical_price, '_initialized', False)) #Added for historical price
        }

# Global service registry instance
service_registry = ServiceRegistry()