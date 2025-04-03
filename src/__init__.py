"""
ZerePy - Cross-blockchain Trading Agent
"""
from pathlib import Path
import sys
import os
import logging

# Add the project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import necessary modules
from .connections.kyberswap_connection import KyberSwapAggregator
from .connections.sonic_wallet import SonicWalletConnection
from .connections.errors import SonicConnectionError
from src.utils.ai_processor import AIProcessor
from src.connections.trading import TradingConnection
from src.connections.webbrowser_connection import WebBrowserConnection


# Initialize Anthropic as the primary AI service through OpenRouter
openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
if openrouter_api_key:
    ai_processor = AIProcessor({
        'api_key': openrouter_api_key,
        'model': 'claude-3-5-sonnet-20241022'  # Use latest model
    })
else:
    logging.warning("OPENROUTER_API_KEY not found. AI processing capabilities will be limited.")
    ai_processor = None

# Import initializers to automatically start background services
try:
    import src.initializers
    logging.info("✅ Background services initialized")
except ImportError as e:
    logging.warning(f"Failed to initialize background services: {str(e)}")

__all__ = [
    'KyberSwapAggregator',
    'SonicWalletConnection',
    'SonicConnectionError',
    'AIProcessor',
    'TradingConnection',
    'WebBrowserConnection',
    'ai_processor'
]