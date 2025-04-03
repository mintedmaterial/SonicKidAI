"""
Telegram data request handlers
"""
from .trending import handle_trending_command
from .news import handle_news_command
from .market import handle_market_query, handle_token_lookup
from .whale import handle_whale_command, handle_whale_transaction