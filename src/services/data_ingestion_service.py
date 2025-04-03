"""
Data ingestion service for managing price feeds, trading data, and market sentiment
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import json
from src.connections.tophat import TopHatConnection
from src.services.knowledge_formatter import KnowledgeFormatter

logger = logging.getLogger(__name__)

class DataIngestionService:
    """Service for ingesting and managing trading data"""

    def __init__(self, db_connection, tophat_connection: Optional[TopHatConnection] = None):
        self.db = db_connection
        self.tophat = tophat_connection
        self.knowledge_formatter = KnowledgeFormatter()
        self.retention_period = timedelta(days=30)  # Set 1-month retention period
        logger.info("Initialized data ingestion service")

    async def ingest_price_feed(self, data: Dict[str, Any]) -> bool:
        """Ingest price feed data into database and TopHat"""
        try:
            logger.debug(f"Ingesting price feed data: {data}")

            # Insert into database
            with self.db.cursor() as cursor:
                query = """
                    INSERT INTO price_feed_data 
                    (symbol, price, source, chain_id, volume_24h, price_change_24h, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                # Extract the first pair's data for database storage
                pair_data = data["pairs"][0] if data.get("pairs") else {}
                cursor.execute(
                    query,
                    (
                        f"{pair_data.get('baseToken', {}).get('symbol', '')}/{pair_data.get('quoteToken', {}).get('symbol', '')}",
                        float(pair_data.get("priceUsd", 0)),
                        data.get("source", "unknown"),
                        pair_data.get("chainId"),
                        pair_data.get("volume", {}).get("h24"),
                        pair_data.get("priceChange", {}).get("h24"),
                        json.dumps(pair_data.get("metadata", {}))
                    )
                )
                self.db.commit()
                logger.info("Successfully stored price feed data in database")

            # Update TopHat knowledge if configured
            if self.tophat:
                # Format data for TopHat
                formatted_data = self.knowledge_formatter.format_market_data(data)
                if formatted_data and not formatted_data.startswith("Error"):
                    await self.tophat.update_market_knowledge({
                        "type": "price_feed",
                        "data": data
                    })
                    logger.info("Successfully updated TopHat knowledge with price feed data")
                else:
                    logger.error(f"Failed to format price feed data: {formatted_data}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error ingesting price feed data: {str(e)}", exc_info=True)
            return False

    async def ingest_trading_activity(self, activity: Dict[str, Any]) -> bool:
        """Ingest trading activity and signals data"""
        try:
            logger.debug(f"Ingesting trading activity: {activity}")

            # Determine if this is a trading signal or activity
            if "signal_type" in activity:
                # This is a trading signal
                with self.db.cursor() as cursor:
                    query = """
                        INSERT INTO trading_activity 
                        (asset, signal_type, confidence, timeframe, entry_price, 
                        stop_loss, take_profit, indicators, status, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(
                        query,
                        (
                            activity["asset"],
                            activity["signal_type"],
                            activity["confidence"],
                            activity["timeframe"],
                            activity["entry_price"],
                            activity["stop_loss"],
                            activity["take_profit"],
                            json.dumps(activity.get("indicators", {})),
                            "active",
                            json.dumps({})
                        )
                    )
                    logger.info("Successfully stored trading signal in database")
            else:
                # This is a trading activity
                with self.db.cursor() as cursor:
                    query = """
                        INSERT INTO trading_activity 
                        (action_type, from_token, to_token, from_amount, to_amount,
                        chain_id, platform, tx_hash, status, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(
                        query,
                        (
                            activity.get("actionType"),
                            activity.get("fromToken"),
                            activity.get("toToken"),
                            activity.get("fromAmount"),
                            activity.get("toAmount"),
                            activity.get("chainId"),
                            activity.get("platform"),
                            activity.get("txHash"),
                            activity.get("status", "pending"),
                            json.dumps(activity.get("metadata", {}))
                        )
                    )
                    logger.info("Successfully stored trading activity in database")

            self.db.commit()

            # Update TopHat knowledge if configured
            if self.tophat:
                formatted_signals = self.knowledge_formatter.format_trading_signals(activity)
                if formatted_signals and not formatted_signals.startswith("Error"):
                    await self.tophat.update_trading_signals(activity)
                    logger.info("Successfully updated TopHat knowledge with trading data")
                else:
                    logger.error(f"Failed to format trading signals: {formatted_signals}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error ingesting trading activity: {str(e)}", exc_info=True)
            return False

    async def ingest_market_sentiment(self, sentiment: Dict[str, Any]) -> bool:
        """Ingest market sentiment data"""
        try:
            logger.debug(f"Ingesting market sentiment: {sentiment}")

            # Insert into database
            with self.db.cursor() as cursor:
                query = """
                    INSERT INTO market_sentiment 
                    (source, sentiment, score, symbol, content, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(
                    query,
                    (
                        sentiment.get("source", "unknown"),
                        sentiment["sentiment"],
                        sentiment.get("score"),
                        sentiment.get("pairs", [{}])[0].get("baseToken", {}).get("symbol"),
                        sentiment["content"],
                        json.dumps(sentiment.get("metadata", {}))
                    )
                )
                self.db.commit()
                logger.info("Successfully stored market sentiment in database")

            # Update TopHat knowledge if configured
            if self.tophat:
                formatted_data = self.knowledge_formatter.format_market_data({
                    "type": "market_sentiment",
                    "data": sentiment
                })
                if formatted_data and not formatted_data.startswith("Error"):
                    await self.tophat.update_market_knowledge({
                        "type": "market_sentiment",
                        "data": sentiment
                    })
                    logger.info("Successfully updated TopHat knowledge with sentiment data")
                else:
                    logger.error(f"Failed to format market sentiment: {formatted_data}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error ingesting market sentiment: {str(e)}", exc_info=True)
            return False

    async def cleanup_old_data(self):
        """Remove data older than retention period"""
        try:
            cutoff_date = datetime.utcnow() - self.retention_period

            with self.db.cursor() as cursor:
                # Clean price feed data
                cursor.execute(
                    "DELETE FROM price_feed_data WHERE timestamp < %s",
                    (cutoff_date,)
                )

                # Clean trading activity
                cursor.execute(
                    "DELETE FROM trading_activity WHERE timestamp < %s",
                    (cutoff_date,)
                )

                # Clean market sentiment
                cursor.execute(
                    "DELETE FROM market_sentiment WHERE timestamp < %s",
                    (cutoff_date,)
                )

                self.db.commit()

            logger.info(f"Successfully cleaned up data older than {cutoff_date}")
            return True

        except Exception as e:
            logger.error(f"Error cleaning up old data: {str(e)}")
            return False

    async def run_cleanup_job(self):
        """Run periodic cleanup job"""
        while True:
            try:
                await self.cleanup_old_data()
                # Run cleanup every 24 hours
                await asyncio.sleep(86400)
            except Exception as e:
                logger.error(f"Error in cleanup job: {str(e)}")
                await asyncio.sleep(3600)  # Retry after 1 hour on error