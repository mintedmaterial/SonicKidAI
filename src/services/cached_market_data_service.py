"""
Cached Market Data Service

This module wraps the market data service with our cache system
to ensure optimal refresh rates while respecting rate limits.
"""
import logging
import json
import time
from typing import Dict, Any, Optional, List, Tuple
import asyncio

from src.services.market_data_service import MarketDataService
from src.services.api_cache_wrapper import (
    cached_price_endpoint,
    cached_sentiment_endpoint,
    cached_news_endpoint,
    cached_fear_greed_endpoint,
    cached_trending_endpoint,
    cached_dex_volume_endpoint,
    cached_sonic_pairs_endpoint,
    cached_sales_endpoint,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CachedMarketDataService:
    """
    Cached version of the market data service that implements smart caching
    with configurable refresh rates for different endpoint types.
    """
    
    def __init__(self, market_service: MarketDataService):
        """
        Initialize with an existing market data service instance
        
        Args:
            market_service: The underlying market data service to wrap
        """
        self.market_service = market_service
        self._initialized = False
        logger.info("CachedMarketDataService initialized")
    
    async def initialize(self) -> bool:
        """Initialize the service and underlying market service"""
        if not self._initialized:
            # Initialize underlying service
            success = await self.market_service.initialize()
            if success:
                self._initialized = True
                logger.info("✅ CachedMarketDataService initialized")
            else:
                logger.error("❌ Failed to initialize underlying market service")
            return success
        return True
    
    async def close(self) -> None:
        """Close the service and underlying market service"""
        if self._initialized:
            try:
                await self.market_service.close()
                self._initialized = False
                logger.info("✅ CachedMarketDataService closed")
            except Exception as e:
                logger.error(f"❌ Error closing market service: {str(e)}")
    
    # ------ Cached market data methods ------
    
    @cached_price_endpoint()
    async def get_token_data(self, token_address: str) -> Dict[str, Any]:
        """
        Get token data with price caching (60s refresh)
        
        Args:
            token_address: Token symbol or address
        
        Returns:
            Token data with price information
        """
        logger.debug(f"Fetching fresh token data for {token_address}")
        return await self.market_service.get_token_data(token_address)
    
    @cached_price_endpoint()
    async def get_token_price(self, token_address: str, chain: str = "sonic") -> Dict[str, Any]:
        """
        Get token price with caching (60s refresh)
        
        Args:
            token_address: Token symbol or address
            chain: Chain ID (default: "sonic")
        
        Returns:
            Token price data dictionary 
        """
        logger.debug(f"Fetching fresh token price for {token_address}")
        return await self.market_service.get_token_price(token_address, chain)
    
    # Note: Sonic pairs endpoint is implemented directly in the Express backend
    
    @cached_sentiment_endpoint()
    async def get_market_sentiment(self) -> Dict[str, Any]:
        """
        Get market sentiment data with caching (120s refresh)
        
        Returns:
            Market sentiment data
        """
        logger.debug("Fetching fresh market sentiment")
        return await self.market_service.get_market_sentiment()
    
    # Note: The following methods are placeholders for future implementation
    # They are not available in the current MarketDataService
    # Once implemented, they can be uncommented and used with caching
    
    """
    @cached_news_endpoint()
    async def get_market_news(self, limit: int = 10) -> Dict[str, Any]:
        # Get market news with caching (300s refresh)
        logger.debug(f"Fetching fresh market news (limit={limit})")
        return await self.market_service.get_market_news(limit)
    
    @cached_fear_greed_endpoint()
    async def get_fear_greed_index(self) -> Dict[str, Any]:
        # Get fear and greed index with caching (1800s refresh)
        logger.debug("Fetching fresh fear and greed index")
        return await self.market_service.get_fear_greed_index()
    
    @cached_trending_endpoint()
    async def get_trending_tokens(self, limit: int = 10) -> List[Dict[str, Any]]:
        # Get trending tokens with caching (600s refresh)
        logger.debug(f"Fetching fresh trending tokens (limit={limit})")
        return await self.market_service.get_trending_tokens(limit)
    
    @cached_dex_volume_endpoint()
    async def get_dex_volume(self, dex_name: Optional[str] = None) -> Dict[str, Any]:
        # Get DEX volume data with caching (300s refresh)
        logger.debug(f"Fetching fresh DEX volume data for {dex_name or 'all DEXes'}")
        return await self.market_service.get_dex_volume(dex_name)
    
    @cached_sales_endpoint()
    async def get_nft_sales(self, limit: int = 10) -> List[Dict[str, Any]]:
        # Get NFT sales data with caching (600s refresh)
        logger.debug(f"Fetching fresh NFT sales data (limit={limit})")
        return await self.market_service.get_nft_sales(limit)
    """
    
    # Additional methods can be implemented as needed
    
    @cached_sentiment_endpoint()
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment for text with caching (120s refresh)
        
        Args:
            text: Text to analyze
            
        Returns:
            Sentiment analysis result
        """
        logger.debug(f"Analyzing sentiment for text: {text[:30]}...")
        return await self.market_service.analyze_sentiment(text)

# Create a singleton instance
cached_market_data_service = None

async def get_cached_market_data_service(market_service=None) -> CachedMarketDataService:
    """
    Get or create the cached market data service singleton
    
    Args:
        market_service: Optional market service to use
    
    Returns:
        Cached market data service instance
    """
    global cached_market_data_service
    
    if cached_market_data_service is None:
        if market_service is None:
            from src.services.market_data_service import MarketDataService
            market_service = MarketDataService()
        
        cached_market_data_service = CachedMarketDataService(market_service)
        await cached_market_data_service.initialize()
    
    return cached_market_data_service