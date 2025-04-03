"""PaintSwap service for handling NFT data and market analysis"""
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from ..connections.paintswap_connection import PaintSwapConnection
from src.utils.ai_processor import AIProcessor

logger = logging.getLogger(__name__)

class PaintSwapService:
    """Service for handling PaintSwap NFT data and market analysis"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize PaintSwap service"""
        try:
            self.config = config or {}
            self.connection = PaintSwapConnection(self.config)
            self.ai_processor = AIProcessor(self.config) if self.config.get('openrouter_api_key') else None
            self._initialized = False
            logger.info("PaintSwap service initialized")
        except Exception as e:
            logger.error(f"Error initializing PaintSwap service: {str(e)}")
            raise

    async def initialize(self) -> bool:
        """Initialize service and test connection"""
        try:
            if self._initialized:
                return True

            connected = await self.connection.connect()
            if connected:
                # Test sales data fetch
                logger.info("Testing sales data fetch...")
                sales = await self.connection.get_sales(limit=1)
                if sales:
                    logger.info("✅ Successfully verified sales data access")
                    sample = sales[0]
                    logger.debug(f"Sample sale data: {json.dumps(sample, indent=2)}")
                    self._initialized = True
                    logger.info("✅ PaintSwap service initialized")
                    return True

            logger.error("❌ Failed to initialize PaintSwap service")
            return False

        except Exception as e:
            logger.error(f"❌ Error initializing PaintSwap service: {str(e)}")
            if hasattr(self, 'connection'):
                await self.connection.close()
            return False

    async def fetch_nft_data(self, collection_address: Optional[str] = None) -> Dict[str, Any]:
        """Fetch latest NFT data from PaintSwap"""
        try:
            if not self._initialized:
                logger.error("Service not initialized")
                return {'status': 'error', 'message': 'Service not initialized'}

            data = {
                'status': 'success',
                'sales': [],
                'stats': None,
                'errors': []
            }

            # Get recent sales
            sales = await self.connection.get_sales(limit=5)
            if sales:
                data['sales'] = sales
                logger.info(f"Retrieved {len(sales)} recent sales")
            else:
                data['errors'].append("Failed to fetch recent sales")

            # Get collection stats if address provided
            if collection_address:
                stats = await self.connection.get_collection_stats(collection_address)
                if stats:
                    data['stats'] = stats
                    logger.info("Retrieved collection statistics")
                else:
                    data['errors'].append("Failed to fetch collection stats")

            if data['errors']:
                data['status'] = 'partial'

            return data

        except Exception as e:
            logger.error(f"Error fetching NFT data: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    async def get_sales_data(self, limit: int = 10) -> Dict[str, Any]:
        """Get recent sales data - worker agent endpoint"""
        try:
            if not self._initialized:
                logger.error("Service not initialized")
                return {'status': 'error', 'message': 'Service not initialized'}

            # Fetch sales data
            logger.info(f"Fetching {limit} recent sales...")
            sales = await self.connection.get_sales(limit=limit)

            if sales:
                logger.info(f"Retrieved {len(sales)} sales")

                # Structure data for instructor agent
                data = {
                    'status': 'success',
                    'data': {
                        'sales': sales,
                        'count': len(sales),
                        'timestamp': datetime.now().isoformat(),
                        'summary': {
                            'total_volume_usd': sum(float(str(s.get('priceUsd', '0')).replace(',', '')) for s in sales),
                            'unique_collections': len(set(s.get('collection', {}).get('name', '') for s in sales)),
                            'avg_price_usd': sum(float(str(s.get('priceUsd', '0')).replace(',', '')) for s in sales) / len(sales) if sales else 0
                        }
                    }
                }

                # Log sample data for validation
                if sales:
                    sample = sales[0]
                    logger.debug("Sample sales data structure:")
                    logger.debug(f"Collection: {sample.get('collection', {}).get('name')}")
                    logger.debug(f"Price: ${sample.get('priceUsd')}")
                    logger.debug(f"Full sample: {json.dumps(sample, indent=2)}")

                # Generate AI insights if available
                if self.ai_processor:
                    try:
                        prompt = self._generate_sales_analysis_prompt(data['data'])
                        insights = await self.ai_processor.generate_response(prompt)
                        if insights:
                            data['data']['insights'] = insights
                            logger.info("Added AI insights to response")
                    except Exception as e:
                        logger.error(f"Error generating sales insights: {str(e)}")

                return data

            logger.warning("No sales data available")
            return {'status': 'error', 'message': 'No sales data available'}

        except Exception as e:
            logger.error(f"Error getting sales data: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def _generate_sales_analysis_prompt(self, data: Dict[str, Any]) -> str:
        """Generate AI analysis prompt for sales data"""
        return f"""Analyze this NFT sales data and provide key insights:
        Sales Data: {json.dumps(data.get('sales', [])[:3], indent=2)}
        Total Sales: {data.get('count', 0)}
        Timestamp: {data.get('timestamp')}

        Focus on:
        1. Recent sales trends
        2. Popular collections
        3. Price ranges
        4. Trading volume
        5. Key market indicators

        Format the analysis in a clear, concise manner.
        """

    async def process_discord_nft_data(self, message_content: str) -> Dict[str, Any]:
        """Process NFT data from Discord message"""
        try:
            logger.info("Processing Discord NFT data message")
            logger.debug(f"Raw message content: {message_content[:200]}")

            # Initialize response structure
            analysis = {
                'status': 'error',
                'data': {},
                'insights': None,
                'errors': []
            }

            # Parse message content
            collection_data = self._parse_nft_message(message_content)
            if collection_data:
                logger.info(f"Extracted NFT data: {collection_data}")
                analysis['data'].update(collection_data)

                # Get latest NFT data
                nft_data = await self.fetch_nft_data(collection_data.get('collection_address'))
                if nft_data['status'] != 'error':
                    analysis['data'].update(nft_data)
                else:
                    analysis['errors'].append(nft_data['message'])

                # Generate AI insights if available
                if self.ai_processor:
                    try:
                        logger.info("Generating AI insights for NFT data")
                        prompt = self._generate_analysis_prompt(analysis['data'])
                        insights = await self.ai_processor.generate_response(prompt)

                        if insights:
                            logger.info("Successfully generated AI insights")
                            analysis['insights'] = insights
                            analysis['status'] = 'success'
                        else:
                            analysis['errors'].append("Failed to generate insights")
                            analysis['status'] = 'partial'
                    except Exception as e:
                        logger.error(f"Error generating insights: {str(e)}")
                        analysis['errors'].append(f"AI analysis error: {str(e)}")
                        analysis['status'] = 'partial'
                else:
                    analysis['status'] = 'success'
                    logger.info("NFT data processed without AI insights (no AI processor available)")

                logger.info("✅ Successfully processed NFT data")
            else:
                analysis['errors'].append("No valid NFT data found in message")
                logger.warning("No valid NFT data found in message")

            return analysis

        except Exception as e:
            logger.error(f"❌ Error processing Discord NFT data: {str(e)}")
            return {'status': 'error', 'message': str(e), 'errors': [str(e)]}

    def _generate_analysis_prompt(self, data: Dict[str, Any]) -> str:
        """Generate AI analysis prompt"""
        return f"""Analyze this NFT collection data and provide key insights:
        Collection Data: {json.dumps(data.get('collection_data', {}), indent=2)}
        Sales Data: {json.dumps(data.get('sales', [])[:3], indent=2)}
        Stats: {json.dumps(data.get('stats', {}), indent=2)}

        Focus on:
        1. Market performance metrics
        2. Trading volume analysis
        3. Price trends and momentum
        4. Notable patterns or anomalies
        5. Recommendations for traders

        Format the analysis in a clear, concise manner.
        """

    def _parse_nft_message(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse NFT data from Discord message"""
        try:
            logger.debug(f"Parsing NFT message: {content[:200]}")
            data = {}

            # Support multiple message formats
            if '|' in content:
                # Format: Collection Name | Floor: 0.5 ETH | Volume: 100 ETH | Sales: 50
                data = self._parse_pipe_format(content)
            elif ' - ' in content:
                # Format: Collection Name - Floor 0.5 ETH - Volume 100 ETH
                data = self._parse_dash_format(content)

            if data:
                # Add metadata
                data.update({
                    'timestamp': datetime.now().isoformat(),
                    'source': 'discord',
                })

                logger.info(f"Successfully parsed NFT data: {data}")
                return data
            else:
                logger.warning("Could not parse NFT data from message")
                return None

        except Exception as e:
            logger.error(f"Error parsing NFT message: {str(e)}")
            return None

    def _parse_pipe_format(self, content: str) -> Dict[str, Any]:
        """Parse pipe-separated format"""
        data = {}
        try:
            parts = [p.strip() for p in content.split('|')]
            data['collection_name'] = parts[0].strip()

            for part in parts[1:]:
                try:
                    if ':' in part:
                        key, value = [p.strip() for p in part.split(':', 1)]
                        key = key.lower().replace(' ', '_')

                        value = value.strip()
                        if 'eth' in value.lower():
                            value = float(value.lower().replace('eth', '').strip())
                            key += '_eth'
                        elif value.replace('.', '').isdigit():
                            value = float(value)

                        data[key] = value
                except ValueError as ve:
                    logger.warning(f"Error parsing value in part '{part}': {str(ve)}")
                    continue
        except Exception as e:
            logger.error(f"Error parsing pipe format: {str(e)}")

        return data

    def _parse_dash_format(self, content: str) -> Dict[str, Any]:
        """Parse dash-separated format"""
        data = {}
        try:
            parts = [p.strip() for p in content.split(' - ')]
            data['collection_name'] = parts[0].strip()

            for part in parts[1:]:
                try:
                    words = part.split()
                    if len(words) >= 2:
                        key = words[0].lower()
                        value = ' '.join(words[1:]).strip()

                        if 'eth' in value.lower():
                            value = float(value.lower().replace('eth', '').strip())
                            key += '_eth'
                        elif value.replace('.', '').isdigit():
                            value = float(value)

                        data[key] = value
                except ValueError as ve:
                    logger.warning(f"Error parsing value in part '{part}': {str(ve)}")
                    continue
        except Exception as e:
            logger.error(f"Error parsing dash format: {str(e)}")

        return data

    async def close(self):
        """Close service connections"""
        try:
            if self._initialized:
                await self.connection.close()
                self._initialized = False
                logger.info("✅ PaintSwap service closed")
        except Exception as e:
            logger.error(f"❌ Error closing PaintSwap service: {str(e)}")

    async def get_nft_market_summary(self) -> Dict[str, Any]:
        """Get comprehensive NFT market summary"""
        try:
            if not self._initialized:
                logger.error("Service not initialized")
                return {'status': 'error', 'message': 'Service not initialized'}

            summary = {
                'status': 'error',
                'data': {}
            }

            # Get market overview
            overview = await self.connection.get_market_overview()
            if overview:
                summary['data']['overview'] = overview

            # Get trending collections
            trending = await self.connection.get_trending_collections(timeframe="24h")
            if trending:
                summary['data']['trending'] = trending[:5]  # Top 5 trending

            # Get recent sales
            sales = await self.connection.get_sales(limit=5)
            if sales:
                summary['data']['recent_sales'] = sales

            if any(summary['data'].values()):
                summary['status'] = 'success'
                logger.info("✅ Retrieved NFT market summary")
            else:
                logger.error("❌ Failed to get market summary")

            return summary

        except Exception as e:
            logger.error(f"❌ Error getting NFT market summary: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    async def get_collection_analysis(self, collection_address: str) -> Dict[str, Any]:
        """Get detailed collection analysis with AI insights"""
        try:
            if not self._initialized:
                logger.error("Service not initialized")
                return {'status': 'error', 'message': 'Service not initialized'}

            analysis = {
                'status': 'error',
                'data': {}
            }

            # Get collection stats
            stats = await self.connection.get_collection_stats(collection_address)
            if stats:
                analysis['data']['stats'] = stats

                # Add AI analysis if available
                if self.ai_processor:
                    try:
                        prompt = f"""Analyze this NFT collection data and provide insights:
                        Collection Stats: {stats}

                        Focus on:
                        1. Market performance
                        2. Trading volume trends
                        3. Key metrics analysis
                        4. Potential opportunities/risks
                        """

                        ai_analysis = await self.ai_processor.generate_response(prompt)
                        if ai_analysis:
                            analysis['data']['ai_insights'] = ai_analysis
                    except Exception as e:
                        logger.error(f"Error getting AI analysis: {str(e)}")

                analysis['status'] = 'success'
                logger.info(f"✅ Retrieved collection analysis for {collection_address}")
            else:
                logger.error(f"❌ Failed to get collection analysis for {collection_address}")

            return analysis

        except Exception as e:
            logger.error(f"❌ Error analyzing collection: {str(e)}")
            return {'status': 'error', 'message': str(e)}