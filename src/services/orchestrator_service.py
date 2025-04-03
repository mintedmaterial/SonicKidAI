"""
Orchestrator service for managing multi-agent workflow and knowledge updates
"""
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from src.connections.base_connection import BaseConnection
from src.connections.eternalai_connection import EternalAIConnection
from src.connections.openrouter_connection import OpenRouterConnection
from src.connections.tophat import TopHatConnection
from src.connections.dexscreener_connection import DexScreenerConnection
from src.services.knowledge_formatter import KnowledgeFormatter
from src.services.market_service_fixed import MarketService

logger = logging.getLogger(__name__)

class OrchestratorService:
    """Service for orchestrating multi-agent workflow and knowledge updates"""

    def __init__(self, config: Dict[str, Any]):
        # Initialize connections
        self.eternal_ai = EternalAIConnection(config.get('eternal_ai_config', {}))
        self.openrouter = OpenRouterConnection(config.get('openrouter_config', {}))
        self.tophat = TopHatConnection(config.get('tophat_config', {}))
        self.dexscreener = DexScreenerConnection(config.get('dexscreener_config', {}))

        # Initialize market service
        self.market_service = MarketService(config, None)  # None for equalizer as it's not needed here

        # Initialize knowledge formatter
        self.knowledge_formatter = KnowledgeFormatter()

        self.update_interval = timedelta(hours=2)  # Update knowledge base every 2 hours
        self.last_update = None

        logger.info("Initialized orchestrator service with hooks pattern")

    async def pre_hook_format_data(self, data: Dict[str, Any], data_type: str) -> Optional[str]:
        """Pre-hook: Format data using available LLM providers"""
        try:
            # Try OpenRouter first (primary provider)
            if await self.openrouter.is_configured():
                system_prompt = self._get_system_prompt(data_type)
                formatted_data = await self.openrouter.generate_text(
                    prompt=str(data),
                    system_prompt=system_prompt
                )
                if formatted_data:
                    logger.info("Successfully formatted data using OpenRouter")
                    return formatted_data

            # Fallback to EternalAI if OpenRouter fails
            if await self.eternal_ai.is_configured():
                system_prompt = self._get_system_prompt(data_type)
                formatted_data = await self.eternal_ai.generate_text(
                    prompt=str(data),
                    system_prompt=system_prompt
                )
                if formatted_data:
                    logger.info("Successfully formatted data using EternalAI fallback")
                    return formatted_data

            logger.error("No LLM provider available for formatting")
            return None

        except Exception as e:
            logger.error(f"Error in pre-hook formatting: {str(e)}")
            return None

    async def update_knowledge_base(self) -> bool:
        """Update knowledge base with formatted data using hooks pattern"""
        try:
            # Collect market data
            market_data = await self.collect_market_data()
            if not market_data:
                logger.error("Failed to collect market data")
                return False

            # Pre-hook: Format data using LLM (prioritize OpenRouter)
            formatted_market_data = await self.pre_hook_format_data(market_data, "market_data")
            if not formatted_market_data:
                logger.error("Failed to format market data in pre-hook")
                return False

            # Format market data through market service
            market_update = await self.market_service.update_market_knowledge(market_data)

            # Combine formatted data
            combined_knowledge = f"{formatted_market_data}\n\n{market_update if market_update else ''}"

            # Post-hook: Update TopHat knowledge base
            success = await self.post_hook_update_tophat(combined_knowledge)
            if not success:
                logger.error("Failed to update knowledge base in post-hook")
                return False

            logger.info("Successfully completed knowledge base update workflow")
            return True

        except Exception as e:
            logger.error(f"Error in knowledge base update workflow: {str(e)}")
            return False

    async def run_periodic_updates(self):
        """Run periodic knowledge base updates"""
        while True:
            try:
                current_time = datetime.utcnow()

                # Check if update is needed
                if (not self.last_update or 
                    current_time - self.last_update >= self.update_interval):
                    logger.info("Starting scheduled knowledge base update")
                    await self.update_knowledge_base()

                # Wait for next check (5 minutes)
                await asyncio.sleep(300)

            except Exception as e:
                logger.error(f"Error in periodic update: {str(e)}")
                await asyncio.sleep(300)  # Wait before retrying

    async def collect_market_data(self) -> Optional[Dict[str, Any]]:
        """Collect current market data from various sources"""
        try:
            # Get data from DexScreener
            pairs_data = await self.dexscreener.perform_action(
                "search-pairs",
                {"query": "WBTC"}  # Example query
            )

            if not pairs_data:
                return None

            # Initial data structuring using knowledge formatter
            market_data = self.knowledge_formatter.format_market_data({
                "timestamp": datetime.utcnow().isoformat(),
                "pairs": pairs_data
            })

            return market_data

        except Exception as e:
            logger.error(f"Error collecting market data: {str(e)}")
            return None

    def _get_system_prompt(self, data_type: str) -> str:
        """Get appropriate system prompt based on data type"""
        prompts = {
            "market_data": """
            Format the following crypto market data for a trading agent's knowledge base.
            Follow these guidelines:
            - Structure information clearly with market trends
            - Include key metrics and their significance
            - Highlight notable changes and patterns
            - Maintain accuracy of numerical data
            - Add relevant trading context
            """,
            "trading_signals": """
            Format the following trading signals for a crypto trading agent's knowledge base.
            Follow these guidelines:
            - Clearly state signal type and direction
            - Include relevant timeframes and confidence levels
            - Highlight key indicators and their values
            - Provide context for signal interpretation
            - Note any risk factors or conditions
            """
        }
        return prompts.get(data_type, "Format the following data for the knowledge base.")

    async def post_hook_update_tophat(self, formatted_data: str) -> bool:
        """Post-hook: Update TopHat knowledge base"""
        try:
            if not await self.tophat.is_configured():
                logger.error("TopHat not configured")
                return False

            update_result = await self.tophat.update_knowledge(formatted_data)
            if update_result:
                self.last_update = datetime.utcnow()
                logger.info("Successfully updated TopHat knowledge base")
                return True

            logger.error("Failed to update TopHat knowledge base")
            return False

        except Exception as e:
            logger.error(f"Error in post-hook update: {str(e)}")
            return False