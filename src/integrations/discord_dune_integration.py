"""
Discord integration for Dune Analytics data
"""
import re
import json
import logging
import discord
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from discord import Embed, Color

from ..services.dune_analytics_service import DuneAnalyticsService
from ..actions.dune_data_actions import DuneDataActions

logger = logging.getLogger(__name__)

class DiscordDuneIntegration:
    """Discord integration for Dune Analytics data"""
    def __init__(self, dune_service: DuneAnalyticsService):
        """Initialize with Dune Analytics service"""
        self.dune_service = dune_service
        self.dune_actions = DuneDataActions(dune_service)
    
    async def process_message(self, message_content: str) -> Optional[Tuple[str, Optional[Embed]]]:
        """
        Process a Discord message to see if it's asking about on-chain data
        
        Args:
            message_content: The content of the Discord message
            
        Returns:
            Tuple of (response text, optional embed) or None if not relevant
        """
        message_content = message_content.lower().strip()
        
        # Check for pool/pair queries
        pool_match = re.search(r'pool(?:\s+id)?\s+([a-zA-Z0-9]+)', message_content)
        pair_match = re.search(r'pair\s+([a-zA-Z0-9]+)(?:[\/\-\s]+([a-zA-Z0-9]+))?', message_content)
        dex_match = re.search(r'(shadow|sonic|metro|beets)\s+(pools?|pairs?|data|stats)', message_content)
        tokens_match = re.search(r'([a-zA-Z0-9]+)[\/\-\s]+([a-zA-Z0-9]+)(?:\s+on\s+(shadow|sonic|metro|beets))?', message_content)
        
        try:
            # Handle pool ID query
            if pool_match:
                pool_id = pool_match.group(1)
                
                # Check for DEX specification
                dex = None
                for dex_name in ['shadow', 'sonic', 'metro', 'beets']:
                    if dex_name in message_content:
                        dex = dex_name
                        break
                
                pool_data = await self.dune_actions.find_pool_by_id(pool_id, dex)
                return self._format_pool_response(pool_id, pool_data, dex)
            
            # Handle pair query
            elif pair_match:
                token_a = pair_match.group(1)
                token_b = pair_match.group(2) if pair_match.group(2) else None
                
                # Check for DEX specification
                dex = None
                for dex_name in ['shadow', 'sonic', 'metro', 'beets']:
                    if dex_name in message_content:
                        dex = dex_name
                        break
                
                pair_data = await self.dune_actions.find_pair_data(token_a, token_b, dex)
                return self._format_pair_response(token_a, token_b, pair_data, dex)
            
            # Handle DEX query
            elif dex_match:
                dex = dex_match.group(1)
                dex_data = await self.dune_actions.get_dex_summary(dex)
                return self._format_dex_response(dex, dex_data)
            
            # Handle tokens query (e.g., "ETH/USDC")
            elif tokens_match:
                token_a = tokens_match.group(1)
                token_b = tokens_match.group(2)
                dex = tokens_match.group(3) if tokens_match.group(3) else None
                
                pair_data = await self.dune_actions.find_pair_data(token_a, token_b, dex)
                return self._format_pair_response(token_a, token_b, pair_data, dex)
            
            # Check for general on-chain data questions
            elif any(term in message_content for term in ['on-chain', 'onchain', 'dune data', 'dune analytics']):
                # This is a general on-chain data question, but not specific enough
                return ("I can provide on-chain data from Dune Analytics for specific pools, pairs, or DEXes. "
                       "Try asking about a specific pair (e.g., 'ETH/USDC pair'), "
                       "a pool (e.g., 'pool 0x123abc'), or a DEX (e.g., 'Shadow DEX data')."), None
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return f"Error processing on-chain data request: {str(e)}", None
    
    def _format_pool_response(self, pool_id: str, pool_data: Dict[str, Any], dex: Optional[str]) -> Tuple[str, Optional[Embed]]:
        """Format response for pool query"""
        if not pool_data or all(not value for value in pool_data.values()):
            return f"I couldn't find data for pool ID {pool_id}" + (f" on {dex.capitalize()}" if dex else ""), None
        
        # Create embed
        embed = Embed(
            title=f"Pool {pool_id} Data" + (f" on {dex.capitalize()}" if dex else ""),
            color=Color.blue()
        )
        
        # Check for error
        if 'error' in pool_data:
            return f"Error retrieving pool data: {pool_data['error']}", None
        
        # Add pool data to embed
        for dex_name, dex_pool_data in pool_data.items():
            if dex_pool_data:
                # Format fields based on available data
                if 'tvl' in dex_pool_data:
                    embed.add_field(
                        name=f"{dex_name.capitalize()} TVL",
                        value=f"${dex_pool_data['tvl']:,.2f}",
                        inline=True
                    )
                
                if 'volume_usd' in dex_pool_data:
                    embed.add_field(
                        name=f"{dex_name.capitalize()} Volume",
                        value=f"${dex_pool_data['volume_usd']:,.2f}",
                        inline=True
                    )
                
                if 'token0_symbol' in dex_pool_data and 'token1_symbol' in dex_pool_data:
                    tokens = f"{dex_pool_data['token0_symbol']}/{dex_pool_data['token1_symbol']}"
                    embed.add_field(
                        name="Tokens",
                        value=tokens,
                        inline=True
                    )
                
                if 'swap_fee' in dex_pool_data:
                    embed.add_field(
                        name="Swap Fee",
                        value=f"{dex_pool_data['swap_fee'] * 100:.2f}%",
                        inline=True
                    )
        
        # Add footer
        embed.set_footer(text=f"Data from Dune Analytics | dune.com")
        
        # Create response text
        response = f"Here's what I found about pool {pool_id}"
        if dex:
            response += f" on {dex.capitalize()}"
        
        return response, embed
    
    def _format_pair_response(self, token_a: str, token_b: Optional[str], pair_data: Dict[str, Any], dex: Optional[str]) -> Tuple[str, Optional[Embed]]:
        """Format response for pair query"""
        token_display = f"{token_a.upper()}/{token_b.upper()}" if token_b else token_a.upper()
        
        if not pair_data or all(not value for value in pair_data.values()):
            return f"I couldn't find data for {token_display} pair" + (f" on {dex.capitalize()}" if dex else ""), None
        
        # Check for error
        if 'error' in pair_data:
            return f"Error retrieving pair data: {pair_data['error']}", None
        
        # Create embed
        embed = Embed(
            title=f"{token_display} Pair Data" + (f" on {dex.capitalize()}" if dex else ""),
            color=Color.green()
        )
        
        # Add pair data for each DEX
        for dex_name, dex_pair_data in pair_data.items():
            if dex_pair_data and isinstance(dex_pair_data, dict):
                # Add section for each DEX
                if 'pairs_found' in dex_pair_data and dex_pair_data['pairs_found'] > 0:
                    embed.add_field(
                        name=f"{dex_name.capitalize()}",
                        value=f"Found {dex_pair_data['pairs_found']} pairs",
                        inline=False
                    )
                    
                    # Add summary data if available
                    if 'summary' in dex_pair_data:
                        summary = dex_pair_data['summary']
                        
                        if 'total_tvl' in summary:
                            embed.add_field(
                                name=f"{dex_name.capitalize()} Total TVL",
                                value=f"${summary['total_tvl']:,.2f}",
                                inline=True
                            )
                        
                        if 'total_volume' in summary:
                            embed.add_field(
                                name=f"{dex_name.capitalize()} Total Volume",
                                value=f"${summary['total_volume']:,.2f}",
                                inline=True
                            )
                        
                        if 'average_apr' in summary:
                            embed.add_field(
                                name=f"{dex_name.capitalize()} Avg APR",
                                value=f"{summary['average_apr']:.2f}%",
                                inline=True
                            )
                
                # Add TVL data for Sonic (doesn't have individual pairs)
                elif dex_name == 'sonic' and 'tvl' in dex_pair_data:
                    tvl_data = dex_pair_data['tvl']
                    
                    if 'latest_tvl' in tvl_data:
                        embed.add_field(
                            name="Sonic TVL",
                            value=f"${tvl_data['latest_tvl']:,.2f}",
                            inline=True
                        )
                    
                    if 'tvl_change_24h' in tvl_data:
                        embed.add_field(
                            name="24h TVL Change",
                            value=f"{tvl_data['tvl_change_24h']:.2f}%",
                            inline=True
                        )
        
        # Add footer
        embed.set_footer(text=f"Data from Dune Analytics | dune.com")
        
        # Create response text
        response = f"Here's what I found about {token_display} pair"
        if dex:
            response += f" on {dex.capitalize()}"
        
        return response, embed
    
    def _format_dex_response(self, dex: str, dex_data: Dict[str, Any]) -> Tuple[str, Optional[Embed]]:
        """Format response for DEX query"""
        if not dex_data:
            return f"I couldn't find data for {dex.capitalize()} DEX", None
        
        # Check for error
        if 'error' in dex_data:
            return f"Error retrieving DEX data: {dex_data['error']}", None
        
        # Create embed
        embed = Embed(
            title=f"{dex.capitalize()} DEX Data",
            color=Color.gold()
        )
        
        # Add TVL data
        if 'tvl' in dex_data and dex_data['tvl']:
            tvl_data = dex_data['tvl']
            
            if 'latest_tvl' in tvl_data:
                embed.add_field(
                    name="Total Value Locked (TVL)",
                    value=f"${tvl_data['latest_tvl']:,.2f}",
                    inline=True
                )
        
        # Add volume data
        if 'volume' in dex_data and dex_data['volume']:
            volume_data = dex_data['volume']
            
            if 'total_volume_usd' in volume_data:
                embed.add_field(
                    name="Total Volume",
                    value=f"${volume_data['total_volume_usd']:,.2f}",
                    inline=True
                )
        
        # Add transaction data (Sonic)
        if 'transactions' in dex_data and dex_data['transactions']:
            tx_data = dex_data['transactions']
            
            if 'total_transactions' in tx_data:
                embed.add_field(
                    name="Total Transactions",
                    value=f"{tx_data['total_transactions']:,}",
                    inline=True
                )
        
        # Add fees data
        if 'fees' in dex_data and dex_data['fees']:
            fees_data = dex_data['fees']
            
            if 'total_fees_usd' in fees_data:
                embed.add_field(
                    name="Total Fees",
                    value=f"${fees_data['total_fees_usd']:,.2f}",
                    inline=True
                )
        
        # Add metrics data (Metro)
        if 'metrics' in dex_data and dex_data['metrics']:
            metrics_data = dex_data['metrics']
            
            if 'pool_count' in metrics_data:
                embed.add_field(
                    name="Pool Count",
                    value=f"{metrics_data['pool_count']:,}",
                    inline=True
                )
            
            if 'total_volume_24h' in metrics_data:
                embed.add_field(
                    name="24h Volume",
                    value=f"${metrics_data['total_volume_24h']:,.2f}",
                    inline=True
                )
        
        # Add footer
        embed.set_footer(text=f"Data from Dune Analytics | dune.com")
        
        # Create response text
        response = f"Here's the latest on-chain data for {dex.capitalize()} DEX"
        
        return response, embed