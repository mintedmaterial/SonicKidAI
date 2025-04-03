"""Shared schema definitions for Python services"""
from typing import TypedDict, Optional
from datetime import datetime

class PriceFeedData(TypedDict):
    symbol: str
    price: float
    source: str
    volume24h: float
    priceChange24h: float
    timestamp: datetime
    metadata: dict

class MarketSentiment(TypedDict):
    source: str
    sentiment: str
    score: float
    content: str
    timestamp: datetime
    metadata: dict

class TwitterData(TypedDict):
    tweetId: str
    content: str
    author: str
    sentiment: str
    category: str
    metadata: dict
    createdAt: datetime

class WhaleKlineData(TypedDict):
    walletAddress: str
    timestamp: datetime
    openPrice: float
    closePrice: float
    highPrice: float
    lowPrice: float
    volume: float
    quoteVolume: float
    isLoading: bool

class WhaleAlerts(TypedDict):
    walletAddress: str
    timestamp: datetime
    movementType: str
    priceChange: float
    volumeChange: float
    volatility: float
    sentiment: str
    confidence: float
    details: dict

# Export schema types
__all__ = [
    'PriceFeedData',
    'MarketSentiment', 
    'TwitterData',
    'WhaleKlineData',
    'WhaleAlerts'
]

# Aliases for backward compatibility with existing imports
priceFeedData = PriceFeedData
marketSentiment = MarketSentiment
whaleKlineData = WhaleKlineData
tradingActivity = dict  # Placeholder for now
sonicPriceFeed = dict  # Placeholder for now