"""TopHat API Service implementation"""
import logging
import aiohttp
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TopHatService:
    """Service for interacting with TopHat API"""

    def __init__(self, api_key: str):
        """Initialize TopHat service with API key"""
        self.api_key = api_key
        self.base_url = "https://api.tophat.one"
        self.agent_id = "052169af-c09c-4e23-bf41-e92ad30eeb84"
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": self.api_key}
            )
        return self._session

    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def chat(self, message: str) -> Dict[str, Any]:
        """Send a chat message to TopHat API"""
        try:
            session = await self._get_session()
            url = f"{self.base_url}/agent-api/{self.agent_id}/chat"

            payload = {
                "message": message
            }

            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"TopHat API error: {response.status} - {error_text}")
                    return {
                        "error": f"API request failed with status {response.status}",
                        "details": error_text
                    }

        except Exception as e:
            logger.error(f"Error in TopHat chat: {str(e)}")
            return {"error": f"Failed to communicate with TopHat API: {str(e)}"}

    async def update_knowledge(self, knowledge: str) -> Dict[str, Any]:
        """Update the knowledge base of the TopHat agent"""
        try:
            session = await self._get_session()
            url = f"{self.base_url}/agent-api/{self.agent_id}/knowledge"

            payload = {
                "knowledge": knowledge
            }

            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"TopHat API error: {response.status} - {error_text}")
                    return {
                        "error": f"API request failed with status {response.status}",
                        "details": error_text
                    }

        except Exception as e:
            logger.error(f"Error updating knowledge base: {str(e)}")
            return {"error": f"Failed to update knowledge base: {str(e)}"}