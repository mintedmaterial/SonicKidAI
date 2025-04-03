"""
Telegram handlers for Dune Analytics integration
"""
import logging
import asyncio
import json
import io
from typing import Dict, Any, Optional, List, Callable
import matplotlib.pyplot as plt
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from src.services.market_service_with_dune import MarketService
from src.services.dune_analytics_service import DuneAnalyticsService, DUNE_QUERIES

logger = logging.getLogger(__name__)

class DuneAnalyticsHandlers:
    """Telegram handlers for Dune Analytics integration"""
    
    def __init__(self, market_service: MarketService):
        """Initialize Dune Analytics handlers"""
        self.market_service = market_service
        self.dune_service = market_service.dune_service
        logger.info("Dune Analytics handlers initialized")
    
    def register_handlers(self, application):
        """Register all Dune Analytics handlers"""
        # Command handlers
        application.add_handler(CommandHandler("dexdata", self.handle_dex_data))
        application.add_handler(CommandHandler("sonictvl", self.handle_sonic_tvl))
        application.add_handler(CommandHandler("sonicmetrics", self.handle_sonic_metrics))
        application.add_handler(CommandHandler("marketdata", self.handle_market_data))
        
        # Callback query handlers
        application.add_handler(CallbackQueryHandler(self.handle_dex_callback, pattern="^dex:"))
        
        logger.info("Dune Analytics handlers registered")
    
    async def handle_dex_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler for /dexdata command
        
        Usage:
        /dexdata [dex_name]
        
        Examples:
        /dexdata shadow
        /dexdata sonic
        /dexdata metro
        /dexdata beets
        /dexdata (for all DEXes)
        """
        try:
            # Parse arguments
            args = context.args
            dex_name = args[0].lower() if args else None
            
            # Validate dex_name if provided
            valid_dexes = ["shadow", "sonic", "metro", "beets"]
            if dex_name and dex_name not in valid_dexes:
                await update.message.reply_text(
                    f"Invalid DEX name. Please use one of: {', '.join(valid_dexes)}"
                )
                return
            
            # Show "typing" action
            await update.message.chat.send_action(action="typing")
            
            # Get DEX data
            dex_data = await self.market_service.get_dex_data(dex_name)
            
            if not dex_data:
                await update.message.reply_text("No DEX data available")
                return
            
            if dex_name:
                # Specific DEX data
                dex_info = dex_data.get(dex_name, {})
                if not dex_info:
                    await update.message.reply_text(f"No data available for {dex_name}")
                    return
                
                # Build message
                message = f"📊 <b>{dex_name.upper()} DEX Data</b>\n\n"
                
                # Add data type summaries
                for data_type, records in dex_info.items():
                    record_count = len(records)
                    message += f"<b>{data_type.replace('_', ' ').title()}</b>: {record_count} records\n"
                
                # Add sample for the first data type if available
                if dex_info:
                    first_data_type = next(iter(dex_info))
                    records = dex_info[first_data_type]
                    if records:
                        message += f"\n<b>Sample {first_data_type.replace('_', ' ').title()}</b>:\n"
                        record = records[0]
                        for key, value in list(record.items())[:5]:  # Show first 5 fields
                            message += f"- {key}: {value}\n"
                
                await update.message.reply_text(message, parse_mode="HTML")
            else:
                # Summary of all DEXes with keyboard
                message = "📊 <b>DEX Data Available</b>\n\n"
                message += "Select a DEX to view detailed data:"
                
                # Create inline keyboard
                keyboard = []
                for dex in valid_dexes:
                    if dex in dex_data:
                        data_types = [f"{data_type}: {len(records)} records" for data_type, records in dex_data[dex].items()]
                        keyboard.append([InlineKeyboardButton(
                            f"{dex.upper()} ({len(data_types)} data types)",
                            callback_data=f"dex:{dex}"
                        )])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="HTML")
        
        except Exception as e:
            logger.error(f"Error handling dex_data command: {str(e)}")
            await update.message.reply_text(f"Error retrieving DEX data: {str(e)}")
    
    async def handle_dex_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callbacks from DEX data keyboard"""
        query = update.callback_query
        await query.answer()
        
        try:
            # Parse callback data
            data = query.data.split(":")
            if len(data) != 2:
                await query.edit_message_text("Invalid callback data")
                return
            
            _, dex_name = data
            
            # Show "typing" action
            await query.message.chat.send_action(action="typing")
            
            # Get DEX data
            dex_data = await self.market_service.get_dex_data(dex_name)
            
            if not dex_data or dex_name not in dex_data:
                await query.edit_message_text(f"No data available for {dex_name}")
                return
            
            # Get DEX info
            dex_info = dex_data[dex_name]
            
            # Build message
            message = f"📊 <b>{dex_name.upper()} DEX Data</b>\n\n"
            
            # Add data type summaries with samples
            for data_type, records in dex_info.items():
                record_count = len(records)
                message += f"<b>{data_type.replace('_', ' ').title()}</b>: {record_count} records\n"
                
                # Add sample for this data type if available
                if records:
                    message += "Sample data:\n"
                    record = records[0]
                    for key, value in list(record.items())[:5]:  # Show first 5 fields
                        message += f"- {key}: {value}\n"
                    message += "\n"
            
            # Create back button
            keyboard = [[InlineKeyboardButton("◀️ Back to DEX List", callback_data="dex:list")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="HTML")
        
        except Exception as e:
            logger.error(f"Error handling dex callback: {str(e)}")
            await query.edit_message_text(f"Error retrieving DEX data: {str(e)}")
    
    async def handle_sonic_tvl(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler for /sonictvl command
        
        Usage:
        /sonictvl
        """
        try:
            # Show "typing" action
            await update.message.chat.send_action(action="typing")
            
            # Get Sonic TVL data
            sonic_tvl_df = await self.dune_service.get_sonic_tvl(force_refresh=True)
            
            if sonic_tvl_df is None or sonic_tvl_df.empty:
                await update.message.reply_text("No Sonic TVL data available")
                return
            
            # Create chart
            plt.figure(figsize=(10, 6))
            plt.plot(sonic_tvl_df['day'], sonic_tvl_df['tvl_usd'])
            plt.title('Sonic TVL Over Time')
            plt.xlabel('Date')
            plt.ylabel('TVL (USD)')
            plt.grid(True)
            plt.xticks(rotation=45)
            
            # Save chart to buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            
            # Current TVL
            current_tvl = sonic_tvl_df['tvl_usd'].iloc[-1] if not sonic_tvl_df.empty else "Unknown"
            caption = f"Sonic TVL: ${current_tvl:,.2f}" if isinstance(current_tvl, (int, float)) else f"Sonic TVL: {current_tvl}"
            
            # Send photo
            await update.message.reply_photo(photo=buf, caption=caption)
            
            # Close the plot to free memory
            plt.close()
        
        except Exception as e:
            logger.error(f"Error handling sonic_tvl command: {str(e)}")
            await update.message.reply_text(f"Error retrieving Sonic TVL data: {str(e)}")
    
    async def handle_sonic_metrics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler for /sonicmetrics command
        
        Usage:
        /sonicmetrics
        """
        try:
            # Show "typing" action
            await update.message.chat.send_action(action="typing")
            
            # Get Sonic data from different sources
            tasks = [
                self.dune_service.get_sonic_tvl(),
                self.dune_service.get_sonic_transactions(),
                self.dune_service.get_sonic_fees(),
                self.dune_service.get_sonic_max_tps()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check if we have valid results
            valid_data = False
            for result in results:
                if isinstance(result, pd.DataFrame) and not result.empty:
                    valid_data = True
                    break
            
            if not valid_data:
                await update.message.reply_text("No Sonic metrics data available")
                return
            
            # Process valid results
            tvl_df = results[0] if isinstance(results[0], pd.DataFrame) and not results[0].empty else None
            tx_df = results[1] if isinstance(results[1], pd.DataFrame) and not results[1].empty else None
            fees_df = results[2] if isinstance(results[2], pd.DataFrame) and not results[2].empty else None
            tps_df = results[3] if isinstance(results[3], pd.DataFrame) and not results[3].empty else None
            
            # Build message
            message = "📊 <b>Sonic Metrics Dashboard</b>\n\n"
            
            # Add TVL data
            if tvl_df is not None:
                current_tvl = tvl_df['tvl_usd'].iloc[-1] if not tvl_df.empty else "N/A"
                message += f"<b>Total Value Locked (TVL)</b>: ${current_tvl:,.2f}" if isinstance(current_tvl, (int, float)) else f"<b>Total Value Locked (TVL)</b>: {current_tvl}"
                message += "\n\n"
            
            # Add transaction data
            if tx_df is not None:
                total_tx = tx_df['transaction_count'].sum() if 'transaction_count' in tx_df.columns else "N/A"
                message += f"<b>Total Transactions</b>: {total_tx:,}" if isinstance(total_tx, (int, float)) else f"<b>Total Transactions</b>: {total_tx}"
                message += "\n\n"
            
            # Add fees data
            if fees_df is not None:
                total_fees = fees_df['fees_usd'].sum() if 'fees_usd' in fees_df.columns else "N/A"
                message += f"<b>Total Fees</b>: ${total_fees:,.2f}" if isinstance(total_fees, (int, float)) else f"<b>Total Fees</b>: {total_fees}"
                message += "\n\n"
            
            # Add TPS data
            if tps_df is not None:
                max_tps = tps_df['max_tps'].max() if 'max_tps' in tps_df.columns else "N/A"
                message += f"<b>Max TPS</b>: {max_tps:,.2f}" if isinstance(max_tps, (int, float)) else f"<b>Max TPS</b>: {max_tps}"
                message += "\n\n"
            
            message += "<i>Data from Dune Analytics</i>"
            
            await update.message.reply_text(message, parse_mode="HTML")
        
        except Exception as e:
            logger.error(f"Error handling sonic_metrics command: {str(e)}")
            await update.message.reply_text(f"Error retrieving Sonic metrics data: {str(e)}")
    
    async def handle_market_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler for /marketdata command
        
        Usage:
        /marketdata [token]
        
        Examples:
        /marketdata SONIC
        /marketdata ETH
        /marketdata BTC
        """
        try:
            # Parse arguments
            args = context.args
            token = args[0].upper() if args else "SONIC"
            
            # Show "typing" action
            await update.message.chat.send_action(action="typing")
            
            # Get token info from market service
            token_info = await self.market_service.get_token_info(token)
            
            if not token_info or "error" in token_info:
                await update.message.reply_text(f"No market data available for {token}")
                return
            
            # Build message
            message = f"📊 <b>{token} Market Data</b>\n\n"
            
            # Add token metrics
            metrics = token_info.get("metrics", {})
            price = metrics.get("price")
            if price:
                message += f"<b>Price</b>: ${price:,.4f}\n\n"
            else:
                message += "<b>Price</b>: Unknown\n\n"
            
            # Add sentiment analysis
            sentiment = token_info.get("sentiment", {})
            if sentiment:
                sentiment_text = sentiment.get('sentiment', 'neutral').title()
                confidence = sentiment.get('confidence', 0) * 100
                
                emoji = "🟢" if sentiment_text == "Bullish" else "🔴" if sentiment_text == "Bearish" else "⚪"
                message += f"<b>Sentiment</b>: {emoji} {sentiment_text} ({confidence:.0f}% confidence)\n\n"
            
            # Add data from DexScreener
            dexscreener = metrics.get("dexscreener", {})
            if dexscreener:
                message += "<b>DexScreener Data</b>:\n"
                
                # Add price change if available
                price_change = dexscreener.get("priceChange", {})
                if price_change:
                    change_24h = price_change.get('h24', 0)
                    emoji = "🟢" if change_24h > 0 else "🔴" if change_24h < 0 else "⚪"
                    message += f"- 24h Change: {emoji} {change_24h:+.2f}%\n"
                
                # Add volume if available
                volume = dexscreener.get("volume", {})
                if volume:
                    message += f"- 24h Volume: ${volume.get('h24', 0):,.2f}\n"
                
                # Add liquidity if available
                liquidity = dexscreener.get("liquidity", {})
                if liquidity:
                    message += f"- Liquidity: ${liquidity.get('usd', 0):,.2f}\n"
                
                message += "\n"
            
            # Add Dune data if available
            dune_data = metrics.get("dune", {})
            if dune_data:
                message += "<b>Dune Analytics Data</b>: Available\n\n"
            
            message += "<i>Data from DexScreener and Dune Analytics</i>"
            
            await update.message.reply_text(message, parse_mode="HTML")
        
        except Exception as e:
            logger.error(f"Error handling market_data command: {str(e)}")
            await update.message.reply_text(f"Error retrieving market data: {str(e)}")