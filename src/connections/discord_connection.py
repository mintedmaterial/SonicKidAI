"""Discord connection for handling API interactions"""
import os
import logging
import aiohttp
from typing import Dict, Any
from src.connections.openrouter_connection import OpenRouterConnection
from src.utils.prompts import SYSTEM_PROMPTS

logger = logging.getLogger(__name__)

class DiscordConnection:
    """Handles Discord API interactions"""
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Discord connection"""
        try:
            # Store raw token without any formatting
            self.token = config.get('token')
            if not self.token:
                raise ValueError("No Discord token provided")

            logger.info("✅ Discord token loaded")

            # Initialize OpenRouter for AI responses
            self.ai_processor = OpenRouterConnection({
                'api_key': config.get('openrouter_api_key'),
                'model': 'anthropic/claude-3-sonnet'
            })
            logger.info("✅ Initialized Discord connection with OpenRouter AI")

        except Exception as e:
            logger.error(f"Error initializing Discord connection: {str(e)}")
            raise

    async def test_token(self) -> bool:
        """Test if the token is valid by making a test API call"""
        try:
            url = "https://discord.com/api/v10/users/@me"
            headers = {
                "Authorization": f"Bot {self.token}",
                "Accept": "application/json"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        bot_info = await response.json()
                        logger.info(f"✅ Discord token verified - Bot username: {bot_info.get('username')}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Token validation failed: {response.status} - {error_text}")
                        return False

        except Exception as e:
            logger.error(f"❌ Error testing token: {str(e)}")
            return False

    async def validate_channel_access(self, channel_id: str) -> bool:
        """Validate bot's access to the specified channel"""
        try:
            url = f"https://discord.com/api/v10/channels/{channel_id}"
            headers = {
                "Authorization": f"Bot {self.token}",
                "Accept": "application/json"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        logger.info(f"✅ Channel {channel_id} access validated")
                        return True
                    else:
                        logger.error(f"❌ Failed to validate channel access: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"❌ Channel validation error: {str(e)}")
            return False

    async def post_message(self, channel_id: str, message: str, **kwargs) -> Dict[str, Any]:
        """Send message with optional AI-generated content"""
        try:
            # Send message to Discord
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            headers = {
                "Authorization": f"Bot {self.token}",
                "Content-Type": "application/json"
            }
            payload = {"content": message}

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info("✅ Message sent successfully")
                        return {
                            "id": result.get("id"),
                            "content": result.get("content"),
                            "channel_id": result.get("channel_id"),
                            "timestamp": result.get("timestamp")
                        }
                    else:
                        error_text = await response.text()
                        raise ValueError(f"Failed to send message: {response.status} - {error_text}")

        except Exception as e:
            logger.error(f"❌ Error sending message: {str(e)}")
            raise