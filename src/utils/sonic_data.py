"""
Utility module for fetching Sonic chain and price data using enhanced DexScreener service
"""
import logging
import time
import requests
from typing import Dict, Any, Optional, List
from src.services.dexscreener_service import DexScreenerService
from src.services.market_data import MarketDataService
from src.services.huggingface_service import HuggingFaceService

logger = logging.getLogger(__name__)

# Initialize services
dex_service = DexScreenerService()
market_service = MarketDataService()
huggingface_service = HuggingFaceService()

# Constants
SONIC_CHAIN_ID = '146'
DEFILLAMA_TVL_API = "https://api.llama.fi/protocols"

# Chain ID mappings
CHAIN_IDS = {
    'sonic': '146',
    'ethereum': '1',
    'base': '8453',
    'arbitrum': '42161'
}

def format_number(value: Any) -> str:
    """Format number with proper decimal places and suffixes"""
    try:
        if isinstance(value, (int, float)):
            if value > 1_000_000_000:
                return f"{value/1_000_000_000:.2f}B"
            elif value > 1_000_000:
                return f"{value/1_000_000:.2f}M"
            elif value > 1_000:
                return f"{value/1_000:.2f}K"
            return f"{value:.4f}"
        return str(value)
    except:
        return 'N/A'

async def fetch_pairs_by_token(chain_id: str, token_query: str, limit: int = 6) -> Optional[List[Dict]]:
    """Fetch top pairs by token symbol/name search with sentiment analysis"""
    try:
        logger.info(f"Fetching pairs for {token_query} on chain {chain_id}")
        pairs = await market_service.get_dexscreener_search(chain_id, token_query)

        if pairs and isinstance(pairs, list):
            pairs = pairs[:limit]
            logger.info(f"Found {len(pairs)} pairs for {token_query}")

            # Add BERT-based sentiment analysis for each pair
            for pair in pairs:
                try:
                    base_token = pair.get('baseToken', {}).get('symbol', '')
                    quote_token = pair.get('quoteToken', {}).get('symbol', '')
                    volume = format_number(pair.get('volume_24h', 0))
                    price_change = format_number(pair.get('priceChange24h', 0))

                    description = f"{base_token}/{quote_token} trading pair shows {volume} 24h volume with {price_change}% price change"
                    sentiment = await huggingface_service.analyze_market_sentiment(description)
                    pair['sentiment'] = sentiment

                    logger.debug(f"Added sentiment analysis for {base_token}/{quote_token}: {sentiment}")
                except Exception as e:
                    logger.error(f"Error analyzing sentiment: {str(e)}")
                    pair['sentiment'] = None

            return pairs

        logger.debug(f"No pairs found for {token_query}")
        return None

    except Exception as e:
        logger.error(f"Error fetching pairs by token: {str(e)}")
        return None

async def fetch_pair_by_address(chain_id: str, pair_address: str) -> Optional[Dict]:
    """Fetch specific pair data with sentiment analysis"""
    try:
        chain_id = CHAIN_IDS.get(chain_id.lower(), chain_id)
        if not chain_id:
            logger.error(f"Unsupported chain: {chain_id}")
            return None

        logger.info(f"Fetching pair data for {pair_address} on {chain_id}")
        pair = await market_service.get_token_data(pair_address, chain_id)

        if pair:
            enhanced_pair = {
                'chainId': chain_id,
                'dexId': pair.get('dexId', 'Unknown'),
                'baseToken': pair.get('baseToken', {}),
                'quoteToken': pair.get('quoteToken', {}),
                'priceUsd': pair.get('price', 0),
                'priceChange': pair.get('priceChange', {}),
                'volume': pair.get('volume_24h', 0),
                'liquidity': pair.get('liquidity', 0),
                'txns': pair.get('txns', {}),
                'marketCap': pair.get('marketCap', 0),
                'fdv': pair.get('fdv', 0),
                'pairCreatedAt': pair.get('pairCreatedAt', 0),
            }

            # Add BERT-based sentiment analysis
            try:
                base_symbol = enhanced_pair['baseToken'].get('symbol', '')
                quote_symbol = enhanced_pair['quoteToken'].get('symbol', '')
                volume = format_number(enhanced_pair['volume'])
                liquidity = format_number(enhanced_pair['liquidity'])
                description = f"{base_symbol}/{quote_symbol} trading pair with ${volume} volume and ${liquidity} liquidity"

                sentiment = await huggingface_service.analyze_market_sentiment(description)
                enhanced_pair['sentiment'] = sentiment
                logger.debug(f"Added sentiment analysis for {base_symbol}/{quote_symbol}: {sentiment}")
            except Exception as e:
                logger.error(f"Error analyzing sentiment: {str(e)}")
                enhanced_pair['sentiment'] = None

            logger.info(f"Found pair data for {pair_address}")
            return enhanced_pair

        logger.warning(f"No pair data found for {pair_address}")
        return None

    except Exception as e:
        logger.error(f"Error fetching pair by address: {str(e)}")
        return None

def format_pair_data(pair: Dict) -> str:
    """Format pair data with sentiment indicators"""
    try:
        symbol = f"{pair['baseToken']['symbol']}/{pair['quoteToken']['symbol']}"
        price = float(pair.get('priceUsd', 0))
        volume_24h = pair.get('volume', 0)
        liquidity = pair.get('liquidity', 0)
        sentiment = pair.get('sentiment', {})

        # Use BERT sentiment for emoji indicator
        if sentiment:
            confidence = sentiment.get('confidence', 0)
            sentiment_type = sentiment.get('sentiment', 'neutral')
            if sentiment_type == 'bullish' and confidence > 80:
                sentiment_emoji = "🚀"  # Strong bullish
            elif sentiment_type == 'bullish':
                sentiment_emoji = "📈"  # Bullish
            elif sentiment_type == 'bearish' and confidence > 80:
                sentiment_emoji = "🔴"  # Strong bearish
            elif sentiment_type == 'bearish':
                sentiment_emoji = "📉"  # Bearish
            else:
                sentiment_emoji = "⚖️"  # Neutral
        else:
            sentiment_emoji = "⚪"

        formatted_data = (
            f"{sentiment_emoji} {symbol}\n"
            f"Price: ${format_number(price)}\n"
            f"Volume (24h): ${format_number(volume_24h)}\n"
            f"Liquidity: ${format_number(liquidity)}"
        )

        if sentiment:
            confidence = sentiment.get('confidence', 0)
            formatted_data += f"\nMarket Sentiment: {sentiment.get('sentiment', 'neutral')} ({format_number(confidence)}% confidence)"

        return formatted_data

    except Exception as e:
        logger.error(f"Error formatting pair data: {str(e)}")
        return "Error formatting pair data"

async def analyze_market_metrics(pair_data: Dict) -> Dict[str, Any]:
    """Analyze market metrics with BERT sentiment"""
    try:
        metrics = {
            'price': float(pair_data.get('priceUsd', 0)),
            'volume_24h': float(pair_data.get('volume', 0)),
            'liquidity': float(pair_data.get('liquidity', 0)),
            'price_change_24h': float(pair_data.get('priceChange', {}).get('h24', 0))
        }

        # Get BERT sentiment analysis
        description = (
            f"Trading pair shows ${format_number(metrics['price'])} price with "
            f"{format_number(metrics['price_change_24h'])}% 24h change. "
            f"Volume: ${format_number(metrics['volume_24h'])}, "
            f"Liquidity: ${format_number(metrics['liquidity'])}"
        )

        sentiment = await huggingface_service.analyze_market_sentiment(description)

        return {
            'metrics': metrics,
            'sentiment': sentiment,
            'momentum': 'bullish' if metrics['price_change_24h'] > 0 else 'bearish',
            'volatility': abs(metrics['price_change_24h']) > 5,
            'liquidity_ratio': metrics['volume_24h'] / max(metrics['liquidity'], 1)
        }

    except Exception as e:
        logger.error(f"Error analyzing market metrics: {str(e)}")
        return {}

async def get_market_summary(chain_id: str = 'sonic', limit: int = 5) -> str:
    """Get market summary with sentiment analysis"""
    try:
        pairs = await fetch_pairs_by_token(chain_id, "", limit)
        if not pairs:
            return "No market data available"

        summary_lines = []
        for pair in pairs:
            analysis = await analyze_market_metrics(pair)
            sentiment = analysis.get('sentiment', {})

            symbol = f"{pair['baseToken']['symbol']}/{pair['quoteToken']['symbol']}"
            price = float(pair.get('priceUsd', 0))
            sentiment_indicator = "🚀" if sentiment.get('sentiment') == 'bullish' and sentiment.get('confidence', 0) > 80 else "📈"

            summary_lines.append(
                f"{sentiment_indicator} {symbol}: ${format_number(price)} "
                f"({format_number(analysis['metrics']['price_change_24h'])}%)"
            )

        return "📊 Market Summary:\n" + "\n".join(summary_lines)

    except Exception as e:
        logger.error(f"Error getting market summary: {str(e)}")
        return "Error generating market summary"


async def fetch_token_price(chain: str, address: str, is_contract_analysis: bool = False) -> Optional[Dict]:
    """Fetch token price using market data service"""
    try:
        if is_contract_analysis and chain.lower() not in CHAIN_IDS:
            logger.debug(f"Skipping unsupported chain for contract analysis: {chain}")
            return None

        chain_id = CHAIN_IDS.get(chain.lower())
        if not chain_id:
            return None

        price_data = await market_service.get_token_price(address, chain_id)
        if price_data:
            return {
                'price': price_data,
                'chain': chain,
                'source': 'market_service'
            }

        return None

    except Exception as e:
        logger.debug(f"Error fetching token price: {str(e)}")
        return None

def format_price_message(price_data: Dict) -> str:
    """Format price data into a concise message"""
    try:
        if not price_data:
            return "Price data unavailable"

        price = format_number(price_data.get('price', 0))
        chain = price_data.get('chain', 'unknown').upper()
        change = price_data.get('change_24h')

        if change is not None:
            return f"💰 {chain}: ${price} ({format_number(change)}%)"
        return f"💰 {chain}: ${price}"

    except Exception as e:
        logger.error(f"Error formatting price message: {str(e)}")
        return "Error formatting price data"

async def fetch_chain_tvl(chain_name: Optional[str] = None) -> Optional[Dict]:
    """Fetch TVL data from DefiLlama"""
    try:
        logger.info(f"Fetching TVL data for {chain_name if chain_name else 'all chains'}")
        return await market_service.get_defillama_data(chain_name)

    except Exception as e:
        logger.error(f"Error fetching TVL: {str(e)}")
        return None

async def fetch_trending_tokens(chain_filter: Optional[str] = None) -> Optional[List[Dict]]:
    """Fetch trending tokens with sentiment analysis"""
    try:
        data = await dex_service.query_latest_dex_search("Sonic,Eth,Base")
        if data and isinstance(data, list):
            tokens = []
            for token in data:
                token_data = {
                    'chain_id': token.get('chainId'),
                    'description': token.get('description', 'No description'),
                    'amount': token.get('totalAmount', 0)
                }

                # Add BERT-based sentiment analysis
                try:
                    sentiment = await huggingface_service.analyze_market_sentiment(token_data['description'])
                    token_data['sentiment'] = sentiment
                except Exception as e:
                    logger.error(f"Error analyzing token sentiment: {str(e)}")
                    token_data['sentiment'] = None

                tokens.append(token_data)

            if chain_filter:
                chain_id = CHAIN_IDS.get(chain_filter.lower())
                if chain_id:
                    tokens = [t for t in tokens if str(t.get('chain_id', '')).lower() == chain_id.lower()]

            return tokens[:5]  # Return top 5 trending tokens
        return None

    except Exception as e:
        logger.error(f"Error fetching trending tokens: {str(e)}")
        return None

def format_tvl_message(tvl_data: Dict) -> str:
    """Format TVL data into a concise message"""
    try:
        if not tvl_data:
            return "TVL data unavailable"

        tvl = tvl_data.get('tvl', 0)
        if tvl >= 1_000_000_000:
            tvl_str = f"${tvl/1_000_000_000:.2f}B"
        elif tvl >= 1_000_000:
            tvl_str = f"${tvl/1_000_000:.2f}M"
        else:
            tvl_str = f"${tvl:,.2f}"

        change = tvl_data.get('change_1d', 0)
        change_symbol = "📈" if change > 0 else "📉"

        last_updated = tvl_data.get('lastUpdated', '')
        last_updated_str = f" (Updated: {last_updated})" if last_updated else ""

        return (
            f"📊 {tvl_data.get('chainName')}: "
            f"{tvl_str} "
            f"{change_symbol} ({change:+.2f}%)"
            f"{last_updated_str}"
        )
    except Exception as e:
        logger.error(f"Error formatting TVL message: {str(e)}")
        return "Error formatting TVL data"

async def fetch_top_pairs(chain_id: Optional[str] = None, limit: int = 6) -> Optional[List[Dict]]:
    """Fetch trending pairs for a specific chain"""
    try:
        logger.info(f"Fetching trending pairs for {chain_id if chain_id else 'all chains'}")
        data = await dex_service.query_latest_dex_search("Sonic,Eth,Base")
        if data and isinstance(data.get('pairs'), list):
            pairs = sorted(
                data['pairs'],
                key=lambda x: float(x.get('volume', {}).get('h24', 0)),
                reverse=True
            )[:limit]
            logger.info(f"Found {len(pairs)} trending pairs")
            return pairs

        logger.warning("No trending pairs found")
        return None

    except Exception as e:
        logger.error(f"Error fetching trending pairs: {str(e)}")
        return None

def format_pairs_list(pairs: List[Dict], chain_id: str) -> str:
    """Format a list of pairs into a concise message"""
    try:
        if not pairs:
            return f"No pairs found on {chain_id.upper()}"

        lines = []
        for pair in pairs[:6]:
            symbol = f"{pair['baseToken']['symbol']}/{pair['quoteToken']['symbol']}"
            price = float(pair.get('priceUsd', 0))
            volume = pair.get('volume', {}).get('h24', 0)
            price_change = pair.get('priceChange', {}).get('h24', 0)

            change_emoji = "🟢" if price_change > 0 else "🔴"
            lines.append(
                f"{change_emoji} {symbol}\n"
                f"💰 Price: ${format_number(price)} ({format_number(price_change)}%)\n"
                f"📊 Volume: ${format_number(volume)}"
            )

        return f"📊 Top pairs on {chain_id.upper()}:\n\n" + "\n\n".join(lines)

    except Exception as e:
        logger.error(f"Error formatting pairs list: {str(e)}")
        return "Error formatting pairs data"

async def fetch_equalizer_pair(token_address: str) -> Optional[Dict]:
    """Find pair information from Equalizer by token address"""
    try:
        url = "https://eqapi-sonic-prod-ltanm.ondigitalocean.app/sonic/v4/pairs"
        logger.info(f"Fetching Equalizer pairs for token: {token_address}")

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()
        logger.debug(f"Received Equalizer pairs data structure: {type(data)}")

        if not isinstance(data, dict) or 'success' not in data or 'data' not in data:
            logger.warning("Invalid pairs data structure received")
            return None

        pairs_data = data.get('data', {})
        if not isinstance(pairs_data, dict):
            logger.warning("Pairs data is not a dictionary")
            return None

        matching_pairs = []
        for pair_address, pair in pairs_data.items():
            if not isinstance(pair, dict):
                logger.warning(f"Invalid pair data for {pair_address}: {type(pair)}")
                continue

            token0 = pair.get('token0', {})
            token1 = pair.get('token1', {})

            token0_address = token0.get('address', '').lower()
            token1_address = token1.get('address', '').lower()

            if token_address.lower() in [token0_address, token1_address]:
                try:
                    tvl_usd = float(pair.get('tvlUsd', 0))
                    volume_usd = float(pair.get('apr', 0)) * tvl_usd  # Using APR * TVL as volume proxy
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error converting values for pair {pair_address}: {str(e)}")
                    tvl_usd = 0
                    volume_usd = 0

                pair_data = {
                    'pair_address': pair_address,
                    'dex': 'equalizer',
                    'token0': {
                        'address': token0_address,
                        'symbol': token0.get('symbol'),
                        'decimals': token0.get('decimals', 18)
                    },
                    'token1': {
                        'address': token1_address,
                        'symbol': token1.get('symbol'),
                        'decimals': token1.get('decimals', 18)
                    },
                    'volume_24h': volume_usd,
                    'tvl': tvl_usd,
                    'price_impact': float(pair.get('fee', '0.01').strip('%') or 0) * 100,
                    'apr': float(pair.get('apr', 0))
                }
                matching_pairs.append(pair_data)

        if matching_pairs:
            matching_pairs.sort(key=lambda x: x['tvl'], reverse=True)
            logger.info(f"Found {len(matching_pairs)} pairs for token {token_address}")
            return matching_pairs[0]

        logger.info(f"No matching pairs found for token {token_address}")
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP error fetching Equalizer pair: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error finding Equalizer pair: {str(e)}")
        return None

async def get_equalizer_stats() -> Dict[str, Any]:
    """Get Equalizer protocol statistics"""
    try:
        url = "https://eqapi-sonic-prod-ltanm.ondigitalocean.app/sonic/stats/equalizer"
        logger.info("Fetching Equalizer protocol stats")

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()
        logger.debug(f"Received Equalizer stats data structure: {type(data)}")

        if not isinstance(data, dict) or 'success' not in data or 'data' not in data:
            logger.warning("Invalid stats data format received")
            return _get_default_stats()

        try:
            raw_stats = data.get('data', {})
            ecosystem = raw_stats.get('ecosystem', {})
            stats = {
                'tvl': float(raw_stats.get('totalTvl', 0)),
                'volume_24h': float(raw_stats.get('liquidity', 0)),  # Using liquidity as 24h volume
                'fees_24h': float(raw_stats.get('totalIncentives', 0)),
                'pairs_count': int(ecosystem.get('numPairs', 0)),
                'transactions_24h': int(ecosystem.get('numTokens', 0))  # Using numTokens as a proxy
            }
            logger.info(f"Successfully fetched Equalizer stats: TVL=${stats['tvl']:,.2f}, "
                       f"24h Volume=${stats['volume_24h']:,.2f}")
            return stats

        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing Equalizer stats values: {str(e)}")
            return _get_default_stats()

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP error fetching Equalizer stats: {str(e)}")
        return _get_default_stats()
    except Exception as e:
        logger.error(f"Error fetching Equalizer stats: {str(e)}")
        return _get_default_stats()

def _get_default_stats() -> Dict[str, Any]:
    """Return default stats structure"""
    return {
        'tvl': 0,
        'volume_24h': 0,
        'fees_24h': 0,
        'pairs_count': 0,
        'transactions_24h': 0
    }

async def fetch_tokens_by_chain(chain: str, addresses: List[str]) -> Optional[List[Dict]]:
    """Fetch data for multiple tokens on a specific chain"""
    try:
        chain_id = CHAIN_IDS.get(chain.lower())
        if not chain_id:
            logger.error(f"Unsupported chain: {chain}")
            return None

        if chain.lower() == 'sonic':
            # Use OpenOcean for Sonic chain
            results = []
            for address in addresses:
                price_data = await fetch_token_price('sonic', address)
                if price_data:
                    results.append(price_data)
            return results if results else None

        # Use DexScreener for other chains
        addresses_str = ','.join(addresses[:30])  # Limit to 30 addresses
        data = await dex_service.fetch_tokens_by_chain(chain_id, addresses_str)
        if data and isinstance(data, list):
            return [{
                'chain_id': pair.get('chainId'),
                'price': float(pair.get('priceUsd', 0)),
                'change_24h': pair.get('priceChange', {}).get('h24', 0),
                'volume_24h': pair.get('volume', {}).get('h24'),
                'liquidity_usd': pair.get('liquidity', {}).get('usd'),
                'base_token': pair.get('baseToken', {})
            } for pair in data]

        return None

    except Exception as e:
        logger.error(f"Error fetching tokens data: {str(e)}")
        return None

def calculate_price_impact(pair: Dict) -> float:
    """Calculate price impact for a pair based on reserves"""
    try:
        reserve0 = float(pair.get('reserve0', 0))
        reserve1 = float(pair.get('reserve1', 0))
        if reserve0 <= 0 or reserve1 <= 0:
            return 0

        # Calculate price impact for a 1% trade of total liquidity
        trade_amount = reserve0 * 0.01
        price_impact = (trade_amount * reserve1) / (reserve0 * (reserve0 + trade_amount))
        return abs(1 - price_impact) * 100

    except Exception as e:
        logger.error(f"Error calculating price impact: {str(e)}")
        return 0

async def fetch_token_price_new(chain: str, address: str, is_contract_analysis: bool = False) -> Optional[Dict]:
    """
    Fetch token price using OpenOcean for Sonic chain, fallback to DexScreener for others
    """
    try:
        # For contract analysis, only query the specified chain
        if is_contract_analysis:
            if chain.lower() not in CHAIN_IDS:
                logger.debug(f"Skipping unsupported chain for contract analysis: {chain}")
                return None

        # Try OpenOcean first for Sonic chain
        if chain.lower() == 'sonic':
            logger.info("Using OpenOcean API for Sonic chain price")
            url = f"{OPENOCEAN_API}/{SONIC_CHAIN_ID}/quote"
            params = {
                'inTokenAddress': address,
                'outTokenAddress': 'USDC',  # Quote against USDC
                'amount': '1',
                'gasPrice': '5'
            }
            try:
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    price = data.get('data', {}).get('price')
                    if price:
                        return {
                            'price': float(price),
                            'chain': 'sonic',
                            'source': 'openocean'
                        }
                elif response.status_code == 404:
                    logger.debug("Token not found on OpenOcean")
                    return None
            except Exception as e:
                logger.debug(f"OpenOcean API request failed: {str(e)}")
                return None

        # Use DexScreener for other chains or as fallback
        chain_id = CHAIN_IDS.get(chain.lower())
        if not chain_id:
            return None

        data = await dex_service.fetch_token_price(chain_id, address)
        if data :
            return {
                'price': float(data.get('priceUsd', 0)),
                'chain': chain,
                'change_24h': data.get('priceChange', {}).get('h24', 0),
                'source': 'dexscreener'
            }
        elif response.status_code == 404:
            logger.debug(f"Token not found on {chain}")
            return None
        return None

    except Exception as e:
        logger.debug(f"Error fetching token price: {str(e)}")
        return None

def format_price_message(price_data: Dict) -> str:
    """Format price data into a concise one-line message"""
    try:
        if not price_data:
            return "Price data unavailable"

        price = format_number(price_data.get('price', 0))
        chain = price_data.get('chain', 'unknown').upper()
        change = price_data.get('change_24h')

        if change is not None:
            return f"💰 {chain}: ${price} ({format_number(change)}%)"
        return f"💰 {chain}: ${price}"

    except Exception as e:
        logger.error(f"Error formatting price message: {str(e)}")
        return "Error formatting price data"

def format_tvl_message(tvl_data: Dict) -> str:
    """Format TVL data into a concise message"""
    try:
        if not tvl_data:
            return "TVL data unavailable"

        # Format numbers for better readability
        tvl = tvl_data.get('tvl', 0)
        if tvl >= 1_000_000_000:
            tvl_str = f"${tvl/1_000_000_000:.2f}B"
        elif tvl >= 1_000_000:
            tvl_str = f"${tvl/1_000_000:.2f}M"
        else:
            tvl_str = f"${tvl:,.2f}"

        change = tvl_data.get('change_1d', 0)
        change_symbol = "📈" if change > 0 else "📉"

        last_updated = tvl_data.get('lastUpdated', '')
        last_updated_str = f" (Updated: {last_updated})" if last_updated else ""

        return (
            f"📊 {tvl_data.get('chainName')}: "
            f"{tvl_str} "
            f"{change_symbol} ({change:+.2f}%)"
            f"{last_updated_str}"
        )
    except Exception as e:
        logger.error(f"Error formatting TVL message: {str(e)}")
        return "Error formatting TVL data"