"""Market visualization service with hyperbolic candlestick charts"""
import logging
import os
from typing import Dict, Any, Optional, List
import io
import base64
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from matplotlib.ticker import FixedLocator

logger = logging.getLogger(__name__)

class MarketVisualizationService:
    """Service for generating hyperbolic market visualization charts"""

    def __init__(self):
        """Initialize visualization with hyperbolic transforms"""
        self.fig_size = (12, 8)  # Wider figure for better visibility
        self.dpi = 100
        plt.style.use('dark_background')
        logger.info("Hyperbolic visualization service initialized")

    def _generate_synthetic_data(self, current_price: float, change_24h: float) -> List[Dict[str, Any]]:
        """Generate synthetic OHLC data with realistic price movements"""
        historical_data = []
        base_price = current_price / (1 + change_24h/100)
        time_now = datetime.now()

        # Configure trend parameters
        volatility = abs(change_24h) * 0.3  # Higher volatility for more movement
        trend_per_hour = change_24h / 24  # Distribute trend across hours
        last_price = base_price

        logger.info(f"Generating synthetic data - Base Price: ${base_price:.2f}, Target: ${current_price:.2f}")
        logger.info(f"24h Change: {change_24h:.2f}%, Volatility: {volatility:.2f}%")

        # Generate price movement with random walks and trend
        for i in range(24):  # 24 hour data
            time_point = time_now - timedelta(hours=23-i)

            # Add some randomness while maintaining overall trend
            noise = np.random.normal(0, volatility/2)  # Random noise
            trend_component = trend_per_hour + noise

            # Calculate next price with momentum
            momentum = 0.3 * (i/23)  # Increasing momentum factor
            if change_24h > 0:
                # For uptrend, limit downside but allow higher upside
                price_change = max(trend_component * (1 + momentum), -volatility/2)
            else:
                # For downtrend, limit upside but allow lower downside
                price_change = min(trend_component * (1 + momentum), volatility/2)

            # Update current price with exponential smoothing
            current_price = last_price * (1 + price_change/100)

            # Generate OHLC with micro-volatility
            micro_vol = volatility * 0.15  # Increased micro-volatility
            high = max(current_price, last_price) * (1 + abs(np.random.normal(0, micro_vol/100)))
            low = min(current_price, last_price) * (1 - abs(np.random.normal(0, micro_vol/100)))

            # Set open/close preserving trend direction
            if i == 0:
                open_price = base_price
            else:
                # Use previous close as open
                open_price = last_price
            close = current_price

            # Log candle data for debugging
            logger.debug(f"Hour {i}: Open=${open_price:.2f}, High=${high:.2f}, Low=${low:.2f}, Close=${close:.2f}")
            logger.debug(f"Price Change: {price_change:.2f}%, Trend: {trend_component:.2f}%, Noise: {noise:.2f}%")

            # Store candle data
            historical_data.append({
                'timestamp': time_point,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close
            })

            last_price = current_price

        # Verify final price matches target
        final_change = ((current_price - base_price) / base_price) * 100
        logger.info(f"Generated data - Final Price: ${current_price:.2f}, Actual Change: {final_change:.2f}%")

        return historical_data

    def _hyperbolic_transform(self, value: float) -> float:
        """Apply bounded hyperbolic transformation"""
        try:
            safe_value = max(abs(value), 1e-10)
            transformed = np.arcsinh(safe_value / 1e3) / np.log(2)
            return max(min(transformed, 5.0), -5.0)
        except Exception as e:
            logger.error(f"Error in hyperbolic transform: {str(e)}")
            return 0.0

    def _create_candlestick(self, ax: plt.Axes, candle_data: Dict[str, float], x_pos: int, width: float = 0.8) -> None:
        """Create a single candlestick with enhanced styling"""
        try:
            # Transform OHLC values
            open_price = self._hyperbolic_transform(candle_data['open'])
            close_price = self._hyperbolic_transform(candle_data['close'])
            high_price = self._hyperbolic_transform(candle_data['high'])
            low_price = self._hyperbolic_transform(candle_data['low'])

            # Determine candle type and color
            is_bullish = close_price >= open_price
            color = '#00ff00' if is_bullish else '#ff0000'

            # Enhanced styling for better visibility
            body_height = abs(open_price - close_price)
            body_bottom = min(open_price, close_price)

            # Draw candlestick body with gradient effect
            rect = Rectangle(
                (x_pos - width/2, body_bottom),
                width,
                body_height,
                facecolor=color,
                edgecolor=color,
                alpha=0.8,
                linewidth=1
            )
            ax.add_patch(rect)

            # Draw wicks with enhanced styling
            wick_line = Line2D(
                [x_pos, x_pos],
                [low_price, high_price],
                color=color,
                alpha=0.8,
                linewidth=1.5,
                solid_capstyle='round'
            )
            ax.add_line(wick_line)

        except Exception as e:
            logger.error(f"Error creating candlestick: {str(e)}")

    async def generate_chart(self, market_data: Dict[str, Any]) -> Optional[str]:
        """Generate hyperbolic candlestick chart visualization"""
        try:
            # Generate synthetic data if not provided
            historical_data = market_data.get('historical_data')
            if not historical_data:
                current_price = market_data.get('price', 0)
                change_24h = market_data.get('change_24h', 0)
                historical_data = self._generate_synthetic_data(current_price, change_24h)

            # Create figure with enhanced styling
            plt.figure(figsize=self.fig_size, dpi=self.dpi)
            ax = plt.gca()

            # Plot candlesticks
            for i, candle in enumerate(historical_data):
                self._create_candlestick(ax, candle, i)

            # Style the chart
            ax.set_facecolor('#1a1a1a')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(True, linestyle='--', alpha=0.2, color='#333333')
            ax.set_ylim(-5.5, 5.5)

            # X-axis formatting
            x_ticks = range(len(historical_data))
            x_labels = [candle['timestamp'].strftime('%H:%M') for candle in historical_data]
            plt.xticks(x_ticks[::4], x_labels[::4], rotation=45)

            # Y-axis hyperbolic scale formatting
            y_ticks = np.linspace(-5, 5, 11)
            ax.yaxis.set_major_locator(FixedLocator(y_ticks))
            y_labels = [f'${np.sinh(y * np.log(2)) * 1e3:,.2f}' for y in y_ticks]
            ax.set_yticklabels(y_labels)

            # Add data source info
            data_source = market_data.get('source', 'market').upper()
            source_text = f"Data Source: {data_source}"
            plt.figtext(0.98, 0.02, source_text, color='white', alpha=0.7,
                      ha='right', va='bottom', bbox=dict(facecolor='black', alpha=0.7, boxstyle='round'))

            # Set title and labels
            token_symbol = market_data.get('token', 'Unknown')
            title = f'{token_symbol} Price Action (Hyperbolic Scale)'
            if market_data.get('timeframe'):
                title += f" - {market_data['timeframe'].upper()}"
            plt.title(title, color='white', pad=20, fontsize=14, fontweight='bold')
            plt.ylabel('Price (USD)', color='white', fontsize=12)

            # Add market metrics
            metrics_text = (
                f"Current: ${market_data.get('price', 0):,.2f}\n"
                f"24h Change: {market_data.get('change_24h', 0):+.2f}%\n"
                f"Volume: ${market_data.get('volume24h', 0)/1e6:.1f}M\n"
                f"Liquidity: ${market_data.get('totalLiquidity', 0)/1e6:.1f}M"
            )
            plt.figtext(0.02, 0.02, metrics_text, color='white',
                      bbox=dict(facecolor='black', alpha=0.7, boxstyle='round'))

            # Use fixed spacing
            plt.tight_layout()

            # Save to buffer with high quality
            buf = io.BytesIO()
            plt.savefig(buf, format='png',
                      facecolor='#1a1a1a',
                      edgecolor='none',
                      bbox_inches='tight',
                      dpi=self.dpi)
            buf.seek(0)
            plt.close()

            return base64.b64encode(buf.getvalue()).decode()

        except Exception as e:
            logger.error(f"Error generating chart: {str(e)}")
            return None

    async def enhance_chart(self, chart_img: str, prompt: str) -> Optional[str]:
        """Add technical indicators to chart"""
        try:
            # For now, return the original chart
            # Future enhancement: Add technical indicators
            return chart_img

        except Exception as e:
            logger.error(f"Error enhancing chart: {str(e)}")
            return None