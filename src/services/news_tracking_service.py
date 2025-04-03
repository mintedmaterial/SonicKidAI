"""News tracking service with multi-agent workflow"""
import logging
from typing import Optional, Dict, Any
from src.services.cryptopanic_service import CryptoPanicService
from src.utils.ai_processor import AIProcessor

logger = logging.getLogger(__name__)

class NewsDirector:
    """Director agent that parses news and trending queries"""
    def __init__(self, ai_processor: AIProcessor):
        self.ai_processor = ai_processor
        self.commands = {
            'latest_news': 'get_latest_news',
            'trending_topics': 'get_trending_topics',
            'market_sentiment': 'get_market_sentiment'
        }

    async def process_query(self, query: str) -> Optional[Dict[str, Any]]:
        """Process news query to identify command and parameters"""
        try:
            # Use AI to analyze query intent
            prompt = (
                "Analyze this news query and identify the command:\n"
                f"Query: {query}\n\n"
                "Only respond with a JSON object containing:\n"
                "{\n"
                '  "command": "news|trending|sentiment",\n'
                '  "timeframe": "24h|week|month",\n'
                '  "topic": "optional specific topic"\n'
                "}"
            )

            response = await self.ai_processor.generate_response(prompt)
            if "error" in response:
                logger.error(f"AI error: {response['error']}")
                return None

            # Get main command and map to CryptoPanic endpoints
            command = response.get('command', '').lower().strip()
            logger.debug(f"Raw command from AI: {command}")

            # Map command aliases
            if command == 'news':
                command = 'latest_news'
            elif 'trend' in command:
                command = 'trending_topics'
            elif 'sentiment' in command:
                command = 'market_sentiment'

            if command not in self.commands:
                logger.error(f"Unsupported command: {command}")
                return None

            return {
                'command': self.commands[command],
                'timeframe': response.get('timeframe', '24h'),
                'topic': response.get('topic')
            }

        except Exception as e:
            logger.error(f"Error processing news query: {str(e)}")
            return None

class NewsWorker:
    """Worker agent for fetching CryptoPanic data"""
    def __init__(self):
        self.cryptopanic = CryptoPanicService()

    async def fetch_news_data(self, command: str, timeframe: str = '24h', topic: Optional[str] = None) -> Dict[str, Any]:
        """Fetch news data based on command"""
        try:
            if not hasattr(self.cryptopanic, command):
                logger.error(f"Unsupported command: {command}")
                return {"error": "Invalid command"}

            # Call the appropriate CryptoPanic method
            method = getattr(self.cryptopanic, command)
            if command == 'get_market_sentiment':
                data = await method(timeframe)
            else:
                data = await method()

            if not data:
                return {"error": "No data available"}

            return data

        except Exception as e:
            logger.error(f"Error fetching news data: {str(e)}")
            return {"error": f"Failed to fetch news data: {str(e)}"}

class NewsTrackingService:
    """Main service coordinating news tracking agents"""
    def __init__(self, ai_processor: AIProcessor):
        self.director = NewsDirector(ai_processor)
        self.worker = NewsWorker()
        self.ai_processor = ai_processor

    async def handle_news_query(self, query: str) -> Dict[str, Any]:
        """Handle news tracking query through agent workflow"""
        try:
            # 1. Director identifies command and parameters
            command_info = await self.director.process_query(query)
            if not command_info:
                return {"error": "Could not process news query"}

            # 2. Worker fetches news data
            news_data = await self.worker.fetch_news_data(
                command_info['command'],
                command_info['timeframe'],
                command_info.get('topic')
            )
            if "error" in news_data:
                return news_data

            # 3. Generate analysis using AI
            try:
                if command_info['command'] == 'get_market_sentiment':
                    prompt = (
                        f"Analyze this market sentiment data:\n"
                        f"Sentiment: {news_data['sentiment']}\n"
                        f"Score: {news_data['score']}\n"
                        f"Confidence: {news_data['confidence']}%\n"
                        f"Summary: {news_data['summary']}\n\n"
                        f"Format your response as a JSON object with an 'analysis' field containing insights about the current market sentiment and its implications."
                    )
                else:
                    # For news/trending, analyze top 3 articles
                    articles = news_data.get('results', [])[:3]
                    articles_text = "\n\n".join([
                        f"Title: {article['title']}\n"
                        f"Source: {article['source']['title']}\n"
                        f"Votes: +{article.get('votes', {}).get('positive', 0)}/-{article.get('votes', {}).get('negative', 0)}"
                        for article in articles
                    ])

                    prompt = (
                        f"Analyze these top crypto news articles:\n"
                        f"{articles_text}\n\n"
                        f"Format your response as a JSON object with an 'analysis' field containing a summary of the key themes and potential market impact."
                    )

                analysis = await self.ai_processor.generate_response(prompt)
                analysis_text = analysis.get('analysis', 'No analysis available')
            except Exception as e:
                logger.error(f"Error generating analysis: {str(e)}")
                analysis_text = "Analysis temporarily unavailable"

            return {
                "data": news_data,
                "command": command_info['command'],
                "timeframe": command_info['timeframe'],
                "analysis": analysis_text
            }

        except Exception as e:
            logger.error(f"Error processing news request: {str(e)}")
            return {"error": f"Failed to process news query: {str(e)}"}