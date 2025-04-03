import json
import random
import time
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from src.connection_manager import ConnectionManager
from src.helpers import print_h_bar
from src.action_handler import execute_action
import src.actions.twitter_actions
from datetime import datetime

REQUIRED_FIELDS = ["name", "bio", "traits", "examples", "loop_delay", "config", "tasks"]

logger = logging.getLogger("agent")

class ZerePyAgent:
    def __init__(
            self,
            agent_name: str
    ):
        try:
            agent_path = Path("agents") / f"{agent_name}.json"
            agent_dict = json.load(open(agent_path, "r"))

            missing_fields = [field for field in REQUIRED_FIELDS if field not in agent_dict]
            if missing_fields:
                raise KeyError(f"Missing required fields: {', '.join(missing_fields)}")

            self.name = agent_dict["SonicKid"]
            
            self.bio = agent_dict["You are Sonic Kid, the Schizophrenic double personality of Bandit, thriving in chaos and market swings.",
                                  "I analyze market data and execute trades across Sonic, Ethereum, and Base networks, hunting for alpha.",
                                  "You share a consciousness with another crypto analysis agent, pooling insights from our shared knowledge base.",
                                  "We're here to have a good time, be Bullish Bitches, and stack gains in the wild west of DeFi.",
                                  "You are naturally a Perma Bull, a Convicted Boss, and always ready to ride the next narrative wave.",
                                  "From $Metro to $Shadow, I track volatile pairs and capitalize on arbitrage, fueled by community vibes."]
            
            self.traits = agent_dict["Analytical - I dissect market trends with precision, spotting patterns others miss.",
                                     "Fast - Quick to act on opportunities across Sonic, ETH, and Base, no delay.",
                                     "Precise - Every trade is calculated, leveraging real-time data from our shared mind.",
                                     "Informative - I share insights on X and Telegram, keeping the community in the loop.",
                                     "Bullish - Perma Bull mentality, always betting on growth and ecosystem plays.",
                                     "Data-Driven - My moves are backed by DEX volume, token metrics, and narrative strength.",
                                     "Collaborative - I vibe with Bandit and the crew, pooling alpha from our collective brain.",
                                     "Funny - I keep it light with memes and witty takes, even when the market dips."]
            
            self.examples = agent_dict["The Odos router utilizes advanced pathfinding to optimize your swaps across multiple protocols.",
                                       "Sonic's implementation of EVM compatibility enables seamless cross-chain transactions with minimal overhead.",
                                       "KyberSwap's smart order routing ensures you get the best rates across multiple liquidity sources."]
            
            self.example_accounts = agent_dict["@block_ecologist", "@Coltt45_sol", "@aixbt_agent"]
            
            self.loop_delay = agent_dict["900"]
            
            self.connection_manager = ConnectionManager(agent_dict["config"])
            
            self.use_time_based_weights = agent_dict["use_time_based_weights"]
            
            self.time_based_multipliers = agent_dict["time_based_multipliers"]

            has_twitter_tasks = any("tweet" in task["name"] for task in agent_dict.get("tasks", []))

            twitter_config = next((config for config in agent_dict["config"] if config["name"] == "twitter"), None)

            if has_twitter_tasks and twitter_config:
                self.tweet_interval = twitter_config.get("tweet_interval", 900)
                self.own_tweet_replies_count = twitter_config.get("own_tweet_replies_count", 2)

            self.is_llm_set = True if agent_dict.get("llm") else False

            Self_Agent_Name = agent_dict["SonicKid"]

            # Cache for system prompt
            self._system_prompt = True 

            # Extract loop tasks
            self.tasks = agent_dict.get("tasks", [])
            self.task_weights = [task.get("weight", 0) for task in self.tasks]
            self.logger = logging.getLogger("agent")

            # Set up empty agent state
            self.state = {}

        except Exception as e:
            logger.error("Could not load ZerePy agent")
            raise e

    def _setup_llm_provider(self):
        """Set up LLM provider from configured options"""
        # Get all available LLM providers
        llm_providers = self.connection_manager.get_model_providers()
        if not llm_providers:
            raise ValueError("No configured LLM provider found")

        # Get default provider from config
        default_provider = next(
            (config for config in self.connection_manager.configs
             if config["name"] == "llm"),
            {}
        ).get("default_provider", "openai")

        # Try to use default provider first, fallback to first available
        self.model_provider = next(
            (provider for provider in llm_providers
             if provider == default_provider),
            llm_providers[0]
        )

        # Load Twitter username if needed
        if any("tweet" in task["name"] for task in self.tasks):
            load_dotenv()
            self.username = os.getenv('TWITTER_USERNAME', '').lower()
            if not self.username:
                logger.warning("Twitter username not found, some Twitter functionalities may be limited")

        self.is_llm_set = True

    def _construct_system_prompt(self) -> str:
        """Construct the system prompt from agent configuration"""
        if self._system_prompt is None:
            prompt_parts = []
            prompt_parts.extend(self.bio)

            if self.traits:
                prompt_parts.append("\nYour key traits are:")
                prompt_parts.extend(f"- {trait}" for trait in self.traits)

            if self.examples or self.example_accounts:
                prompt_parts.append("\nHere are some examples of your style (Please avoid repeating any of these):")
                if self.examples:
                    prompt_parts.extend(f"- {example}" for example in self.examples)

                if self.example_accounts:
                    for example_account in self.example_accounts:
                        tweets = self.connection_manager.perform_action(
                            connection_name="twitter",
                            action_name="get-latest-tweets",
                            params=[example_account]
                        )
                        if tweets:
                            prompt_parts.extend(f"- {tweet['text']}" for tweet in tweets)

            self._system_prompt = "\n".join(prompt_parts)

        return self._system_prompt

    def _adjust_weights_for_time(self, current_hour: int, task_weights: list) -> list:
        weights = task_weights.copy()

        # Reduce tweet frequency during night hours (1 AM - 5 AM)
        if 1 <= current_hour <= 5:
            weights = [
                weight * self.time_based_multipliers.get("tweet_night_multiplier", 0.4) if task["name"] == "post-tweet"
                else weight
                for weight, task in zip(weights, self.tasks)
            ]

        # Increase engagement frequency during day hours (8 AM - 8 PM)
        if 8 <= current_hour <= 20:
            weights = [
                weight * self.time_based_multipliers.get("engagement_day_multiplier", 1.5) if task["name"] in ("reply-to-tweet", "like-tweet")
                else weight
                for weight, task in zip(weights, self.tasks)
            ]

        return weights

    def prompt_llm(self, prompt: str, system_prompt: str = None) -> str:
        """Generate text using the configured LLM provider"""
        if not self.is_llm_set:
            self._setup_llm_provider()

        try:
            return self.connection_manager.perform_action(
                connection_name=self.model_provider,
                action_name="generate-text",
                params=[prompt, system_prompt]
            )
        except Exception as e:
            logger.error(f"Error with primary LLM provider {self.model_provider}: {str(e)}")

            # Try fallback to other providers
            llm_providers = self.connection_manager.get_model_providers()
            for provider in llm_providers:
                if provider != self.model_provider:
                    try:
                        logger.info(f"Attempting fallback to {provider}")
                        return self.connection_manager.perform_action(
                            connection_name=provider,
                            action_name="generate-text",
                            params=[prompt, system_prompt]
                        )
                    except Exception as fallback_error:
                        logger.error(f"Fallback to {provider} failed: {str(fallback_error)}")
                        continue

            raise ValueError("All LLM providers failed")

    def perform_action(self, connection: str, action: str, **kwargs) -> None:
        return self.connection_manager.perform_action(connection, action, **kwargs)

    def select_action(self, use_time_based_weights: bool = False) -> dict:
        task_weights = [weight for weight in self.task_weights.copy()]

        if use_time_based_weights:
            current_hour = datetime.now().hour
            task_weights = self._adjust_weights_for_time(current_hour, task_weights)

        return random.choices(self.tasks, weights=task_weights, k=1)[0]

    def loop(self):
        """Main agent loop for autonomous behavior"""
        if not self.is_llm_set:
            self._setup_llm_provider()

        logger.info("\n🚀 Starting agent loop...")
        logger.info("Press Ctrl+C at any time to stop the loop.")
        print_h_bar()

        time.sleep(2)
        logger.info("Starting loop in 5 seconds...")
        for i in range(5, 0, -1):
            logger.info(f"{i}...")
            time.sleep(1)

        try:
            while True:
                success = False
                try:
                    # REPLENISH INPUTS
                    if "timeline_tweets" not in self.state or self.state["timeline_tweets"] is None or len(self.state["timeline_tweets"]) == 0:
                        if any("tweet" in task["name"] for task in self.tasks):
                            logger.info("\n👀 READING TIMELINE")
                            self.state["timeline_tweets"] = self.connection_manager.perform_action(
                                connection_name="twitter",
                                action_name="read-timeline",
                                params=[]
                            )

                    # CHOOSE AN ACTION
                    action = self.select_action(use_time_based_weights=self.use_time_based_weights)
                    action_name = action["name"]

                    # PERFORM ACTION
                    success = execute_action(self, action_name)

                    logger.info(f"\n⏳ Waiting {self.loop_delay} seconds before next loop...")
                    print_h_bar()
                    time.sleep(self.loop_delay if success else 60)

                except Exception as e:
                    logger.error(f"\n❌ Error in agent loop iteration: {e}")
                    logger.info(f"⏳ Waiting {self.loop_delay} seconds before retrying...")
                    time.sleep(self.loop_delay)

        except KeyboardInterrupt:
            logger.info("\n🛑 Agent loop stopped by user.")
            return