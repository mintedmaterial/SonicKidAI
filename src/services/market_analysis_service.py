"""Market analysis service with multi-agent workflow"""
import logging
from typing import Dict, Any, Optional
from src.services.market_service import MarketService
from src.services.market_visualization_service import MarketVisualizationService
from src.services.defillama_service import DeFiLlamaService
from src.utils.ai_processor import AIProcessor
import time

logger = logging.getLogger(__name__)

# Shared AI model configuration
DEFAULT_AI_CONFIG = {
    'model': 'anthropic/claude-3-sonnet',  # Latest stable model
    'base_url': 'https://openrouter.ai/api/v1',
    'headers': {
        'HTTP-Referer': 'https://github.com/ZerePy/sonic-kid',
        'X-Title': 'Sonic Kid Agent'
    }
}

SONICBOT_SYSTEM_PROMPT = """You are Sonic Kid, DeFi's Mad King - a high-energy, street-smart crypto analyst.
Keep your analysis concise and energetic:
1. Break down the numbers with attitude
2. Focus on key trends and moves
3. Highlight potential risks and opportunities
4. End with a clear, actionable insight
Keep it under 300 tokens and maintain your high-energy personality."""

class MarketAnalysisDirector:
    """Director agent for coordinating market analysis"""

    def __init__(self, ai_processor: AIProcessor):
        """Initialize with AI processor using shared config"""
        self.ai_processor = AIProcessor(config={
            **DEFAULT_AI_CONFIG,
            'api_key': ai_processor.client.api_key
        })

    async def process_query(self, query: str) -> Optional[Dict[str, Any]]:
        """Process market analysis query with fallback defaults"""
        try:
            # Default parameters if AI processing fails
            default_params = {
                "token": "SONIC",
                "timeframe": "24h",
                "visualization": True,
                "data_source": "market"  # New parameter for data source
            }

            try:
                prompt = f"""Yo! Sonic Kid here! Let's break down this market request and get what we need.

                Query to analyze: {query}

                Return ONLY a JSON object with:
                {{
                    "token": "token symbol in uppercase",
                    "timeframe": "24h|week|month",
                    "visualization": "boolean - show me the charts",
                    "data_source": "market|defillama"
                }}"""

                response = await self.ai_processor.generate_response(query=prompt)

                if isinstance(response, dict) and "error" not in response:
                    return {
                        "token": response.get("token", default_params["token"]),
                        "timeframe": response.get("timeframe", default_params["timeframe"]),
                        "visualization": response.get("visualization", default_params["visualization"]),
                        "data_source": response.get("data_source", default_params["data_source"])
                    }
                else:
                    logger.warning(f"AI processing returned unexpected format, using defaults")
                    return default_params

            except Exception as e:
                logger.warning(f"AI processing error, using defaults: {str(e)}")
                return default_params

        except Exception as e:
            logger.error(f"Error processing market query: {str(e)}")
            return None

class MarketAnalysisWorker:
    """Worker agent for fetching and analyzing market data"""

    def __init__(self, api_key: str):
        """Initialize with market and visualization services"""
        self.market_service = MarketService(
            {"api_key": api_key}, 
            equalizer=None, 
            openrouter=None, 
            db_pool=None
        )
        self.defillama_service = DeFiLlamaService()
        self.visualization = MarketVisualizationService()

    async def fetch_market_data(self, token: str, timeframe: str, data_source: str = "market", generate_chart: bool = True) -> Dict[str, Any]:
        """Fetch market data and generate visualization"""
        try:
            market_data = {}

            # Get market data based on source
            if data_source == "defillama":
                market_data = await self.defillama_service.get_token_data(token)
                if "error" in market_data:
                    logger.warning(f"DeFiLlama data fetch failed, falling back to market service")
                    market_data = await self.market_service.get_token_info(token)
            else:
                market_data = await self.market_service.get_token_info(token)

            if "error" in market_data:
                return market_data

            # Generate chart if requested
            if generate_chart:
                chart_data = await self.visualization.generate_chart(market_data)
                if chart_data:
                    market_data["chart"] = chart_data

                    # Enhance chart with technical indicators
                    enhanced_chart = await self.visualization.enhance_chart(
                        chart_data,
                        f"Market analysis for {token} over {timeframe}"
                    )
                    if enhanced_chart:
                        market_data["enhanced_chart"] = enhanced_chart

            return market_data

        except Exception as e:
            logger.error(f"Error fetching market data: {str(e)}")
            return {"error": f"Failed to fetch market data: {str(e)}"}

class MarketAnalysisService:
    """Main service coordinating market analysis agents"""

    def __init__(self, ai_processor: AIProcessor):
        """Initialize service with shared model configuration"""
        config = {
            **DEFAULT_AI_CONFIG,
            'api_key': ai_processor.client.api_key
        }
        # Create new instances with consistent config
        self.director = MarketAnalysisDirector(AIProcessor(config=config))
        self.worker = MarketAnalysisWorker(api_key=ai_processor.client.api_key)
        self.ai_processor = AIProcessor(config=config)  # For market analysis

    async def analyze_market(self, query: str) -> Dict[str, Any]:
        """Analyze market based on query"""
        try:
            # 1. Process query parameters
            command_info = await self.director.process_query(query)
            if not command_info:
                return {"error": "Could not process market query"}

            # 2. Fetch data and generate visualization
            market_data = await self.worker.fetch_market_data(
                command_info["token"],
                command_info["timeframe"],
                command_info.get("data_source", "market"),
                command_info["visualization"]
            )
            if "error" in market_data:
                return market_data

            # 3. Generate analysis using AI with SonicKid personality
            prompt = f"""Yo! Sonic Kid here! Let's break down these market moves:

            Token: {command_info['token']}
            Price: ${market_data.get('price', 0):,.2f}
            24h Change: {market_data.get('change_24h', 0):+.2f}%
            Volume: ${market_data.get('volume_24h', 0):,.2f}
            Liquidity: ${market_data.get('liquidity', 0):,.2f}
            Source: {command_info.get('data_source', 'market')}

            {SONICBOT_SYSTEM_PROMPT}

            Return ONLY a JSON object with:
            - analysis: your high-energy market breakdown
            - sentiment: "bullish"|"bearish"|"neutral"
            - confidence: number 0-100
            - recommendation: specific move to make"""

            try:
                analysis = await self.ai_processor.generate_response(query=prompt)
                if isinstance(analysis, dict) and "error" not in analysis:
                    return {
                        "data": market_data,
                        "token": command_info["token"],
                        "timeframe": command_info["timeframe"],
                        "data_source": command_info.get("data_source", "market"),
                        "analysis": analysis.get("analysis", "No analysis available"),
                        "sentiment": analysis.get("sentiment", "neutral"),
                        "confidence": analysis.get("confidence", 50),
                        "recommendation": analysis.get("recommendation", "hold"),
                        "chart": market_data.get("chart"),
                        "enhanced_chart": market_data.get("enhanced_chart")
                    }
                else:
                    logger.warning("AI analysis returned unexpected format, using defaults")
                    return {
                        "data": market_data,
                        "token": command_info["token"],
                        "timeframe": command_info["timeframe"],
                        "data_source": command_info.get("data_source", "market"),
                        "analysis": "Market analysis temporarily unavailable",
                        "sentiment": "neutral",
                        "confidence": 50,
                        "recommendation": "hold",
                        "chart": market_data.get("chart"),
                        "enhanced_chart": market_data.get("enhanced_chart")
                    }

            except Exception as e:
                logger.warning(f"AI analysis failed, using defaults: {str(e)}")
                return {
                    "data": market_data,
                    "token": command_info["token"],
                    "timeframe": command_info["timeframe"],
                    "data_source": command_info.get("data_source", "market"),
                    "analysis": "Market analysis temporarily unavailable",
                    "sentiment": "neutral",
                    "confidence": 50,
                    "recommendation": "hold",
                    "chart": market_data.get("chart"),
                    "enhanced_chart": market_data.get("enhanced_chart")
                }

        except Exception as e:
            logger.error(f"Error in market analysis: {str(e)}")
            return {"error": str(e)}