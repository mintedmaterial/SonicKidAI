"""Market Data Service for token price and sentiment analysis"""
import logging
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("services.market_data")

class MarketDataService:
    """Service for fetching and processing market data"""
    
    def __init__(self, db=None, config: Optional[Dict[str, Any]] = None):
        """Initialize the market data service"""
        self.db = db
        self.config = config or {}
        self.session = None
        self._initialized = False
        self._update_task = None
        self.sentiment_worker = None
        self.cache = {}
        self.cache_time = {}
        self.cache_ttl = 60 * 5  # 5 minutes TTL
        logger.info("MarketDataService initialized")
        
    async def initialize(self):
        """Initialize the session and connections"""
        if not self._initialized:
            if not self.session:
                self.session = aiohttp.ClientSession()
            self._initialized = True
            
            # Start background update task
            self._update_task = asyncio.create_task(self._background_updates())
            
            logger.info("MarketDataService session created")
        return True
    
    async def _background_updates(self):
        """Background task to update market data periodically"""
        try:
            logger.info("Starting background market data updates")
            while self._initialized:
                try:
                    # Update token data for major tokens
                    for token in ["SONIC", "ETH", "BTC"]:
                        await self.get_token_data(token)
                    logger.debug("Market data updated")
                except Exception as e:
                    logger.error(f"Error in background update: {str(e)}")
                
                # Wait for next update cycle
                await asyncio.sleep(300)  # 5 minutes
        except asyncio.CancelledError:
            logger.info("Background update task cancelled")
        except Exception as e:
            logger.error(f"Unhandled error in background updates: {str(e)}")
            
    async def close(self):
        """Close any open connections"""
        if self._update_task and not self._update_task.done():
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
            self._update_task = None
            
        if self.session:
            await self.session.close()
            self.session = None
            
        self._initialized = False
        logger.info("MarketDataService closed")
        
    async def get_token_data(self, token: str, chain: str = "sonic") -> Dict[str, Any]:
        """Get token data from available sources"""
        try:
            result = await self.get_token_price(token, chain)
            
            # Store in database if connected
            if self.db and not result.get("error"):
                # Database storage implementation would go here
                pass
                
            return result
        except Exception as e:
            logger.error(f"Error getting token data: {str(e)}")
            return {
                "price": 0,
                "volume_24h": 0,
                "liquidity": 0,
                "error": str(e)
            }
        
    async def get_token_price(self, token: str, chain: str = "sonic") -> Dict[str, Any]:
        """Get token price from available sources"""
        try:
            cache_key = f"{token}_{chain}"
            # Check cache first
            if cache_key in self.cache:
                now = datetime.now().timestamp()
                if now - self.cache_time.get(cache_key, 0) < self.cache_ttl:
                    logger.info(f"Returning cached data for {token} on {chain}")
                    return self.cache[cache_key]
            
            # Fetch live data
            logger.info(f"Fetching price for {token} on {chain}")
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token}"
            
            if not self.session:
                await self.initialize()
                
            max_retries = 3
            retry_count = 0
            retry_delay = 0.1  # 100ms
            
            while retry_count < max_retries:
                try:
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get("pairs"):
                                # Filter by chain if needed
                                if chain != "any":
                                    pairs = [p for p in data["pairs"] if p.get("chainId") == chain]
                                else:
                                    pairs = data["pairs"]
                                    
                                # Sort by liquidity
                                pairs.sort(key=lambda x: float(x.get("liquidity", {}).get("usd", 0)), reverse=True)
                                
                                if pairs:
                                    result = {
                                        "price": float(pairs[0].get("priceUsd", 0)),
                                        "volume_24h": float(pairs[0].get("volume", {}).get("h24", 0)),
                                        "liquidity": float(pairs[0].get("liquidity", {}).get("usd", 0)),
                                        "priceChange24h": float(pairs[0].get("priceChange", {}).get("h24", 0)),
                                        "pairAddress": pairs[0].get("pairAddress"),
                                        "pairName": pairs[0].get("pairName"),
                                        "baseToken": pairs[0].get("baseToken", {}).get("name", token),
                                        "quoteToken": pairs[0].get("quoteToken", {}).get("name", "Unknown"),
                                        "timestamp": datetime.now(),
                                        "source": "dexscreener"
                                    }
                                    
                                    # Cache the result
                                    self.cache[cache_key] = result
                                    self.cache_time[cache_key] = datetime.now().timestamp()
                                    
                                    return result
                                    
                        # Failed request - increment retry count
                        retry_count += 1
                        if retry_count >= max_retries:
                            # Max retries exceeded
                            break
                            
                        # Wait before next retry
                        logger.warning(f"Request failed, retrying {retry_count}/{max_retries}...")
                        await asyncio.sleep(retry_delay)
                        
                except Exception as e:
                    logger.error(f"Request error: {str(e)}")
                    retry_count += 1
                    if retry_count >= max_retries:
                        break
                    await asyncio.sleep(retry_delay)
            
            logger.warning(f"No price data found for {token} on {chain}")
            return {
                "price": 0,
                "volume_24h": 0,
                "liquidity": 0,
                "priceChange24h": 0,
                "error": "No data found",
                "timestamp": datetime.now(),
                "source": "error"
            }
            
        except Exception as e:
            logger.error(f"Error fetching price for {token} on {chain}: {str(e)}")
            return {
                "price": 0,
                "volume_24h": 0,
                "liquidity": 0,
                "priceChange24h": 0,
                "error": str(e),
                "timestamp": datetime.now(),
                "source": "error"
            }
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment using worker if available"""
        try:
            if self.sentiment_worker:
                result = await self.sentiment_worker._analyze_text(text)
                return result
            else:
                # Return neutral sentiment if no worker available
                return {
                    "sentiment": "neutral",
                    "confidence": 0.5,
                    "source": "fallback"
                }
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {
                "sentiment": "neutral",
                "confidence": 0,
                "error": str(e),
                "source": "error"
            }
    
    async def get_market_sentiment(self) -> Dict[str, Any]:
        """Get market sentiment data"""
        # For now just returning neutral data
        return await self.analyze_sentiment("Market sentiment analysis request")
