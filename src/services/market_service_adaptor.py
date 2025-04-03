"""Market service adaptor for backward compatibility"""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class MarketServiceAdaptor:
    """Adaptor class to maintain compatibility during migration"""
    
    def __init__(self, v2_service):
        """Initialize with v2 service instance"""
        self.v2 = v2_service
        logger.info("Initialized market service adaptor")
        
    async def get_token_price(self, address: str) -> float:
        """Forward token price requests to v2 service"""
        return await self.v2.get_token_price(address)
        
    async def analyze_market_sentiment(self, text: str) -> Dict[str, Any]:
        """Forward sentiment analysis requests to v2 service"""
        return await self.v2.analyze_market_sentiment({'text': text})
        
    async def get_token_info(self, query: str) -> str:
        """Forward token info requests to v2 service"""
        return await self.v2.get_token_info(query)
        
    async def get_latest_news(self, force_refresh: bool = False) -> str:
        """Forward news requests to v2 service"""
        return await self.v2.get_latest_news(force_refresh)
        
    async def get_market_sentiment(self) -> str:
        """Forward market sentiment requests to v2 service"""
        return await self.v2.get_market_sentiment()
