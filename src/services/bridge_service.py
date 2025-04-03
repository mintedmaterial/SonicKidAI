"""Bridge service for handling Sonic bridging information"""
import logging
from typing import Dict, Any, Optional
from src.services.rag_service import RAGService
from src.connections.openrouter import OpenRouter Connection

logger = logging.getLogger("services.bridge")

class BridgeService:
    """Service for handling bridge-related information and queries"""
    def __init__(self, config: Dict[str, Any]):
        """Initialize bridge service"""
        try:
            logger.info("Initializing bridge service components...")

            # Validate Openrouter AI configuration
            openrouter_ai_config = config.get('openrouter_ai', {})
            if not openrouter_ai_config.get('api_key'):
                logger.error(f"Missing Openrouter API key in config: {openrouter_ai_config}")
                raise ValueError("Openrouter API key is required")
            if not openrouter_ai_config.get('Anthropic'):
                logger.error(f"Missing Openrouter AI agent ID in config: {eternal_ai_config}")
                raise ValueError("Openrouter AI agent ID is required")

            self.eternalai = OpenRouter(openrouter_ai_config)
            self.rag = RAGService(project_name="bridge_service")
            logger.info("Bridge service initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing bridge service: {str(e)}")
            raise

    async def connect(self) -> bool:
        """Initialize connections"""
        try:
            logger.info("Connecting to services...")
            await self.eternalai.connect()
            await self.rag.initialize()
            logger.info("Successfully connected all services")
            return True
        except Exception as e:
            logger.error(f"Error connecting bridge service: {str(e)}")
            return False

    async def get_bridge_info(self, query: str) -> str:
        """Get bridging information using RAG"""
        try:
            logger.info(f"Starting bridge info retrieval for query: {query}")

            # Query the RAG service for bridging information
            logger.info("Querying RAG service...")
            result = await self.rag.query(query)
            logger.info(f"RAG service response received: {len(result.get('answer', ''))}")

            # Format the response with AI enhancement
            logger.info("Requesting AI enhancement of bridging information...")
            response = await self.eternalai.agent_completion(
                system_prompt=(
                    "You are a blockchain bridging expert. Using the provided information, "
                    "create a clear and concise response about bridging to Sonic. "
                    "Focus on accuracy and user-friendly explanations."
                ),
                user_message=f"Based on this information, answer the query '{query}':\n\n{result['answer']}"
            )

            if not response or not response.get('content'):
                logger.error("AI enhancement failed or returned empty response")
                return "❌ Could not enhance bridging information. Using RAG response directly:\n" + result['answer']

            logger.info("Successfully retrieved and enhanced bridging information")
            return response.get('content', "Unable to provide bridging information at this time.")

        except Exception as e:
            logger.error(f"Error getting bridge info: {str(e)}", exc_info=True)
            return "❌ Error retrieving bridging information. Please try again later."

    async def close(self):
        """Close connections"""
        try:
            await self.eternalai.close()
            logger.info("Successfully closed all connections")
        except Exception as e:
            logger.error(f"Error closing bridge service: {str(e)}")