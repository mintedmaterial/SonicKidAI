"""
Agent Activity Service for Dashboard

This service generates and posts regular updates to the Agent Activity dashboard component.
It ensures fresh content every 3-4 hours and never repeats the same information.
"""
import os
import asyncio
import logging
import random
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import aiohttp
import time

# Import OpenOcean service for fallback data
from .openocean_service import OpenOceanService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class AgentActivityService:
    """Service to post regular updates to the dashboard Agent Activity section"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the service with configuration"""
        self.config = config or {}
        self.api_url = self.config.get("api_url", "http://localhost:3000")
        self.openai_api_key = self.config.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")
        self.post_interval = self.config.get("post_interval", random.randint(180, 240)) # 3-4 hours in minutes
        self.market_data_service = None
        self.openocean_service = None  # Will be lazily initialized when needed
        self.post_history = []
        self.running = False
        self.task = None
        
        # Initialize post category weights
        self.post_categories = {
            "market_analysis": 30,  # Market trends and analysis
            "token_spotlight": 20,  # Focus on specific tokens/coins
            "trading_signals": 15,  # Trading signals and opportunities
            "sentiment_analysis": 15,  # Market sentiment analysis
            "nft_trends": 10,        # NFT market updates
            "defi_updates": 10,      # DeFi protocol updates
        }
    
    async def initialize(self) -> bool:
        """Initialize the service and connections"""
        logger.info("Initializing Agent Activity Service...")
        try:
            # Nothing to initialize yet, just validate API connection
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/api/health") as response:
                    if response.status != 200:
                        logger.error(f"API health check failed: {response.status}")
                        return False
                    
                    data = await response.json()
                    logger.info(f"API health check successful: {data}")
                    return True
        except Exception as e:
            logger.error(f"Error initializing Agent Activity Service: {str(e)}")
            return False
    
    async def close(self) -> None:
        """Close all connections and resources"""
        logger.info("Closing Agent Activity Service...")
        if self.running and self.task:
            self.running = False
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        # Close the OpenOcean service if it was initialized
        if self.openocean_service is not None:
            try:
                await self.openocean_service.close()
                logger.info("OpenOcean service closed successfully")
            except Exception as e:
                logger.error(f"Error closing OpenOcean service: {str(e)}")
    
    async def start(self) -> bool:
        """Start the agent activity posting service"""
        if self.running:
            logger.warning("Agent Activity Service is already running")
            return False
        
        logger.info("Starting Agent Activity Service...")
        self.running = True
        self.task = asyncio.create_task(self._posting_loop())
        return True
    
    async def stop(self) -> bool:
        """Stop the agent activity posting service"""
        if not self.running:
            logger.warning("Agent Activity Service is not running")
            return False
        
        logger.info("Stopping Agent Activity Service...")
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        return True
    
    async def _posting_loop(self) -> None:
        """Main posting loop that runs continuously"""
        try:
            logger.info(f"Agent Activity posting loop starting with interval: {self.post_interval} minutes")
            # Create initial post immediately
            await self.create_and_post_activity()
            
            while self.running:
                # Wait for the configured interval with some randomness
                jitter = random.randint(-15, 15)  # Add/subtract up to 15 minutes
                wait_minutes = max(60, self.post_interval + jitter)  # At least 1 hour
                logger.info(f"Next post scheduled in {wait_minutes} minutes")
                
                # Wait in smaller intervals to allow for graceful shutdown
                for _ in range(wait_minutes * 6):  # Check every 10 seconds
                    if not self.running:
                        break
                    await asyncio.sleep(10)
                
                if self.running:
                    await self.create_and_post_activity()
        except asyncio.CancelledError:
            logger.info("Agent Activity posting loop cancelled")
        except Exception as e:
            logger.error(f"Error in posting loop: {str(e)}")
            if self.running:
                logger.info("Restarting posting loop in 5 minutes...")
                await asyncio.sleep(300)
                if self.running:
                    self.task = asyncio.create_task(self._posting_loop())
    
    async def create_and_post_activity(self) -> bool:
        """Create and post a new agent activity update"""
        try:
            logger.info("Creating new agent activity post...")
            
            # 1. Select post category
            category = self._select_post_category()
            logger.info(f"Selected category: {category}")
            
            # 2. Collect market data for context
            market_data = await self._collect_market_data()
            
            # 3. Generate content using selected category and market data
            post_data = await self._generate_post_content(category, market_data)
            if not post_data:
                logger.error("Failed to generate post content")
                return False
            
            # 4. Store post to database
            success = await self._store_dashboard_post(
                post_type=category,
                content=post_data["content"],
                title=post_data["title"],
                metadata=post_data.get("metadata", {})
            )
            
            if success:
                # 5. Update post history to avoid repetition
                self._update_post_history(post_data)
                logger.info("Successfully created and posted agent activity")
                return True
            else:
                logger.error("Failed to store dashboard post")
                return False
        except Exception as e:
            logger.error(f"Error creating agent activity: {str(e)}")
            return False
    
    def _select_post_category(self) -> str:
        """Select a post category with weighted preferences based on importance"""
        # Filter out recently used categories if possible
        recent_categories = set(item["category"] for item in self.post_history[-3:]) if len(self.post_history) >= 3 else set()
        available_categories = {k: v for k, v in self.post_categories.items() if k not in recent_categories}
        
        # If all categories were recently used, use all categories
        if not available_categories:
            available_categories = self.post_categories
        
        # Calculate total weight
        total_weight = sum(available_categories.values())
        
        # Make weighted random selection
        r = random.uniform(0, total_weight)
        running_sum = 0
        
        for category, weight in available_categories.items():
            running_sum += weight
            if r <= running_sum:
                return category
        
        # Fallback to first category (should never reach here)
        return list(available_categories.keys())[0]
    
    async def _collect_market_data(self) -> Dict[str, Any]:
        """Collect market data for post context"""
        market_data = {
            "timestamp": datetime.now().isoformat(),
            "tokens": {},
            "market": {
                "sentiment": "neutral",
                "confidence": 50,
                "trending_topics": []
            }
        }
        
        data_from_api = False
        api_sonic_data = False
        
        try:
            # First attempt to get token data from API
            async with aiohttp.ClientSession() as session:
                # Get SONIC data
                try:
                    async with session.get(f"{self.api_url}/api/market/sonic") as response:
                        if response.status == 200:
                            sonic_data = await response.json()
                            market_data["tokens"]["SONIC"] = sonic_data
                            api_sonic_data = True
                            data_from_api = True
                except Exception as e:
                    logger.error(f"Error fetching SONIC data from API: {str(e)}")
                
                # Get general market sentiment
                try:
                    async with session.get(f"{self.api_url}/api/market/sentiment") as response:
                        if response.status == 200:
                            sentiment_data = await response.json()
                            if sentiment_data:
                                market_data["market"]["sentiment"] = sentiment_data.get("sentiment", "neutral")
                                market_data["market"]["confidence"] = sentiment_data.get("confidence", 50)
                                market_data["market"]["trending_topics"] = sentiment_data.get("trending", [])
                                data_from_api = True
                except Exception as e:
                    logger.error(f"Error fetching sentiment data from API: {str(e)}")
                    
                # Get DEX volume if available
                try:
                    async with session.get(f"{self.api_url}/api/market/dex-volume") as response:
                        if response.status == 200:
                            volume_data = await response.json()
                            if volume_data and "data" in volume_data:
                                market_data["market"]["dex_volume"] = volume_data["data"]
                                data_from_api = True
                except Exception as e:
                    logger.error(f"Error fetching DEX volume data from API: {str(e)}")
        except Exception as e:
            logger.error(f"Error collecting market data from API: {str(e)}")
        
        # If we couldn't get all data from API, try OpenOcean as fallback
        if not data_from_api or not api_sonic_data:
            logger.info("Using OpenOcean as fallback data source")
            try:
                # Initialize OpenOcean service if needed
                if self.openocean_service is None:
                    self.openocean_service = OpenOceanService()
                    await self.openocean_service.connect()
                
                # Get SONIC price data if we don't have it yet
                if not api_sonic_data:
                    try:
                        sonic_price_data = await self.openocean_service.get_sonic_price_data()
                        if sonic_price_data:
                            # Create a simplified token data structure
                            sonic_data = {
                                "symbol": "SONIC",
                                "name": "Sonic",
                                "price": float(sonic_price_data.get("priceUsd", 0)),
                                "priceChange24h": float(sonic_price_data.get("priceChange24h", 0)),
                                "volume24h": float(sonic_price_data.get("volume24h", 0)),
                                "tvl": float(sonic_price_data.get("tvl", 0)),
                                "source": sonic_price_data.get("source", "openocean")
                            }
                            market_data["tokens"]["SONIC"] = sonic_data
                            logger.info(f"✅ Got SONIC data from OpenOcean: ${sonic_data['price']}")
                    except Exception as e:
                        logger.error(f"Error fetching SONIC data from OpenOcean: {str(e)}")
                
                # Get DEX volume data if we don't have it yet
                if "dex_volume" not in market_data["market"]:
                    try:
                        dex_volumes = await self.openocean_service.get_dex_volumes("sonic")
                        if dex_volumes and "dex_volumes" in dex_volumes:
                            volume_sum = sum(dex.get("volume24h", 0) for dex in dex_volumes["dex_volumes"])
                            market_data["market"]["dex_volume"] = {
                                "volume24h": volume_sum,
                                "volumeChange24h": dex_volumes.get("volume_change", 0),
                                "source": "openocean"
                            }
                            logger.info(f"✅ Got DEX volume data from OpenOcean: ${volume_sum:,.2f}")
                    except Exception as e:
                        logger.error(f"Error fetching DEX volume from OpenOcean: {str(e)}")
                
                # Get market data for trending tokens
                if not market_data["market"]["trending_topics"]:
                    try:
                        market_tokens = await self.openocean_service.get_market_data("sonic", 5)
                        trending_topics = []
                        
                        for token in market_tokens:
                            trending_topics.append({
                                "topic": token.get("symbol", "Unknown"),
                                "sentiment": "neutral",
                                "confidence": 50
                            })
                        
                        if trending_topics:
                            market_data["market"]["trending_topics"] = trending_topics
                            logger.info(f"✅ Got trending tokens from OpenOcean: {len(trending_topics)} tokens")
                    except Exception as e:
                        logger.error(f"Error fetching trending tokens from OpenOcean: {str(e)}")
            except Exception as e:
                logger.error(f"Error using OpenOcean fallback: {str(e)}")
        
        return market_data
    
    async def _generate_post_content(self, category: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate content for a post based on category and market data"""
        try:
            # Prepare market context string
            market_context = self._prepare_market_context(market_data)
            
            # Get prompt for specific category
            prompt = self._get_category_prompt(category, market_data)
            
            # Generate content using OpenAI API
            async with aiohttp.ClientSession() as session:
                # First try OpenRouter
                try:
                    headers = {
                        "Content-Type": "application/json"
                    }
                    
                    # Use OpenAI API if key available
                    if self.openai_api_key:
                        headers["Authorization"] = f"Bearer {self.openai_api_key}"
                        payload = {
                            "model": "gpt-3.5-turbo",
                            "messages": [
                                {"role": "system", "content": "You are a crypto market analyst generating insights for a dashboard. Keep responses concise, informative, and data-driven."},
                                {"role": "user", "content": f"Market Context: {market_context}\n\nTask: {prompt}"}
                            ],
                            "temperature": 0.7,
                            "max_tokens": 300
                        }
                        
                        async with session.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload) as response:
                            if response.status == 200:
                                data = await response.json()
                                generated_text = data["choices"][0]["message"]["content"].strip()
                                
                                # Extract title and clean content
                                title = self._extract_title(generated_text, category)
                                content = self._clean_content(generated_text)
                                
                                # Create post data
                                post_data = {
                                    "category": category,
                                    "title": title,
                                    "content": content,
                                    "metadata": {
                                        "source": "openai",
                                        "model": "gpt-3.5-turbo",
                                        "category": category,
                                        "sentiment": market_data["market"]["sentiment"],
                                        "confidence": market_data["market"]["confidence"]
                                    }
                                }
                                
                                return post_data
                except Exception as e:
                    logger.error(f"Error generating content with OpenAI: {str(e)}")
            
            # Fallback to hardcoded post templates if API generation fails
            logger.warning("Using fallback hardcoded post template")
            return self._get_fallback_post(category, market_data)
        except Exception as e:
            logger.error(f"Error generating post content: {str(e)}")
            return None
    
    def _prepare_market_context(self, market_data: Dict[str, Any]) -> str:
        """Prepare market context string for prompt"""
        context_parts = []
        
        # Add SONIC token data if available
        if "SONIC" in market_data.get("tokens", {}):
            sonic = market_data["tokens"]["SONIC"]
            context_parts.append(
                f"SONIC Token: Price ${sonic.get('price', 0):.2f}, "
                f"24h Volume: ${sonic.get('volume24h', 0):,.2f}, "
                f"TVL: ${sonic.get('tvl', 0):,.2f}, "
                f"Price Change 24h: {sonic.get('priceChange24h', 0):.2f}%"
            )
        
        # Add market sentiment
        sentiment = market_data.get("market", {}).get("sentiment", "neutral")
        confidence = market_data.get("market", {}).get("confidence", 50)
        context_parts.append(f"Market Sentiment: {sentiment.capitalize()} (Confidence: {confidence}%)")
        
        # Add DEX volume if available
        dex_volume = market_data.get("market", {}).get("dex_volume", {})
        if dex_volume:
            volume = dex_volume.get("volume24h", 0)
            change = dex_volume.get("volumeChange24h", 0)
            context_parts.append(f"DEX 24h Volume: ${volume:,.2f} ({change:.2f}% change)")
        
        # Add trending topics if available
        trending = market_data.get("market", {}).get("trending_topics", [])
        if trending:
            topics = ", ".join([t.get("topic", "") for t in trending[:3]])
            context_parts.append(f"Trending Topics: {topics}")
        
        # Join all parts
        return "\n".join(context_parts)
    
    def _get_category_prompt(self, category: str, market_data: Dict[str, Any]) -> str:
        """Get prompt template for specific category"""
        prompts = {
            "market_analysis": (
                "Generate a concise market analysis for the Sonic ecosystem. "
                "Include insights on price movements, trading volume, and overall market conditions. "
                "Keep it under 100 words."
            ),
            "token_spotlight": (
                "Create a brief spotlight on SONIC token's recent performance. "
                "Highlight key metrics and noteworthy changes. "
                "Keep it under 100 words."
            ),
            "trading_signals": (
                "Identify a potential trading opportunity or signal based on current market conditions. "
                "Be specific but avoid overly prescriptive language. "
                "Include factors that support this signal. "
                "Keep it under 100 words."
            ),
            "sentiment_analysis": (
                "Analyze the current market sentiment for the Sonic ecosystem. "
                "How are investors feeling? What's driving the sentiment? "
                "Keep it under 100 words."
            ),
            "nft_trends": (
                "Generate insights about the latest NFT trends in the crypto space. "
                "Include popular collections, trade volumes, or unique developments. "
                "Keep it under 100 words."
            ),
            "defi_updates": (
                "Provide updates on DeFi protocols in the Sonic ecosystem. "
                "Include TVL changes, yield opportunities, or protocol developments. "
                "Keep it under 100 words."
            )
        }
        
        return prompts.get(category, prompts["market_analysis"])
    
    def _category_to_title(self, category: str) -> str:
        """Convert category to default title"""
        titles = {
            "market_analysis": "Market Analysis Update",
            "token_spotlight": "SONIC Token Spotlight",
            "trading_signals": "Trading Signal Alert",
            "sentiment_analysis": "Market Sentiment Report",
            "nft_trends": "NFT Market Trends",
            "defi_updates": "DeFi Ecosystem Update"
        }
        
        return titles.get(category, "Agent Update")
    
    def _extract_title(self, text: str, category: str) -> str:
        """Extract title from generated text or create default"""
        # Check if text starts with a title on the first line
        lines = text.strip().split('\n')
        if len(lines) > 1 and len(lines[0]) < 80 and not lines[0].endswith('.'):
            return lines[0].strip()
        
        # Return default title based on category
        return self._category_to_title(category)
    
    def _clean_content(self, text: str) -> str:
        """Clean up generated content"""
        # Remove title line if it exists
        lines = text.strip().split('\n')
        if len(lines) > 1 and len(lines[0]) < 80 and not lines[0].endswith('.'):
            content = '\n'.join(lines[1:]).strip()
        else:
            content = text.strip()
        
        # Remove quotes if present
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1].strip()
        
        return content
    
    def _update_post_history(self, post: Dict[str, Any]) -> None:
        """Update post history for avoiding repetition"""
        # Add to history
        self.post_history.append({
            "category": post["category"],
            "title": post["title"],
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only the last 10 posts in history
        if len(self.post_history) > 10:
            self.post_history = self.post_history[-10:]
    
    async def _store_dashboard_post(self, post_type: str, content: str, title: str = None, source_id: str = None, metadata: Dict[str, Any] = None) -> bool:
        """Store post in dashboard_posts table"""
        try:
            # Create post data
            post_data = {
                "type": post_type,
                "content": content,
                "title": title,
                "sourceId": source_id,
                "metadata": metadata or {}
            }
            
            # Make API call to store post
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_url}/api/dashboard/posts", json=post_data) as response:
                    if response.status == 201:
                        result = await response.json()
                        logger.info(f"Successfully stored dashboard post with ID: {result.get('id')}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Error storing dashboard post: API returned {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error storing dashboard post: {str(e)}")
            return False
    
    def _get_fallback_post(self, category: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get fallback post data when API generation fails"""
        # Get default title for category
        title = self._category_to_title(category)
        
        # Get sentiment from market data
        sentiment = market_data.get("market", {}).get("sentiment", "neutral")
        confidence = market_data.get("market", {}).get("confidence", 50)
        
        # Get price and volume if available
        price = market_data.get("tokens", {}).get("SONIC", {}).get("price", 0.45)
        volume = market_data.get("tokens", {}).get("SONIC", {}).get("volume24h", 750000)
        price_change = market_data.get("tokens", {}).get("SONIC", {}).get("priceChange24h", 0)
        
        # Create fallback content based on category
        content_templates = {
            "market_analysis": f"SONIC currently trading at ${price:.2f} with {'positive' if price_change > 0 else 'negative' if price_change < 0 else 'neutral'} momentum. Trading volume at ${volume:,.2f} over the past 24 hours. Market sentiment remains {sentiment} with continued interest from traders.",
            "token_spotlight": f"SONIC Token showing {'strength' if price_change > 0 else 'weakness' if price_change < 0 else 'stability'} at ${price:.2f}. 24-hour volume holding at ${volume:,.2f} with {abs(price_change):.2f}% {'gain' if price_change > 0 else 'loss' if price_change < 0 else 'change'} since yesterday.",
            "trading_signals": f"{'Potential buying opportunity' if sentiment == 'bullish' else 'Potential selling pressure' if sentiment == 'bearish' else 'Market consolidation'} for SONIC at ${price:.2f}. {'Watch support levels carefully' if price_change < 0 else 'Resistance at $' + str(price + price * 0.05)} with volume indicators {'strengthening' if volume > 800000 else 'weakening'}.",
            "sentiment_analysis": f"Market sentiment analysis: {sentiment.capitalize()} with {confidence}% confidence. {'Increasing bullish momentum' if sentiment == 'bullish' else 'Bearish pressure mounting' if sentiment == 'bearish' else 'Mixed signals with neutral bias'}. Social mentions {'up' if confidence > 60 else 'down'} compared to previous week.",
            "nft_trends": "NFT market showing signs of renewed interest with collectible sales increasing 15% week-over-week. Profile picture projects remain popular while utility-focused NFTs gain momentum in the Sonic ecosystem.",
            "defi_updates": f"DeFi protocols in the Sonic ecosystem maintain stable TVL despite market fluctuations. Yield farming opportunities averaging 8-12% APY with liquidity mining programs attracting new users. Trading volume at ${volume:,.2f} over the past 24 hours."
        }
        
        content = content_templates.get(category, content_templates["market_analysis"])
        
        # Create post data
        post_data = {
            "category": category,
            "title": title,
            "content": content,
            "metadata": {
                "source": "fallback",
                "category": category,
                "sentiment": sentiment,
                "confidence": confidence
            }
        }
        
        return post_data
    
    async def force_post(self, category: str = None) -> bool:
        """Force creation of a new post immediately"""
        selected_category = category or self._select_post_category()
        market_data = await self._collect_market_data()
        return await self.create_and_post_activity()

# Singleton instance
_service_instance = None

async def get_agent_activity_service(config: Dict[str, Any] = None) -> AgentActivityService:
    """Get or create the agent activity service singleton"""
    global _service_instance
    if _service_instance is None:
        _service_instance = AgentActivityService(config)
        await _service_instance.initialize()
    return _service_instance