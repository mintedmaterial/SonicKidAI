"""SonicKid Agent Implementation"""
import logging
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import random
import time
from src.connection_manager import ConnectionManager
from src.services.rag_service import RAGService

logger = logging.getLogger("agent")

REQUIRED_FIELDS = ["name", "bio", "traits", "examples", "loop_delay", "config"]

class ZerePyAgent:
    def __init__(self, agent_name: str):
        """Initialize agent from configuration file"""
        try:
            agent_path = Path("agents") / f"{agent_name}.json"
            agent_dict = json.load(open(agent_path, "r"))

            missing_fields = [field for field in REQUIRED_FIELDS if field not in agent_dict]
            if missing_fields:
                raise KeyError(f"Missing required fields: {', '.join(missing_fields)}")

            self.name = agent_dict["name"]
            self.bio = agent_dict["bio"]
            self.traits = agent_dict["traits"]
            self.examples = agent_dict["examples"]
            self.loop_delay = agent_dict["loop_delay"]
            self.connection_manager = ConnectionManager(agent_dict["config"])

            # Initialize provider variables
            self.model_provider = None
            self.is_llm_set = False
            self._system_prompt = None

            # Initialize RAG service
            self.rag_service = RAGService()
            self.is_rag_initialized = False

            # Set up empty agent state
            self.state = {}
            logger.info(f"Successfully initialized agent: {self.name}")

        except Exception as e:
            logger.error("Could not load ZerePy agent")
            raise e

    async def _setup_rag_service(self):
        """Set up RAG service for accessing stored documentation"""
        if not self.is_rag_initialized:
            try:
                await self.rag_service.initialize()
                self.is_rag_initialized = True
                logger.info("✅ Initialized RAG service")
            except Exception as e:
                logger.error(f"❌ Error initializing RAG service: {str(e)}")
                raise e

    async def _setup_llm_provider(self):
        """Set up LLM provider from configured connections"""
        try:
            # Get all available LLM providers
            llm_providers = await self.connection_manager.get_model_providers()
            if not llm_providers:
                # Try to configure default provider if available
                for name, conn in self.connection_manager.connections.items():
                    if conn.is_llm_provider:
                        logger.info(f"Attempting to configure {name} provider...")
                        await self.connection_manager.configure_connection(name)

            # Check providers again after configuration attempts
            llm_providers = await self.connection_manager.get_model_providers()
            if not llm_providers:
                raise ValueError("No configured LLM provider found")

            # Select the default provider if specified
            for config in self.connection_manager.configs:
                if config.get("default_provider") and config["name"] in llm_providers:
                    self.model_provider = config["name"]
                    break

            # Fallback to first available if no default
            if not self.model_provider:
                self.model_provider = llm_providers[0]

            self.is_llm_set = True
            logger.info(f"Using LLM provider: {self.model_provider}")
        except Exception as e:
            logger.error(f"Failed to setup LLM provider: {str(e)}")
            raise

    async def get_relevant_documentation(self, query: str, router: Optional[str] = None, limit: int = 3) -> List[Dict[str, Any]]:
        """Get relevant documentation based on a query"""
        if not self.is_rag_initialized:
            await self._setup_rag_service()

        filters = {"doc_type": "documentation"}
        if router:
            filters["router"] = router

        try:
            docs = await self.rag_service.search_all_content(query, filters=filters, limit=limit)
            return docs
        except Exception as e:
            logger.error(f"Error retrieving documentation: {str(e)}")
            return []

    async def get_relevant_tweets(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Get relevant tweets based on a query"""
        if not self.is_rag_initialized:
            await self._setup_rag_service()

        try:
            tweets = await self.rag_service.search_all_content(
                query, 
                filters={"source": "Discord"}, 
                limit=limit
            )
            return tweets
        except Exception as e:
            logger.error(f"Error retrieving tweets: {str(e)}")
            return []

    def _construct_system_prompt(self) -> str:
        """Construct the system prompt from agent configuration"""
        if self._system_prompt is None:
            prompt_parts = []
            prompt_parts.extend(self.bio)

            if self.traits:
                prompt_parts.append("\nYour key traits are:")
                prompt_parts.extend(f"- {trait}" for trait in self.traits)

            if self.examples:
                prompt_parts.append("\nHere are some examples of your style:")
                prompt_parts.extend(f"- {example}" for example in self.examples)

            self._system_prompt = "\n".join(prompt_parts)

        return self._system_prompt

    async def prompt_llm(self, prompt: str, system_prompt: str = None, include_context: bool = True) -> str:
        """Generate text using the configured LLM provider with optional context from documentation"""
        if not self.is_llm_set:
            await self._setup_llm_provider()

        try:
            # If context is requested, fetch relevant documentation and tweets
            if include_context:
                context_parts = []

                # Get relevant documentation
                docs = await self.get_relevant_documentation(prompt)
                if docs:
                    context_parts.append("\nRelevant documentation:")
                    for doc in docs:
                        context_parts.append(f"- {doc['content'][:200]}...")

                # Get relevant tweets
                tweets = await self.get_relevant_tweets(prompt)
                if tweets:
                    context_parts.append("\nRelevant tweets:")
                    for tweet in tweets:
                        context_parts.append(f"- {tweet['content']}")

                if context_parts:
                    prompt = "\n".join([
                        "Here is some relevant context:",
                        *context_parts,
                        "\nUsing this context, please respond to:",
                        prompt
                    ])

            system_prompt = system_prompt or self._construct_system_prompt()

            return await self.connection_manager.perform_action(
                connection_name=self.model_provider,
                action_name="generate-text",
                params={"prompt": prompt, "system_prompt": system_prompt}
            )
        except Exception as e:
            logger.error(f"Error with primary LLM provider {self.model_provider}: {str(e)}")

            # Try fallback to other providers
            llm_providers = await self.connection_manager.get_model_providers()
            for provider in llm_providers:
                if provider != self.model_provider:
                    try:
                        logger.info(f"Attempting fallback to {provider}")
                        return await self.connection_manager.perform_action(
                            connection_name=provider,
                            action_name="generate-text",
                            params={"prompt": prompt, "system_prompt": system_prompt}
                        )
                    except Exception as fallback_error:
                        logger.error(f"Fallback to {provider} failed: {str(fallback_error)}")
                        continue

            raise ValueError("All LLM providers failed")

    async def perform_action(self, connection: str, action: str, params: Dict[str, Any]) -> Optional[Any]:
        """Execute an action through the connection manager"""
        return await self.connection_manager.perform_action(
            connection_name=connection,
            action_name=action,
            params=params
        )