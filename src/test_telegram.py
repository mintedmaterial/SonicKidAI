"""Telegram bot test module with enhanced logging and command testing"""
import logging
import asyncio
import os
from typing import Dict, Any, Optional
try:
    from telegram import Update, Chat, Message, User
    from telegram.ext import Application, CommandHandler, filters, ContextTypes
except ImportError:
    # Define placeholder classes for testing without telegram package
    class Update:
        def __init__(self, update_id, message=None):
            self.update_id = update_id
            self.message = message
            self.effective_message = message
            self.effective_chat = message.chat if message else None

    class Chat:
        def __init__(self, id, type):
            self.id = id
            self.type = type

    class Message:
        def __init__(self, message_id, date, chat, from_user=None, text=None):
            self.message_id = message_id
            self.date = date
            self.chat = chat
            self.from_user = from_user
            self.text = text

    class User:
        def __init__(self, id, is_bot, first_name, last_name=None):
            self.id = id
            self.is_bot = is_bot
            self.first_name = first_name
            self.last_name = last_name
            self.username = first_name.lower()

    class Application:
        pass

    class CommandHandler:
        pass

    class ContextTypes:
        DEFAULT_TYPE = "DEFAULT_TYPE"

    class filters:
        @staticmethod
        def command(*args, **kwargs):
            return None
import sys
sys.path.insert(0, '.')
try:
    from src.connections.telegram import TelegramConnection
    from src.services.market_service import MarketService
    from src.services.equalizer_service import EqualizerService
    from src.connections.openrouter import OpenRouterConnection
except ImportError:
    try:
        from connections.telegram import TelegramConnection
        from services.market_service import MarketService
        from services.equalizer_service import EqualizerService
        from connections.openrouter import OpenRouterConnection
    except ImportError:
        logging.warning("Unable to import required modules, test may fail")
from unittest.mock import MagicMock, AsyncMock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def create_mock_update(text: str, chat_id: int = 123456789) -> Update:
    """Create a mock update with proper chat and message objects"""
    try:
        # Create valid chat object
        chat = Chat(id=chat_id, type='private')
        user = User(id=1234, is_bot=False, first_name='Test', last_name='User')

        # Create message with proper attributes
        message = Message(
            message_id=1,
            date=1234567890,
            chat=chat,
            from_user=user,
            text=text
        )

        # Create update with message
        update = Update(update_id=1, message=message)
        return update
    except Exception as e:
        logger.error(f"Error creating mock update: {str(e)}")
        raise

async def test_bot_initialization(timeout: int = 30):
    """Test bot initialization and connection"""
    try:
        logger.info("\n🤖 Testing bot initialization...")

        # Initialize with complete config
        config = {
            'token': os.getenv('TELEGRAM_BOT_TOKEN', 'test_token'),
            'openrouter': {
                'api_key': os.getenv('OPENROUTER_API_KEY', 'test_key')
            },
            'whale_tracker': AsyncMock(
                analyze_whale_activity=AsyncMock(return_value={
                    'metrics': {
                        'current_price': 50000,
                        'total_volume': 1000000,
                        'unique_whales': 5,
                        'price_impact': 2.5,
                        'market_sentiment': 'bullish'
                    }
                })
            )
        }

        # Create bot instance
        bot = TelegramConnection(config)
        assert bot is not None, "Bot should be initialized"

        # Create mock Application
        mock_application = MagicMock(spec=Application)
        mock_application.bot = MagicMock()
        mock_application.bot.username = "test_bot"
        mock_application.bot.send_message = AsyncMock()
        bot.application = mock_application

        # Test connection with timeout
        async with asyncio.timeout(timeout):
            success = await bot.connect()
            assert success, "Bot should connect successfully"

        logger.info("✅ Bot initialization test passed")
        return bot
    except asyncio.TimeoutError:
        logger.error("❌ Bot initialization test timed out")
        raise
    except Exception as e:
        logger.error(f"❌ Bot initialization test failed: {str(e)}")
        raise

async def test_message_handling(bot: TelegramConnection, timeout: int = 10):
    """Test message handling"""
    try:
        logger.info("\n📝 Testing message handling...")

        async with asyncio.timeout(timeout):
            # Mock context with bot
            context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
            context.bot = bot.application.bot

            # Test message handling
            update = await create_mock_update("Hello bot")
            await bot._handle_message(update, context)
            logger.info("✅ Message handling test completed")

        logger.info("✅ Message handling tests completed")
    except asyncio.TimeoutError:
        logger.error("❌ Message handling test timed out")
        raise
    except Exception as e:
        logger.error(f"❌ Message handling test failed: {str(e)}")
        raise

async def test_rate_limiting(bot: TelegramConnection, timeout: int = 10):
    """Test rate limiting functionality"""
    try:
        logger.info("\n⏱️ Testing rate limiting...")

        async with asyncio.timeout(timeout):
            chat_id = 123456789
            messages = ["Test message 1", "Test message 2", "Test message 3"]

            # Send multiple messages
            for msg in messages:
                await bot._send_message(
                    chat_id=chat_id,
                    text=msg
                )
                logger.info(f"✅ Sent message: {msg}")

        logger.info("✅ Rate limiting test passed")
    except asyncio.TimeoutError:
        logger.error("❌ Rate limiting test timed out")
        raise
    except Exception as e:
        logger.error(f"❌ Rate limiting test failed: {str(e)}")
        raise

async def test_sonic_price_query(bot: TelegramConnection, timeout: int = 10):
    """Test Sonic price query functionality"""
    try:
        logger.info("\n💰 Testing Sonic price query handling...")

        # Create a mock storage with realistic price data
        mock_storage = MagicMock()
        mock_storage.getLatestTokenData = AsyncMock(return_value={
            'symbol': 'SONIC',
            'price': 0.5012,
            'price_change_24h': 2.5,
            'volume_24h': 1250000,
            'liquidity': 800000,
            'tvl': 1026714654,
            'market_cap': 50120000,
            'timestamp': None,
            'source': 'database'
        })
        
        # Add mock storage to bot
        bot.storage_service = mock_storage

        async with asyncio.timeout(timeout):
            # Mock context with bot
            context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
            context.bot = bot.application.bot

            # Test Sonic price handling with different queries
            sonic_queries = [
                "What's the price of SONIC?",
                "sonic price",
                "SONIC/USD",
                "Price of $SONIC"
            ]

            for query in sonic_queries:
                update = await create_mock_update(query)
                await bot._handle_message(update, context)
                logger.info(f"✅ Sonic price query handled: '{query}'")

        logger.info("✅ Sonic price query test completed")
    except asyncio.TimeoutError:
        logger.error("❌ Sonic price query test timed out")
        raise
    except Exception as e:
        logger.error(f"❌ Sonic price query test failed: {str(e)}")
        raise

async def run_tests_with_timeout(total_timeout: int = 60):
    """Run all tests with a total timeout and proper cleanup"""
    bot = None
    try:
        async with asyncio.timeout(total_timeout):
            # Initialize and test bot
            bot = await test_bot_initialization()
            if not bot:
                logger.error("Failed to initialize bot")
                return

            # Run test cases
            await test_message_handling(bot)
            await test_rate_limiting(bot)
            await test_sonic_price_query(bot)

            logger.info("\n✅ All Telegram bot tests completed successfully!")

    except asyncio.TimeoutError:
        logger.error(f"\n❌ Tests timed out after {total_timeout} seconds")
        raise
    except Exception as e:
        logger.error(f"\n❌ Tests failed: {str(e)}")
        raise
    finally:
        if bot:
            await bot.close()

if __name__ == "__main__":
    try:
        # Run tests with timeout
        asyncio.run(run_tests_with_timeout(60))
    except Exception as e:
        logger.error("Test suite failed")
        raise