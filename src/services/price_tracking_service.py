"""Price tracking service with multi-agent workflow"""
import logging
import re
from typing import Optional, Tuple, Dict, Any, List
from src.services.dexscreener_service import (
    DexScreenerService, SONIC, 
    BASE  # Updated to use BASE instead of BASE_CHAIN
)
# Import chain IDs from constants
from src.constants.chain_config import SONIC_CHAIN_ID, SONIC_CHAIN_ID_STR, BASE_CHAIN_ID
from src.utils.ai_processor import AIProcessor

logger = logging.getLogger(__name__)

class PriceTrackingDirector:
    """Director agent that parses price queries"""
    def __init__(self, ai_processor: AIProcessor):
        self.ai_processor = ai_processor
        # Default to Sonic chain when SONIC token is involved
        self.chain_mappings = {
            'SONIC': {'id': SONIC_CHAIN_ID, 'name': 'Sonic'},  # Sonic chain ID
            'ETH': {'id': '1', 'name': 'Ethereum'},
            'ARB': {'id': '42161', 'name': 'Arbitrum'},
            'OP': {'id': '10', 'name': 'Optimism'},
            'BASE': {'id': BASE_CHAIN_ID, 'name': BASE.capitalize()}  # Updated to use BASE
        }

        # Token to chain mappings
        self.token_chain_mappings = {
            'SONIC': 'SONIC',
            'ETH': 'ETH', 
            'ARB': 'ARB',
            'OP': 'OP',
            'TOSHI': 'BASE'  # TOSHI is native to Base chain
        }

    async def process_query(self, query: str) -> Tuple[Optional[str], Optional[str]]:
        """Process price query to identify chain and pair"""
        try:
            # Extract token pair from query
            pair_match = re.search(r'(?:price of\s+)?([A-Za-z0-9]+)/([A-Za-z0-9]+)', query, re.IGNORECASE)
            if pair_match:
                base_token, quote_token = pair_match.groups()
                search_query = f"{base_token}/{quote_token}"

                # Check if base token is mapped to a specific chain
                base_token_upper = base_token.upper()
                if base_token_upper in self.token_chain_mappings:
                    chain_key = self.token_chain_mappings[base_token_upper]
                    chain_info = self.chain_mappings[chain_key]
                    logger.info(f"Identified chain: {chain_info['name']} (ID: {chain_info['id']}) with search query: {search_query}")
                    return chain_info['id'], search_query

                # Otherwise use AI to analyze
                prompt = (
                    "Analyze this price query and identify the chain and pair:\n"
                    f"Query: {query}\n\n"
                    "Only respond with a JSON object containing:\n"
                    "{\n"
                    '  "chain": "SONIC|ETH|ARB|OP|BASE",\n'
                    '  "base_token": "token symbol",\n'
                    '  "quote_token": "token symbol"\n'
                    "}"
                )

                response = await self.ai_processor.generate_response(prompt)
                logger.debug(f"AI Response: {response}")

                if "error" in response:
                    logger.error(f"AI error: {response['error']}")
                    return None, None

                chain = response.get('chain')
                chain_info = self.chain_mappings.get(chain.upper())
                if not chain_info:
                    logger.error(f"Unsupported chain: {chain}")
                    return None, None

                logger.info(f"Identified chain: {chain_info['name']} (ID: {chain_info['id']}) with search query: {search_query}")
                return chain_info['id'], search_query

            logger.error("Could not extract token pair from query")
            return None, None

        except Exception as e:
            logger.error(f"Error processing price query: {str(e)}")
            return None, None


class PriceTrackingWorker:
    """Worker agent for fetching DexScreener data"""
    def __init__(self):
        self.dex_service = DexScreenerService()

    async def fetch_price_data(self, chain_id: str, search_query: str) -> Dict[str, Any]:
        """Fetch price data from DexScreener using search_pairs()"""
        try:
            logger.info(f"Fetching price data for chain {chain_id}, query: {search_query}")

            # Search for pairs using DexScreener service with chain filter
            async with self.dex_service as service:
                pairs = await service.search_pairs(search_query, chain_id)
                logger.debug(f"Found {len(pairs)} total pairs")

                if not pairs:
                    logger.error("No pairs found from DexScreener")
                    return {"error": "No price data available"}

                # Get pair with highest liquidity
                pair = max(pairs, key=lambda x: float(x.get('liquidity', {}).get('usd', 0) or 0))
                logger.debug(f"Selected pair: {pair.get('pairAddress')} with highest liquidity")

                # Format the response data using PairInfo structure
                return {
                    "price": float(pair.get('priceUsd', 0)),
                    "price_change": float(pair.get('priceChange', {}).get('h24', 0) or 0),
                    "volume_24h": float(pair.get('volume24h', 0)),
                    "liquidity": float(pair.get('liquidity', {}).get('usd', 0) or 0),
                    "symbol": f"{pair.get('baseToken', {}).get('symbol', '')}/{pair.get('quoteToken', {}).get('symbol', '')}",
                    "dex": pair.get('dexId', 'Unknown'),
                    "chain": pair.get('chainId', 'Unknown')
                }

        except Exception as e:
            logger.error(f"Error fetching price data: {str(e)}")
            return {"error": f"Failed to fetch price data: {str(e)}"}


class PriceTrackingService:
    """Main service coordinating price tracking agents"""
    def __init__(self, ai_processor: AIProcessor):
        self.director = PriceTrackingDirector(ai_processor)
        self.worker = PriceTrackingWorker()
        self.ai_processor = ai_processor

    async def handle_price_query(self, query: str) -> Dict[str, Any]:
        """Handle price tracking query through the agent workflow"""
        try:
            # 1. Director identifies chain and pair
            chain_id, search_query = await self.director.process_query(query)
            if not chain_id:
                return {"error": "Could not identify blockchain from query"}

            # 2. Worker fetches price data
            price_data = await self.worker.fetch_price_data(chain_id, search_query)
            if "error" in price_data:
                return price_data

            # 3. Generate analysis using Anthropic
            response_prompt = (
                f"Analyze this market data and provide a concise summary:\n"
                f"Token: {price_data['symbol']}\n"
                f"Chain: {price_data['chain']}\n"
                f"DEX: {price_data['dex']}\n"
                f"Price: ${price_data['price']:.8f}\n"
                f"24h Change: {price_data['price_change']:+.2f}%\n"
                f"24h Volume: ${price_data['volume_24h']:,.2f}\n"
                f"Liquidity: ${price_data['liquidity']:,.2f}\n\n"
                f"Format your response as a JSON object with an 'analysis' field containing a market summary focusing on price action, volume, and liquidity metrics."
            )

            analysis = await self.ai_processor.generate_response(response_prompt)

            return {
                "data": price_data,
                "analysis": analysis.get('analysis', 'No analysis available'),
                "chain_id": chain_id,
                "pair": search_query
            }

        except Exception as e:
            logger.error(f"Error processing price request: {str(e)}")
            return {"error": f"Failed to process price query: {str(e)}"}

async def search_pairs(self, query: str, chain_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search for pairs with chain-specific quote token focus"""
    try:
        if not self.dex_service:
            logger.error("DexScreener service not initialized")
            return []

        # Use Sonic chain by default
        chain_id = chain_id or SONIC_CHAIN_ID_STR
        logger.debug(f"Searching pairs for chain {chain_id} with query: {query}")

        pairs = await self.dex_service.search_pairs(query, chain_id)
        if not pairs:
            logger.warning(f"No pairs found for query: {query} on chain: {chain_id}")
            return []

        logger.info(f"Found {len(pairs)} pairs for query: {query}")

        # Filter and validate pairs
        valid_pairs = []
        for pair in pairs:
            try:
                # Validate required fields
                if not all(k in pair for k in ['price', 'priceUsd', 'volume24h', 'liquidity']):
                    logger.warning(f"Skipping pair due to missing fields: {pair.get('pair')}")
                    continue

                # Validate numeric values
                values = [
                    float(pair['price']),
                    float(pair['priceUsd']),
                    float(pair['volume24h']),
                    float(pair['liquidity'])
                ]

                if any(not isinstance(v, float) or v < 0 for v in values):
                    logger.warning(f"Skipping pair due to invalid values: {pair.get('pair')}")
                    continue

                valid_pairs.append(pair)
                logger.debug(f"Valid pair found: {pair.get('pair')} - Price: ${pair['priceUsd']:.8f}")

            except (ValueError, TypeError) as e:
                logger.error(f"Error validating pair: {str(e)}")
                continue

        logger.info(f"Validated {len(valid_pairs)} pairs")
        return valid_pairs

    except Exception as e:
        logger.error(f"Error searching pairs: {str(e)}")
        return []