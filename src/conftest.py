"""Pytest configuration file for test discovery and shared fixtures"""
import pytest
import logging
from unittest.mock import MagicMock

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture
def mock_agent():
    """Create a mock agent with required services"""
    agent = MagicMock()
    agent.market_service = MagicMock()
    agent.equalizer = MagicMock()
    return agent

@pytest.fixture
def mock_services():
    """Create mock services for testing"""
    return {
        'dex_service': MagicMock(),
        'crypto_panic': MagicMock(),
        'huggingface': MagicMock(),
        'market_service': MagicMock(),
        'get_llm_response': MagicMock(return_value="Mock LLM analysis response")
    }
