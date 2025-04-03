"""Base storage classes and interfaces"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseStorage(ABC):
    """Abstract base class for storage implementations"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Initialize database connection"""
        pass
        
    @abstractmethod
    async def savePriceFeed(self, data: Dict[str, Any]) -> bool:
        """Save price feed data"""
        pass
        
    @abstractmethod
    async def getLatestPrices(self, chain: str) -> List[Dict[str, Any]]:
        """Get latest prices for chain"""
        pass
        
    @abstractmethod
    async def logMarketUpdate(self, data: Dict[str, Any]) -> bool:
        """Log market data update"""
        pass
