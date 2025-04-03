"""Technical indicators for trading strategy"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

def calculate_moving_averages(data: pd.DataFrame, short_period: int = 10, long_period: int = 50) -> Tuple[pd.Series, pd.Series]:
    """Calculate short and long-term moving averages"""
    try:
        short_ma = data['Close'].rolling(window=short_period).mean()
        long_ma = data['Close'].rolling(window=long_period).mean()
        return short_ma, long_ma
    except Exception as e:
        logger.error(f"Error calculating moving averages: {str(e)}")
        return pd.Series(), pd.Series()

def calculate_rsi(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index"""
    try:
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    except Exception as e:
        logger.error(f"Error calculating RSI: {str(e)}")
        return pd.Series()

def analyze_market_signals(price_data: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze market data using multiple technical indicators
    Returns a dictionary with trading signals and analysis
    """
    try:
        # Calculate indicators
        short_ma, long_ma = calculate_moving_averages(price_data)
        rsi = calculate_rsi(price_data)
        
        # Get latest values
        current_short_ma = short_ma.iloc[-1]
        current_long_ma = long_ma.iloc[-1]
        current_rsi = rsi.iloc[-1]
        
        # Previous values for crossover detection
        prev_short_ma = short_ma.iloc[-2]
        prev_long_ma = long_ma.iloc[-2]
        prev_rsi = rsi.iloc[-2]
        
        # Detect signals
        bullish_ma_crossover = prev_short_ma <= prev_long_ma and current_short_ma > current_long_ma
        bearish_ma_crossover = prev_short_ma >= prev_long_ma and current_short_ma < current_long_ma
        
        # RSI signals
        oversold = current_rsi < 30 and current_rsi > prev_rsi  # Oversold and turning up
        overbought = current_rsi > 70 and current_rsi < prev_rsi  # Overbought and turning down
        
        # Combine signals
        signal = "buy" if (bullish_ma_crossover and current_rsi < 40) else \
                "sell" if (bearish_ma_crossover and current_rsi > 60) else \
                "neutral"
        
        # Calculate volatility
        volatility = price_data['Close'].pct_change().std() * np.sqrt(252)  # Annualized
        
        return {
            'signal': signal,
            'confidence': 0.8 if (bullish_ma_crossover and oversold) or (bearish_ma_crossover and overbought) else 0.6,
            'rsi': current_rsi,
            'short_ma': current_short_ma,
            'long_ma': current_long_ma,
            'volatility': volatility,
            'market_trend': "bullish" if current_short_ma > current_long_ma else "bearish",
            'analysis_time': pd.Timestamp.now()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing market signals: {str(e)}")
        return {
            'signal': 'error',
            'confidence': 0.0,
            'error': str(e)
        }

def load_historical_data(csv_path: str) -> Optional[pd.DataFrame]:
    """Load and preprocess historical price data"""
    try:
        df = pd.read_csv(csv_path)
        df['Date'] = pd.to_datetime(df['Start'])
        df.set_index('Date', inplace=True)
        return df
    except Exception as e:
        logger.error(f"Error loading historical data: {str(e)}")
        return None
