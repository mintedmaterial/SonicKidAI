"""
TopHat API connection implementation
"""
import os
import logging
import aiohttp
import json
from typing import Dict, Any, Optional, List
from .base_connection import BaseConnection, Action, Parameter
from src.services.knowledge_formatter import KnowledgeFormatter
from .eternalai_connection import EternalAIConnection

logger = logging.getLogger(__name__)

class TopHatConnection(BaseConnection):
    """TopHat API connection implementation"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize TopHat connection"""
        # Initialize credentials before base class
        self.api_key = config.get('tophat_api_key', os.getenv('TOPHAT_API_KEY'))
        self.agent_id = config.get('agent_id', '052169af-c09c-4e23-bf41-e92ad30eeb84')
        self.base_url = f"https://api.tophat.one/agent-api/{self.agent_id}"

        # Initialize base class
        super().__init__(config)

        self.session = None
        # Using plain API key for authorization as per TopHat docs
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": self.api_key  # Use API key directly without Bearer prefix
        }

        # Initialize knowledge formatter
        self.knowledge_formatter = KnowledgeFormatter()
        logger.info("Initialized knowledge formatter")

        # Initialize EternalAI for additional formatting if configured
        self.eternal_ai = None
        if 'eternal_ai_config' in config:
            try:
                self.eternal_ai = EternalAIConnection(config['eternal_ai_config'])
                logger.info("Initialized EternalAI connection for advanced formatting")
            except Exception as e:
                logger.warning(f"Failed to initialize EternalAI connection: {str(e)}")

        logger.info(f"Initializing TopHat connection for agent ID: {self.agent_id}")
        logger.debug(f"Base URL: {self.base_url}")
        logger.debug(f"Authorization header present: {'Authorization' in self.headers}")

        # Validate configuration
        if not self.api_key:
            raise ValueError("No TopHat API key provided in config or environment")

    async def update_market_knowledge(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update knowledge base with formatted market data"""
        try:
            formatted_knowledge = self.knowledge_formatter.format_market_data(market_data)
            if formatted_knowledge:
                return await self.update_knowledge(formatted_knowledge)
            return None

        except Exception as e:
            logger.error(f"Error updating market knowledge: {str(e)}")
            return None

    async def update_trading_signals(self, signals: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update knowledge base with formatted trading signals"""
        try:
            formatted_signals = self.knowledge_formatter.format_trading_signals(signals)
            if formatted_signals:
                return await self.update_knowledge(formatted_signals)
            return None

        except Exception as e:
            logger.error(f"Error updating trading signals: {str(e)}")
            return None

    async def connect(self) -> bool:
        """Initialize connection"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                logger.info("Created new aiohttp session")

            # Test connection with a simple chat message
            test_response = await self.chat("Test connection")
            success = bool(test_response and test_response.get('status') == 'success')
            if success:
                logger.info("Successfully connected to TopHat API")
            else:
                logger.error(f"Failed to connect to TopHat API. Response: {test_response}")
            return success

        except Exception as e:
            logger.error(f"Error connecting to TopHat: {str(e)}")
            return False

    async def _format_knowledge(self, knowledge: str) -> str:
        """Format knowledge using LLM before updating"""
        try:
            if self.eternal_ai and await self.eternal_ai.is_configured():
                system_prompt = """
                Format the following knowledge for a crypto trading agent's knowledge base.
                - Structure the information clearly
                - Add relevant context if needed
                - Ensure accuracy and clarity
                - Keep key trading-related details
                """
                response = await self.eternal_ai.generate_text(
                    prompt=knowledge,
                    system_prompt=system_prompt
                )
                if response:
                    return response

            logger.warning("EternalAI formatting unavailable, using original knowledge")
            return knowledge

        except Exception as e:
            logger.error(f"Error formatting knowledge: {str(e)}")
            return knowledge

    async def get_knowledge(self) -> Optional[Dict[str, Any]]:
        """Get current knowledge base"""
        try:
            if not self.session:
                await self.connect()

            url = f"{self.base_url}/knowledge"
            logger.debug(f"Making GET request to: {url}")
            logger.debug(f"Headers: {self.headers}")

            async with self.session.get(url, headers=self.headers) as response:
                response_text = await response.text()
                logger.debug(f"Response status: {response.status}, Body: {response_text}")

                if response.status == 200:
                    return json.loads(response_text)
                else:
                    logger.error(f"Error getting knowledge base: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error in get_knowledge: {str(e)}")
            return None

    async def update_knowledge(self, knowledge: str) -> Optional[Dict[str, Any]]:
        """Update knowledge base with LLM formatting"""
        try:
            if not self.session:
                await self.connect()

            # Format knowledge using LLM before updating
            #formatted_knowledge = await self._format_knowledge(knowledge) #This line is commented out because formatting is now handled by the new methods.

            url = f"{self.base_url}/knowledge"
            payload = {"knowledge": knowledge}

            logger.debug(f"Making POST request to: {url}")
            logger.debug(f"Payload: {payload}")
            logger.debug(f"Headers: {self.headers}")

            async with self.session.post(url, headers=self.headers, json=payload) as response:
                response_text = await response.text()
                logger.debug(f"Response status: {response.status}, Body: {response_text}")

                if response.status == 200:
                    logger.info("Successfully updated knowledge base")
                    return json.loads(response_text)
                else:
                    logger.error(f"Error updating knowledge base: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error in update_knowledge: {str(e)}")
            return None

    async def chat(self, message: str) -> Optional[Dict[str, Any]]:
        """Send chat message"""
        try:
            if not self.session:
                await self.connect()

            url = f"{self.base_url}/chat"
            payload = {"message": message}

            logger.debug(f"Making POST request to: {url}")
            logger.debug(f"Payload: {payload}")
            logger.debug(f"Headers: {self.headers}")

            async with self.session.post(url, headers=self.headers, json=payload) as response:
                response_text = await response.text()
                logger.debug(f"Response status: {response.status}, Body: {response_text}")

                if response.status == 200:
                    return json.loads(response_text)
                else:
                    logger.error(f"Error in chat: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            return None

    def register_actions(self) -> None:
        """Register available TopHat actions"""
        self.actions = {
            'get_knowledge': Action(
                name='get_knowledge',
                parameters=[],
                description='Get current knowledge base'
            ),
            'update_knowledge': Action(
                name='update_knowledge',
                parameters=[
                    Parameter(
                        name='knowledge',
                        required=True,
                        type=str,
                        description='New knowledge to add'
                    )
                ],
                description='Update knowledge base'
            ),
            'chat': Action(
                name='chat',
                parameters=[
                    Parameter(
                        name='message',
                        required=True,
                        type=str,
                        description='Message to send'
                    )
                ],
                description='Send chat message'
            ),
            'update_market_knowledge':Action(
                name='update_market_knowledge',
                parameters=[
                    Parameter(
                        name='market_data',
                        required=True,
                        type=Dict[str,Any],
                        description='Market data to update'
                    )
                ],
                description='Update market knowledge'
            ),
            'update_trading_signals':Action(
                name='update_trading_signals',
                parameters=[
                    Parameter(
                        name='signals',
                        required=True,
                        type=Dict[str,Any],
                        description='Trading signals to update'
                    )
                ],
                description='Update trading signals'
            )
        }

    async def is_configured(self, verbose: bool = False) -> bool:
        """Check if the connection is properly configured"""
        if not self.api_key:
            if verbose:
                logger.warning("TopHat API key not found")
            return False
        return True

    async def perform_action(self, action_name: str, params: Dict[str, Any], **kwargs) -> Optional[Any]:
        """Execute an action with the given parameters"""
        if not await self.is_configured():
            logger.error("TopHat API key not configured")
            return None

        if action_name == "get_knowledge":
            return await self.get_knowledge()
        elif action_name == "update_knowledge":
            return await self.update_knowledge(params["knowledge"])
        elif action_name == "chat":
            return await self.chat(params["message"])
        elif action_name == "update_market_knowledge":
            return await self.update_market_knowledge(params["market_data"])
        elif action_name == "update_trading_signals":
            return await self.update_trading_signals(params["signals"])
        else:
            logger.error(f"Unknown action: {action_name}")
            return None

    async def close(self):
        """Close the connection"""
        if self.session:
            await self.session.close()
            self.session = None

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate TopHat connection configuration"""
        if not self.api_key:
            raise ValueError("No TopHat API key provided")
        if not self.agent_id:
            raise ValueError("No TopHat agent ID provided")
        return config