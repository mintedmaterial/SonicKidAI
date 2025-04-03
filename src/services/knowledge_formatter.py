"""
Knowledge formatting service for the ZerePy framework
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class KnowledgeFormatter:
    """Service for formatting knowledge data"""

    def __init__(self):
        logger.info("Initialized knowledge formatter service")

    def format_market_data(self, market_data: Dict[str, Any]) -> str:
        """Format market data for processing"""
        try:
            logger.debug(f"Received market data to format: {market_data}")

            if not isinstance(market_data, dict):
                logger.error(f"Invalid market data type: {type(market_data)}")
                return "Error: Invalid market data format"

            # Extract data if wrapped in a data field
            if "data" in market_data:
                market_data = market_data["data"]

            formatted_data = {
                "pairs": [],
                "summary": {}
            }

            # Process pair data
            if "pairs" in market_data:
                for pair in market_data["pairs"]:
                    formatted_pair = self._format_pair_data(pair)
                    if formatted_pair:
                        formatted_data["pairs"].append(formatted_pair)

            # Calculate summary metrics
            formatted_data["summary"] = self._calculate_market_summary(
                formatted_data["pairs"]
            )

            # Convert to human-readable format for TopHat
            formatted_text = self._convert_to_text(formatted_data, "Market Data Update")
            logger.debug(f"Formatted market data: {formatted_text}")
            return formatted_text

        except Exception as e:
            logger.error(f"Error formatting market data: {str(e)}", exc_info=True)
            return "Error formatting market data"

    def format_trading_signals(self, signals: Dict[str, Any]) -> str:
        """Format trading signals data with enhanced validation"""
        try:
            logger.debug(f"Received trading signals to format: {signals}")

            if not isinstance(signals, dict):
                error_msg = f"Invalid trading signals type: {type(signals)}"
                logger.error(error_msg)
                return f"Error: {error_msg}"

            # Extract data if wrapped in a data field
            if "data" in signals:
                signals = signals["data"]

            # Required fields with type validation
            required_fields = {
                "asset": str,
                "signal_type": str,
                "confidence": float,
                "timeframe": str,
                "entry_price": float,
                "stop_loss": float,
                "take_profit": float
            }

            # Validate required fields
            for field, field_type in required_fields.items():
                if field not in signals:
                    error_msg = f"Missing required field: {field}"
                    logger.error(error_msg)
                    return f"Error: {error_msg}"

                try:
                    if field_type == float:
                        signals[field] = float(signals[field])
                except (TypeError, ValueError):
                    error_msg = f"Invalid {field} value: {signals.get(field)}"
                    logger.error(error_msg)
                    return f"Error: {error_msg}"

            # Format the trading signal with additional context
            formatted_data = {
                "asset": signals["asset"],
                "signal_type": signals["signal_type"].upper(),
                "confidence": float(signals["confidence"]),
                "timeframe": signals["timeframe"],
                "entry": float(signals["entry_price"]),
                "stop_loss": float(signals["stop_loss"]),
                "take_profit": float(signals["take_profit"]),
                "risk_reward_ratio": self._calculate_risk_reward(
                    entry=signals["entry_price"],
                    stop=signals["stop_loss"],
                    target=signals["take_profit"]
                ),
                "indicators": self._format_indicators(signals.get("indicators", {})),
                "metadata": signals.get("metadata", {}),
                "timestamp": signals.get("timestamp", datetime.utcnow().isoformat())
            }

            # Convert to human-readable format for TopHat
            formatted_text = self._convert_to_text(formatted_data, "Trading Signal Update")
            logger.debug(f"Formatted trading signals: {formatted_text}")
            return formatted_text

        except Exception as e:
            logger.error(f"Error formatting trading signals: {str(e)}", exc_info=True)
            return f"Error formatting trading signals: {str(e)}"

    def _format_indicators(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Format technical indicators with validation"""
        try:
            formatted_indicators = {}

            # Standard indicator mappings
            indicator_types = {
                "RSI": (int, float),
                "MACD": str,
                "MA_200": str,
                "Volume": str,
                "Trend": str,
                "Support": (int, float),
                "Resistance": (int, float)
            }

            for indicator, value in indicators.items():
                if indicator in indicator_types:
                    expected_type = indicator_types[indicator]
                    if isinstance(expected_type, tuple):
                        if not isinstance(value, expected_type):
                            try:
                                value = float(value)
                            except (TypeError, ValueError):
                                logger.warning(f"Invalid {indicator} value: {value}")
                                continue
                    elif not isinstance(value, expected_type):
                        logger.warning(f"Invalid {indicator} value type: {type(value)}")
                        continue

                    formatted_indicators[indicator] = value

            return formatted_indicators

        except Exception as e:
            logger.error(f"Error formatting indicators: {str(e)}")
            return {}

    def _calculate_risk_reward(self, entry: float, stop: float, target: float) -> float:
        """Calculate risk-reward ratio for the trade"""
        try:
            risk = abs(entry - stop)
            reward = abs(target - entry)
            return round(reward / risk, 2) if risk != 0 else 0.0
        except Exception as e:
            logger.error(f"Error calculating risk-reward ratio: {str(e)}")
            return 0.0

    def _convert_to_text(self, data: Dict[str, Any], title: str) -> str:
        """Convert formatted data to human-readable text for TopHat"""
        try:
            current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            text_parts = [
                f"# {title}",
                f"Updated: {current_time}\n"
            ]

            if "pairs" in data:
                # Format market data
                text_parts.append("## Market Overview")
                if data["summary"]:
                    summary = data["summary"]
                    text_parts.extend([
                        f"Total Pairs: {summary.get('total_pairs', 0)}",
                        f"24h Volume: ${summary.get('total_volume_24h', 0):,.2f}",
                        f"Total Liquidity: ${summary.get('total_liquidity', 0):,.2f}",
                        f"Average Price Change: {summary.get('average_price_change', 0):.2f}%\n"
                    ])

                if data["pairs"]:
                    text_parts.append("## Notable Pairs")
                    for pair in data["pairs"]:
                        text_parts.extend([
                            f"- {pair['chain']} {pair['pair']}:",
                            f"  Price: ${pair['price']:,.2f}",
                            f"  24h Change: {pair['priceChange24h']}%",
                            f"  Volume: ${pair['volume24h']:,.2f}",
                            f"  Liquidity: ${pair['liquidity']:,.2f}\n"
                        ])

            elif "signal_type" in data:
                # Format trading signals
                text_parts.extend([
                    "## Signal Details",
                    f"Asset: {data['asset']}",
                    f"Type: {data['signal_type']}",
                    f"Confidence: {data['confidence']*100:.1f}%",
                    f"Timeframe: {data['timeframe']}",
                    f"Risk/Reward: {data['risk_reward_ratio']}",
                    f"\nEntry: ${data['entry']:,.2f}",
                    f"Stop Loss: ${data['stop_loss']:,.2f}",
                    f"Take Profit: ${data['take_profit']:,.2f}\n"
                ])

                if data.get("indicators"):
                    text_parts.append("## Technical Indicators")
                    for indicator, value in data["indicators"].items():
                        text_parts.append(f"- {indicator}: {value}")

                if data.get("metadata"):
                    text_parts.append("\n## Additional Information")
                    for key, value in data["metadata"].items():
                        text_parts.append(f"- {key.replace('_', ' ').title()}: {value}")

            formatted_text = "\n".join(text_parts)
            logger.debug(f"Converted to text format: {formatted_text}")
            return formatted_text

        except Exception as e:
            logger.error(f"Error converting to text: {str(e)}")
            return f"Error formatting {title.lower()}"

    def _format_pair_data(self, pair: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Format individual pair data"""
        try:
            formatted_pair = {
                "chain": pair.get("chainId", "").upper(),
                "pair": f"{pair.get('baseToken', {}).get('symbol', '')}/{pair.get('quoteToken', {}).get('symbol', '')}",
                "price": float(pair.get("priceUsd", 0)),
                "priceChange24h": pair.get("priceChange", {}).get("h24", 0),
                "volume24h": pair.get("volume", {}).get("h24", 0),
                "liquidity": pair.get("liquidity", {}).get("usd", 0)
            }
            logger.debug(f"Formatted pair data: {formatted_pair}")
            return formatted_pair

        except Exception as e:
            logger.error(f"Error formatting pair data: {str(e)}")
            return None

    def _calculate_market_summary(self, pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary metrics from pair data"""
        try:
            if not pairs:
                return {}

            total_volume = sum(pair.get("volume24h", 0) for pair in pairs)
            total_liquidity = sum(pair.get("liquidity", 0) for pair in pairs)

            summary = {
                "total_pairs": len(pairs),
                "total_volume_24h": total_volume,
                "total_liquidity": total_liquidity,
                "average_price_change": sum(pair.get("priceChange24h", 0) for pair in pairs) / len(pairs) if pairs else 0
            }

            logger.debug(f"Calculated market summary: {summary}")
            return summary

        except Exception as e:
            logger.error(f"Error calculating market summary: {str(e)}")
            return {}