import logging
import aiohttp
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

# Ensure src is in the Python path
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from constants.chain_config import SONIC_CHAIN_ID
from services.dexscreener_service import SONIC
from .base_connection import BaseConnection, Action, Parameter

logger = logging.getLogger(__name__)

class DexScreenerConnection(BaseConnection):
    """Connection for DexScreener API integration"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = "https://api.dexscreener.com/latest/dex"
        self.session: Optional[aiohttp.ClientSession] = None

        self.actions = {
            "search-pairs": Action(
                name="search-pairs",
                description="Search for trading pairs",
                parameters=[
                    Parameter(
                        name="query",
                        required=True,
                        type=str,
                        description="Search query string"
                    )
                ]
            ),
            "get-pair-info": Action(
                name="get-pair-info", 
                description="Get detailed information about a specific pair",
                parameters=[
                    Parameter(
                        name="pair_address",
                        required=True,
                        type=str,
                        description="Trading pair address"
                    ),
                    Parameter(
                        name="chain_id",
                        required=True,
                        type=str,
                        description="Chain ID"
                    )
                ]
            )
        }

    async def connect(self) -> bool:
        """Initialize connection"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                logger.info("Created new aiohttp session for DexScreener")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize DexScreener session: {str(e)}")
            return False

    async def _ensure_session(self) -> None:
        """Ensure aiohttp session exists"""
        if not self.session:
            await self.connect()

    async def _close_session(self) -> None:
        """Close aiohttp session if it exists"""
        if self.session:
            await self.session.close()
            self.session = None

    async def is_configured(self, verbose: bool = False) -> bool:
        """Check if the connection is properly configured"""
        return True  # DexScreener doesn't require authentication

    async def configure(self) -> bool:
        """Configure the connection"""
        return True  # No configuration needed for DexScreener

    async def _search_pairs(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Search for trading pairs"""
        try:
            # Ensure query is properly formatted
            query = query.strip()
            if not query:
                logger.error("Empty search query")
                return None

            # Fix: Use correct endpoint for Sonic chain search
            params = {"q": f"{SONIC} {query}"}
            logger.debug(f"Searching pairs with params: {params}")

            async with self.session.get(f"{self.base_url}/search", params=params) as response:
                response_text = await response.text()
                logger.debug(f"Response status: {response.status}")
                logger.debug(f"Response body: {response_text}")

                if response.status == 200:
                    data = await response.json()
                    pairs = data.get("pairs", [])
                    # Filter for Sonic chain pairs
                    sonic_pairs = [
                        pair for pair in pairs 
                        if pair.get('chainId', '').lower() == SONIC.lower() or 
                           pair.get('chainId') == SONIC_CHAIN_ID
                    ]
                    logger.info(f"Found {len(sonic_pairs)} Sonic pairs matching query: {query}")
                    return sonic_pairs
                else:
                    logger.warning(f"DexScreener API error: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error searching pairs: {e}")
            return None

    async def _get_pair_info(self, pair_address: str, chain_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific pair"""
        try:
            # Validate input parameters
            if not pair_address or not chain_id:
                logger.error("Missing required parameters")
                return None

            logger.debug(f"Getting pair info for {chain_id}/{pair_address}")

            # Fix: Use correct pairs endpoint format
            async with self.session.get(f"{self.base_url}/pairs/{chain_id}/{pair_address}") as response:
                response_text = await response.text()
                logger.debug(f"Response status: {response.status}")
                logger.debug(f"Response body: {response_text}")

                if response.status == 200:
                    data = await response.json()
                    pairs = data.get("pairs", [])
                    if pairs:
                        pair = pairs[0]
                        logger.info(f"Retrieved info for pair {pair_address}")
                        return pair
                    else:
                        logger.warning("No pair data found")
                        return None
                else:
                    logger.warning(f"DexScreener API error: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting pair info: {e}")
            return None

    async def perform_action(self, action_name: str, params: Dict[str, Any]) -> Optional[Any]:
        """Execute an action with the given parameters"""
        try:
            await self._ensure_session()

            if action_name == "search-pairs":
                return await self._search_pairs(params["query"])
            elif action_name == "get-pair-info":
                return await self._get_pair_info(params["pair_address"], params["chain_id"])
            else:
                logger.error(f"Unknown action: {action_name}")
                return None

        except Exception as e:
            logger.error(f"Error performing DexScreener action: {e}")
            return None
        finally:
            await self._close_session()
            
    async def start_background_updates(self) -> bool:
        """Start background updates for DexScreener data
        
        This method is called by MarketService to initiate background price updates.
        """
        try:
            await self._ensure_session()
            logger.info("DexScreener background updates started")
            return True
        except Exception as e:
            logger.error(f"Failed to start DexScreener background updates: {str(e)}")
            return False
            
    async def get_pairs(self, query: str) -> List[Dict[str, Any]]:
        """Get pairs matching the query
        
        This is a convenience method that wraps the perform_action method.
        """
        try:
            await self._ensure_session()
            return await self._search_pairs(query)
        except Exception as e:
            logger.error(f"Error getting pairs: {str(e)}")
            return []
        finally:
            # Don't close the session here as it may be used by other methods
            pass