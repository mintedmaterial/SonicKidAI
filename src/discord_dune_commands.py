"""
Discord bot commands for Dune Analytics integration

This module provides Discord commands for accessing on-chain data
from Dune Analytics for various DeFi platforms.
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import os

try:
    import discord
    from discord.ext import commands
    from discord import Embed, Color
except ImportError:
    # Create mock classes for type checking when Discord is not available
    class commands:
        class Cog:
            pass
        class Context:
            pass
        class Bot:
            pass
    class Embed:
        pass
    class Color:
        pass

from .services.market_service_with_dune import MarketServiceWithDune

# Setup logging
logger = logging.getLogger(__name__)

class DuneAnalyticsCommands(commands.Cog):
    """Discord commands for Dune Analytics integration"""
    
    def __init__(self, bot: commands.Bot, market_service: MarketServiceWithDune):
        """Initialize Dune Analytics commands"""
        self.bot = bot
        self.market_service = market_service
        
    @commands.command(name="dexdata")
    async def dex_data(self, ctx: commands.Context, dex_name: str = None):
        """
        Get DEX data from Dune Analytics
        
        Usage:
        !dexdata [dex_name]
        
        Examples:
        !dexdata shadow
        !dexdata sonic
        !dexdata metro
        !dexdata beets
        !dexdata (for all DEXes)
        """
        async with ctx.typing():
            try:
                if dex_name:
                    # Get data for a specific DEX
                    dex_name = dex_name.lower()
                    data = await self.market_service.get_dex_data(dex_name)
                    
                    if not data or "rows" not in data:
                        await ctx.send(f"❌ No data found for DEX: {dex_name}")
                        return
                    
                    # Create Discord embed for DEX data
                    embed = Embed(
                        title=f"{dex_name.capitalize()} DEX Data",
                        description=f"On-chain data from Dune Analytics",
                        color=Color.blue()
                    )
                    
                    # Add key metrics
                    row_count = len(data["rows"])
                    embed.add_field(name="Pairs", value=str(row_count), inline=True)
                    
                    # Calculate total metrics
                    total_volume = sum(float(row.get("volume_24h", 0)) for row in data["rows"] if row.get("volume_24h"))
                    total_tvl = sum(float(row.get("tvl", 0)) for row in data["rows"] if row.get("tvl"))
                    
                    embed.add_field(name="Total Volume (24h)", value=f"${total_volume:,.2f}", inline=True)
                    embed.add_field(name="Total TVL", value=f"${total_tvl:,.2f}", inline=True)
                    
                    # Add timestamp
                    embed.set_footer(text=f"Data retrieved at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    
                    await ctx.send(embed=embed)
                    
                    # If many pairs, show top 5 by volume
                    if row_count > 5:
                        # Sort by volume
                        sorted_pairs = sorted(data["rows"], key=lambda x: float(x.get("volume_24h", 0)), reverse=True)
                        top_pairs = sorted_pairs[:5]
                        
                        embed = Embed(
                            title=f"Top 5 Pairs by Volume on {dex_name.capitalize()}",
                            color=Color.green()
                        )
                        
                        for pair in top_pairs:
                            token0 = pair.get("token0_symbol", "Unknown")
                            token1 = pair.get("token1_symbol", "Unknown")
                            volume = float(pair.get("volume_24h", 0))
                            tvl = float(pair.get("tvl", 0))
                            
                            embed.add_field(
                                name=f"{token0}/{token1}",
                                value=f"Volume: ${volume:,.2f}\nTVL: ${tvl:,.2f}",
                                inline=True
                            )
                        
                        await ctx.send(embed=embed)
                    
                else:
                    # Get comparison data for all DEXes
                    comparison = await self.market_service.get_dex_comparison()
                    
                    if "error" in comparison:
                        await ctx.send(f"❌ Error getting DEX comparison: {comparison['error']}")
                        return
                    
                    embed = Embed(
                        title="DEX Comparison",
                        description="On-chain data comparison across DEXes",
                        color=Color.gold()
                    )
                    
                    dex_names = list(comparison.get("dexes", {}).keys())
                    embed.add_field(name="DEXes Compared", value=", ".join(dex_names) or "None found", inline=False)
                    
                    for dex_name in dex_names:
                        dex_metrics = comparison["dexes"].get(dex_name, {})
                        comparison_data = comparison.get("comparisons", {}).get(dex_name, {})
                        
                        metrics_text = (
                            f"Pairs: {dex_metrics.get('pair_count', 0)}\n"
                            f"Volume (24h): ${dex_metrics.get('total_volume_24h', 0):,.2f}\n"
                            f"TVL: ${dex_metrics.get('total_tvl', 0):,.2f}\n"
                            f"Market Share: {comparison_data.get('tvl_share_percent', 0):.1f}%\n"
                            f"Rank: #{comparison_data.get('tvl_rank', 'N/A')}"
                        )
                        
                        embed.add_field(name=dex_name.capitalize(), value=metrics_text, inline=True)
                    
                    await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error in dex_data command: {str(e)}", exc_info=True)
                await ctx.send(f"❌ Error retrieving DEX data: {str(e)}")
    
    @commands.command(name="sonictvl")
    async def sonic_tvl(self, ctx: commands.Context):
        """
        Get Sonic TVL data with chart
        
        Usage:
        !sonictvl
        """
        async with ctx.typing():
            try:
                # Get Sonic TVL data
                data = await self.market_service.get_sonic_tvl()
                
                if not data or "rows" not in data:
                    await ctx.send("❌ No Sonic TVL data found")
                    return
                
                # Create embed for TVL data
                embed = Embed(
                    title="Sonic TVL Data",
                    description="Total Value Locked in Sonic over time",
                    color=Color.purple()
                )
                
                # Get last data point for current TVL
                rows = data["rows"]
                if rows:
                    current_tvl = float(rows[-1].get("tvl", 0))
                    
                    # Calculate 7-day change if we have enough data
                    tvl_change = 0
                    if len(rows) > 7:
                        week_ago_tvl = float(rows[-8].get("tvl", 0))
                        if week_ago_tvl > 0:
                            tvl_change = ((current_tvl - week_ago_tvl) / week_ago_tvl) * 100
                    
                    embed.add_field(name="Current TVL", value=f"${current_tvl:,.2f}", inline=True)
                    embed.add_field(name="7-day Change", value=f"{tvl_change:+.2f}%", inline=True)
                    
                    # Add data points count
                    embed.add_field(name="Data Points", value=str(len(rows)), inline=True)
                
                # Add timestamp
                embed.set_footer(text=f"Data retrieved at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                
                await ctx.send(embed=embed)
                
                # TODO: In a future update, generate and attach a chart image
                # For now, just display the message that this feature is coming
                await ctx.send("📊 Chart visualization feature coming soon!")
                
            except Exception as e:
                logger.error(f"Error in sonic_tvl command: {str(e)}", exc_info=True)
                await ctx.send(f"❌ Error retrieving Sonic TVL data: {str(e)}")
    
    @commands.command(name="poolquery")
    async def pool_query(self, ctx: commands.Context, pool_id: str = None, dex_name: str = None):
        """
        Query for a specific pool by ID
        
        Usage:
        !poolquery <pool_id> [dex_name]
        
        Examples:
        !poolquery 0x1234...5678
        !poolquery 0x1234...5678 sonic
        !poolquery 0x1234...5678 shadow
        """
        async with ctx.typing():
            try:
                if not pool_id:
                    await ctx.send("❌ Please provide a pool ID to search for")
                    return
                
                # Search for pool across DEXes
                pool_data = await self.market_service.search_pools(pool_id, dex_name)
                
                if not pool_data or not pool_data.get("pools"):
                    await ctx.send(f"❌ No pool found with ID: {pool_id}")
                    return
                
                # Create embed for pool data
                embed = Embed(
                    title=f"Pool Data for {pool_id[:8]}...{pool_id[-4:]}",
                    description=f"Data from Dune Analytics",
                    color=Color.blue()
                )
                
                # Add DEXes where the pool was found
                dex_list = list(pool_data["pools"].keys())
                embed.add_field(name="Found on DEXes", value=", ".join(dex_list), inline=False)
                
                # Add pool details - just take the first DEX for now
                first_dex = dex_list[0]
                first_pool = pool_data["pools"][first_dex][0]
                
                token0 = first_pool.get("token0_symbol", "Unknown")
                token1 = first_pool.get("token1_symbol", "Unknown")
                
                embed.add_field(name="Pair", value=f"{token0}/{token1}", inline=True)
                
                # Add key metrics if available
                if "volume_24h" in first_pool:
                    embed.add_field(name="24h Volume", value=f"${float(first_pool['volume_24h']):,.2f}", inline=True)
                
                if "tvl" in first_pool:
                    embed.add_field(name="TVL", value=f"${float(first_pool['tvl']):,.2f}", inline=True)
                
                if "fee" in first_pool:
                    embed.add_field(name="Fee", value=f"{float(first_pool['fee']) * 100:.2f}%", inline=True)
                
                # Add timestamp
                embed.set_footer(text=f"Data retrieved at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                
                await ctx.send(embed=embed)
                
                # If pool found on multiple DEXes, show comparison
                if len(dex_list) > 1:
                    comparison_embed = Embed(
                        title=f"Pool Comparison Across DEXes",
                        description=f"Comparing {token0}/{token1} pool across DEXes",
                        color=Color.green()
                    )
                    
                    for dex in dex_list:
                        dex_pool = pool_data["pools"][dex][0]
                        
                        volume = float(dex_pool.get("volume_24h", 0))
                        tvl = float(dex_pool.get("tvl", 0))
                        
                        comparison_embed.add_field(
                            name=dex.capitalize(),
                            value=f"Volume: ${volume:,.2f}\nTVL: ${tvl:,.2f}",
                            inline=True
                        )
                    
                    await ctx.send(embed=comparison_embed)
                
            except Exception as e:
                logger.error(f"Error in pool_query command: {str(e)}", exc_info=True)
                await ctx.send(f"❌ Error querying pool data: {str(e)}")
    
    @commands.command(name="pairquery")
    async def pair_query(self, ctx: commands.Context, token_a: str = None, token_b: str = None, dex_name: str = None):
        """
        Query for token pairs across DEXes
        
        Usage:
        !pairquery <token_a> [token_b] [dex_name]
        
        Examples:
        !pairquery WETH
        !pairquery WETH USDC
        !pairquery WETH USDC sonic
        """
        async with ctx.typing():
            try:
                if not token_a:
                    await ctx.send("❌ Please provide at least one token symbol to search for")
                    return
                
                # Search for pairs
                pair_data = await self.market_service.search_pairs(token_a, token_b, dex_name)
                
                if not pair_data or not pair_data.get("records"):
                    await ctx.send(f"❌ No pairs found for {token_a}{' / ' + token_b if token_b else ''}")
                    return
                
                # Create main embed for pair count
                pairs = pair_data["records"]
                pair_count = len(pairs)
                
                query_desc = f"Token: {token_a}"
                if token_b:
                    query_desc += f" / {token_b}"
                if dex_name:
                    query_desc += f" on {dex_name}"
                
                embed = Embed(
                    title=f"Pair Search Results",
                    description=query_desc,
                    color=Color.blue()
                )
                
                embed.add_field(name="Pairs Found", value=str(pair_count), inline=False)
                
                # Count pairs by DEX
                dex_counts = {}
                for pair in pairs:
                    dex = pair.get("dex", "unknown")
                    dex_counts[dex] = dex_counts.get(dex, 0) + 1
                
                dex_summary = "\n".join([f"{dex.capitalize()}: {count}" for dex, count in dex_counts.items()])
                embed.add_field(name="DEX Distribution", value=dex_summary or "None", inline=False)
                
                # Add timestamp
                embed.set_footer(text=f"Data retrieved at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                
                await ctx.send(embed=embed)
                
                # If we have pairs, show top 5 by volume
                if pair_count > 0:
                    # Sort by volume if available
                    try:
                        sorted_pairs = sorted(
                            pairs, 
                            key=lambda x: float(x.get("volume_24h", 0)), 
                            reverse=True
                        )
                    except Exception:
                        # If sorting fails, use original order
                        sorted_pairs = pairs
                    
                    top_pairs = sorted_pairs[:5]
                    
                    comparison_embed = Embed(
                        title=f"Top Pairs for {token_a}{' / ' + token_b if token_b else ''}",
                        color=Color.green()
                    )
                    
                    for pair in top_pairs:
                        token0 = pair.get("token0_symbol", "Unknown")
                        token1 = pair.get("token1_symbol", "Unknown")
                        dex = pair.get("dex", "Unknown").capitalize()
                        
                        # Get volume and TVL if available
                        volume = pair.get("volume_24h", "N/A")
                        if volume != "N/A":
                            volume = f"${float(volume):,.2f}"
                        
                        tvl = pair.get("tvl", "N/A")
                        if tvl != "N/A":
                            tvl = f"${float(tvl):,.2f}"
                        
                        comparison_embed.add_field(
                            name=f"{token0}/{token1} on {dex}",
                            value=f"Volume: {volume}\nTVL: {tvl}",
                            inline=True
                        )
                    
                    await ctx.send(embed=comparison_embed)
                
            except Exception as e:
                logger.error(f"Error in pair_query command: {str(e)}", exc_info=True)
                await ctx.send(f"❌ Error querying pair data: {str(e)}")

def setup(bot: commands.Bot, market_service: MarketServiceWithDune = None):
    """Register the Dune Analytics commands with the bot"""
    if not market_service:
        # Create a new market service if one is not provided
        market_service = MarketServiceWithDune()
        
    # Register the commands
    bot.add_cog(DuneAnalyticsCommands(bot, market_service))