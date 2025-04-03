"""
Utility functions for formatting data in consistent ways
"""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

def format_number(value: Any) -> str:
    """Format number with proper decimal places"""
    try:
        if isinstance(value, (int, float)):
            return f"{value:,.2f}"
        return str(value)
    except:
        return 'N/A'

def format_percentage(value: Any) -> str:
    """Format percentage with proper decimal places"""
    try:
        if isinstance(value, (int, float)):
            return f"{value:,.2f}%"
        return str(value)
    except:
        return 'N/A'

def format_currency(value: Any, currency: str = "$") -> str:
    """Format currency with proper decimal places"""
    try:
        if isinstance(value, (int, float)):
            return f"{currency}{value:,.2f}"
        return str(value)
    except:
        return 'N/A'

def format_market_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Format market data with consistent number formatting"""
    try:
        formatted = {}
        for key, value in data.items():
            if key in ['price', 'lastPrice', 'openPrice', 'closePrice']:
                formatted[key] = format_currency(value)
            elif key in ['priceChange', 'priceChangePercent', 'volume24hChange']:
                formatted[key] = format_percentage(value)
            elif key in ['volume', 'volume24h', 'marketCap']:
                formatted[key] = format_number(value)
            else:
                formatted[key] = str(value)
        return formatted
    except Exception as e:
        logger.error(f"Error formatting market data: {str(e)}")
        return data