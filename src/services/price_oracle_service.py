"""Price Oracle Service for token pricing"""
import logging
from typing import Dict, Any, Optional, List
# Removed circular import
# from .dexscreener_service import DexScreenerService
from .equalizer_service import EqualizerService
from .abstract_service import AbstractService
from src.connections.defillama_connection import DefiLlamaConnection

logger = logging.getLogger(__name__)

class PriceOracleService(AbstractService):
    """Service for fetching token prices from multiple sources"""

    def __init__(self):
        super().__init__()
        # Lazy import to avoid circular dependency
        from .dexscreener_service import DexScreenerService
        self.dexscreener = DexScreenerService()
        self.equalizer = EqualizerService()
        self.defillama = DefiLlamaConnection()

    async def connect(self):
        """Initialize connections"""
        await self.defillama.connect()

    async def get_token_price(self, token_address: str, chain: str = 'sonic') -> float:
        """Get token price from multiple sources with fallbacks"""
        try:
            if not token_address:
                logger.error("Token address is required")
                return 0.0

            token_address = token_address.lower()

            # Try Equalizer first for Sonic chain tokens
            if chain.lower() == 'sonic':
                logger.debug(f"Trying Equalizer for token {token_address}")
                eq_data = await self.equalizer.fetch_global_stats()
                if eq_data and 'pairs' in eq_data:
                    for pair in eq_data['pairs']:
                        if (pair.get('token0', '').lower() == token_address or
                            pair.get('token1', '').lower() == token_address):
                            price = float(pair.get('priceUsd', 0))
                            if price > 0:
                                logger.info(f"Got price from Equalizer: ${price:.4f}")
                                return price

            # Try DexScreener second
            logger.debug(f"Trying DexScreener for token {token_address}")
            pairs = await self.dexscreener.search_pairs(token_address)
            if pairs:
                # Sort by liquidity to get most reliable pair
                sorted_pairs = sorted(
                    [p for p in pairs if p.get('liquidity', 0) > 0],
                    key=lambda x: float(x.get('liquidity', 0)),
                    reverse=True
                )
                if sorted_pairs:
                    price = float(sorted_pairs[0].get('price', 0))
                    if price > 0:
                        logger.info(f"Got price from DexScreener: ${price:.4f}")
                        return price

            # Fallback to DeFi Llama
            logger.debug(f"Trying DeFi Llama for token {token_address}")
            defillama_data = await self.defillama.get_token_price(chain, token_address)
            if defillama_data and 'price' in defillama_data:
                price = float(defillama_data['price'])
                logger.info(f"Got price from DeFi Llama: ${price:.4f}")
                return price

            logger.warning(f"No price found for {token_address} on any source")
            return 0.0

        except Exception as e:
            self.log_error(e, "Failed to get token price")
            return 0.0

    async def get_pair_liquidity(
        self,
        token_a: str,
        token_b: str,
        chain: str = 'sonic'
    ) -> float:
        """Get pair liquidity from multiple sources"""
        try:
            if not token_a or not token_b:
                logger.error("Both token addresses are required")
                return 0.0

            token_a = token_a.lower()
            token_b = token_b.lower()

            # Try Equalizer first for Sonic chain pairs
            if chain.lower() == 'sonic':
                eq_data = await self.equalizer.fetch_global_stats()
                if eq_data and 'pairs' in eq_data:
                    for pair in eq_data['pairs']:
                        if ((pair.get('token0', '').lower() == token_a and
                             pair.get('token1', '').lower() == token_b) or
                            (pair.get('token0', '').lower() == token_b and
                             pair.get('token1', '').lower() == token_a)):
                            liquidity = float(pair.get('liquidityUSD', 0))
                            if liquidity > 0:
                                logger.info(f"Got liquidity from Equalizer: ${liquidity:.2f}")
                                return liquidity

            # Try DexScreener
            pair_query = f"{token_a}/{token_b}"
            logger.debug(f"Trying DexScreener for pair {pair_query}")
            pairs = await self.dexscreener.search_pairs(pair_query)
            if pairs:
                sorted_pairs = sorted(
                    [p for p in pairs if p.get('liquidity', 0) > 0],
                    key=lambda x: float(x.get('liquidity', 0)),
                    reverse=True
                )
                if sorted_pairs:
                    liquidity = float(sorted_pairs[0].get('liquidity', 0))
                    if liquidity > 0:
                        logger.info(f"Got liquidity from DexScreener: ${liquidity:.2f}")
                        return liquidity

            logger.warning(f"No liquidity found for pair {token_a}/{token_b}")
            return 0.0

        except Exception as e:
            self.log_error(e, "Failed to get pair liquidity")
            return 0.0

    async def close(self):
        """Close connections"""
        await self.defillama.close()