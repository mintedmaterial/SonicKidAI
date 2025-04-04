"""
Test SonicKid Tweet Generation and Posting

This script tests the ability to generate a tweet in SonicKid's style about a
trading update and post it to Twitter using the agent-twitter-client package.
"""
import os
import json
import asyncio
import tempfile
import logging
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

class TwitterPostClient:
    """Client for posting tweets to Twitter"""
    
    def __init__(self):
        """Initialize the Twitter client"""
        # Load environment variables
        self.auth_token = os.environ.get("TWITTER_AUTH_TOKEN", "")
        self.auth_multi_token = os.environ.get("TWITTER_AUTH_MULTI_TOKEN", "")
        self.username = os.environ.get("TWITTER_USERNAME", "")
        self.password = os.environ.get("TWITTER_PASSWORD", "")
        self.email = os.environ.get("TWITTER_EMAIL", "")
        
        if not self.auth_token:
            logger.warning("TWITTER_AUTH_TOKEN not found in environment variables")
            
        if not self.username or not self.password:
            logger.warning("TWITTER_USERNAME or TWITTER_PASSWORD not found in environment variables")
    
    async def authenticate(self) -> bool:
        """Authenticate with Twitter"""
        logger.info("Starting Twitter authentication")
        
        try:
            script = self._create_auth_script()
            result = await self._run_node_script(script)
            
            if not result:
                logger.error("Authentication failed: No result from script")
                return False
            
            try:
                data = json.loads(result)
                if data.get("success", False):
                    logger.info("Authentication successful")
                    if "token" in data:
                        logger.info(f"Got token: {data['token'][:20]}...")
                    return True
                else:
                    logger.error(f"Authentication failed: {data.get('error', 'Unknown error')}")
                    return False
            except json.JSONDecodeError:
                logger.error(f"Failed to parse authentication result: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
    
    async def post_tweet(self, tweet_text: str) -> bool:
        """Post a tweet to Twitter"""
        logger.info(f"Posting tweet: {tweet_text}")
        
        try:
            script = self._create_post_tweet_script(tweet_text)
            result = await self._run_node_script(script)
            
            if not result:
                logger.error("Tweet posting failed: No result from script")
                return False
            
            try:
                data = json.loads(result)
                if data.get("success", False):
                    logger.info("Tweet posted successfully")
                    if "tweet_id" in data:
                        logger.info(f"Tweet ID: {data['tweet_id']}")
                    return True
                else:
                    logger.error(f"Tweet posting failed: {data.get('error', 'Unknown error')}")
                    return False
            except json.JSONDecodeError:
                logger.error(f"Failed to parse tweet posting result: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Tweet posting error: {str(e)}")
            return False
    
    def _create_auth_script(self) -> str:
        """Create Node.js script for authentication"""
        return f"""
        const {{ Scraper }} = require('agent-twitter-client');

        (async () => {{
            try {{
                const scraper = new Scraper();
                
                // Try authenticating with auth token first
                if ('{self.auth_token}') {{
                    const success = await scraper.loginWithAuthToken('{self.auth_token}');
                    if (success) {{
                        const token = scraper.getGuestToken();
                        console.log(JSON.stringify({{ success: true, method: 'auth_token', token }}));
                        return;
                    }}
                }}
                
                // Fall back to username/password if auth token fails
                if ('{self.username}' && '{self.password}') {{
                    const success = await scraper.login('{self.username}', '{self.password}');
                    if (success) {{
                        const token = scraper.getGuestToken();
                        console.log(JSON.stringify({{ success: true, method: 'credentials', token }}));
                        return;
                    }}
                }}
                
                console.log(JSON.stringify({{ success: false, error: 'Authentication failed with all methods' }}));
            }} catch (error) {{
                console.log(JSON.stringify({{ success: false, error: error.message }}));
            }}
        }})();
        """
    
    def _create_post_tweet_script(self, tweet_text: str) -> str:
        """Create Node.js script for posting a tweet"""
        # Escape any single quotes in the tweet text to avoid breaking the JS template string
        safe_tweet_text = tweet_text.replace("'", "\\'")
        
        return f"""
        const {{ Scraper }} = require('agent-twitter-client');

        (async () => {{
            try {{
                const scraper = new Scraper();
                
                // Authenticate first
                let authenticated = false;
                
                if ('{self.auth_token}') {{
                    authenticated = await scraper.loginWithAuthToken('{self.auth_token}');
                }}
                
                if (!authenticated && '{self.username}' && '{self.password}') {{
                    authenticated = await scraper.login('{self.username}', '{self.password}');
                }}
                
                if (!authenticated) {{
                    console.log(JSON.stringify({{ success: false, error: 'Authentication failed' }}));
                    return;
                }}
                
                // Post tweet
                const result = await scraper.sendTweet('{safe_tweet_text}');
                if (result && result.tweet_id) {{
                    console.log(JSON.stringify({{ 
                        success: true, 
                        tweet_id: result.tweet_id,
                        message: 'Tweet posted successfully' 
                    }}));
                }} else {{
                    console.log(JSON.stringify({{ 
                        success: false, 
                        error: 'No tweet ID returned' 
                    }}));
                }}
            }} catch (error) {{
                console.log(JSON.stringify({{ success: false, error: error.message }}));
            }}
        }})();
        """
    
    async def _run_node_script(self, script: str) -> Optional[str]:
        """
        Run a Node.js script and return its output
        
        Args:
            script: Node.js script to run
            
        Returns:
            Script output or None if an error occurred
        """
        with tempfile.NamedTemporaryFile(suffix=".js", delete=False) as f:
            script_path = f.name
            f.write(script.encode('utf-8'))
        
        try:
            process = await asyncio.create_subprocess_exec(
                "node", script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if stderr:
                error_message = stderr.decode('utf-8').strip()
                if error_message:
                    logger.error(f"Script error: {error_message}")
            
            if process.returncode != 0:
                logger.error(f"Script exited with non-zero code: {process.returncode}")
                return None
            
            output = stdout.decode('utf-8').strip()
            return output
            
        except Exception as e:
            logger.error(f"Error running Node.js script: {str(e)}")
            return None
        finally:
            try:
                os.unlink(script_path)
            except:
                pass

async def generate_sonic_kid_tweet() -> str:
    """
    Generate a tweet in SonicKid's style about a trading update using real-time data
    
    Returns:
        str: The generated tweet text
    """
    # Get real data from database
    import psycopg2
    import json
    import os
    from psycopg2.extras import RealDictCursor
    
    # Get database connection string from environment variables
    database_url = os.environ.get("DATABASE_URL")
    
    if not database_url:
        logger.error("DATABASE_URL not found in environment variables")
        raise ValueError("DATABASE_URL environment variable is required")
    
    # Connect to the database
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # First try to get specific OS/USDC.e pair data
        cursor.execute("""
            SELECT 
                pair_symbol, 
                base_token,
                quote_token,
                price, 
                price_change_24h, 
                volume_24h, 
                liquidity,
                metadata
            FROM sonic_price_feed 
            WHERE base_token = 'OS' AND quote_token = 'USDC.e'
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        
        # If no OS/USDC.e data, get any most recent price data
        if not result:
            logger.warning("No OS/USDC.e price data found, getting most recent price data")
            cursor.execute("""
                SELECT 
                    pair_symbol, 
                    base_token,
                    quote_token,
                    price, 
                    price_change_24h, 
                    volume_24h, 
                    liquidity,
                    metadata
                FROM sonic_price_feed 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            result = cursor.fetchone()
        
        if not result:
            logger.error("No price data found in database")
            raise ValueError("No price data available in database")
        
        # Parse the metadata JSON if it exists
        metadata = {}
        if result['metadata']:
            # Check if metadata is already a dict or is a JSON string
            if isinstance(result['metadata'], dict):
                metadata = result['metadata']
            elif isinstance(result['metadata'], str) and result['metadata'].strip():
                try:
                    metadata = json.loads(result['metadata'])
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Could not parse metadata JSON: {result['metadata']}")
            else:
                logger.warning(f"Unexpected metadata type: {type(result['metadata'])}")
        
        # Construct the trade data
        trade_data = {
            "pair": f"{result['base_token']}/{result['quote_token']}",
            "price": float(result['price']),
            "price_change_24h": float(result['price_change_24h']),
            "volume_24h": float(result['volume_24h']),
            "liquidity": float(result['liquidity']),
            "metadata": metadata
        }
        
        # Add buy/sell sentiment based on market data
        if trade_data["price_change_24h"] > 0:
            trade_data["action"] = "buy"
            trade_data["sentiment"] = "bullish"
        else:
            trade_data["action"] = "watching"
            trade_data["sentiment"] = "cautious"
        
        # Get additional market sentiment data if available
        cursor.execute("""
            SELECT sentiment, score, content 
            FROM market_sentiment 
            WHERE symbol = %s 
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (result['base_token'],))
        
        sentiment_data = cursor.fetchone()
        if sentiment_data:
            trade_data["market_sentiment"] = sentiment_data["sentiment"]
            trade_data["sentiment_score"] = float(sentiment_data["score"])
            trade_data["sentiment_content"] = sentiment_data["content"]
        
        # Check for relevant whale alerts
        cursor.execute("""
            SELECT wallet_address, movement_type, price_change, volume_change, 
                   volatility, sentiment, confidence, details
            FROM whale_alerts
            ORDER BY timestamp DESC
            LIMIT 5
        """)
        
        whale_alerts = cursor.fetchall()
        if whale_alerts:
            # Find the most significant whale alert based on confidence and volume
            most_significant_alert = None
            highest_score = 0
            
            for alert in whale_alerts:
                # Calculate significance score based on confidence and volume
                confidence = float(alert["confidence"]) if alert["confidence"] else 0
                volume = float(alert["volume_change"]) if alert["volume_change"] else 0
                significance_score = confidence * volume / 100
                
                if significance_score > highest_score:
                    highest_score = significance_score
                    most_significant_alert = alert
            
            if most_significant_alert:
                trade_data["whale_alert"] = {
                    "wallet": most_significant_alert["wallet_address"],
                    "type": most_significant_alert["movement_type"],
                    "price_impact": float(most_significant_alert["price_change"]) if most_significant_alert["price_change"] else 0,
                    "volume": float(most_significant_alert["volume_change"]) if most_significant_alert["volume_change"] else 0,
                    "sentiment": most_significant_alert["sentiment"],
                    "confidence": float(most_significant_alert["confidence"]) if most_significant_alert["confidence"] else 0
                }
        
        logger.info(f"Retrieved price data from database: {trade_data}")
        
    except Exception as e:
        logger.error(f"Error retrieving price data from database: {str(e)}")
        raise
    finally:
        # Close database connection
        cursor.close()
        conn.close()
    
    # Generate tweet content based on market sentiment and data
    price_change = trade_data.get("price_change_24h", 0)
    market_sentiment = trade_data.get("market_sentiment", "").lower()
    
    # Set sentiment variables based on price change and market sentiment
    if price_change > 0:
        # Bullish tweet for positive price change
        emoji_set = ["🚀", "💰", "📈", "🔥"]
        action_phrase = "Just aped into"
        
        if market_sentiment == "positive" or market_sentiment == "bullish":
            sentiment_phrase = "Market sentiment is STRONG! Bulls taking control!"
        else:
            sentiment_phrase = "The charts are SCREAMING right now! Cross-chain liquidity flowing in FAST!"
            
        conclusion = "This setup is TOO CLEAN to ignore! $Goglz Stay On! 👑"
    else:
        # Cautious tweet for negative price change
        emoji_set = ["👀", "💰", "📊", "🔍"]
        action_phrase = "Keeping a close eye on"
        
        if market_sentiment == "negative" or market_sentiment == "bearish":
            sentiment_phrase = "Market sentiment is weak. Bears putting pressure on key levels."
        else:
            sentiment_phrase = "Market's showing some weakness but watching key levels."
            
        conclusion = "Waiting for confirmation before making a move. Stay sharp! 🧠"
    
    # Format the price change with appropriate sign
    price_change_str = f"+{price_change:.2f}" if price_change > 0 else f"{price_change:.2f}"
    
    # Get market metadata information if available
    market_metadata = trade_data.get("metadata", {})
    txn_data = market_metadata.get("txns", {}).get("h24", {})
    buy_sell_ratio = ""
    
    if txn_data and "buys" in txn_data and "sells" in txn_data:
        buys = txn_data.get("buys", 0)
        sells = txn_data.get("sells", 0)
        if buys > 0 or sells > 0:
            ratio = buys / (buys + sells) if (buys + sells) > 0 else 0
            ratio_pct = ratio * 100
            buy_sell_emoji = "📈" if ratio > 0.5 else "📉"
            buy_sell_ratio = f"Buy/Sell Ratio: {ratio_pct:.1f}% {buy_sell_emoji}"
    
    # Get market cap if available in metadata
    market_cap_info = ""
    if "marketCap" in market_metadata:
        market_cap = market_metadata.get("marketCap", 0)
        if market_cap > 0:
            market_cap_info = f"Market Cap: ${market_cap:,.0f}"
    
    # Create a trade update tweet in SonicKid's style
    tweet_parts = [
        f"{emoji_set[0]} SONIC MARKET UPDATE {emoji_set[0]}",
        f"{action_phrase} ${trade_data['pair'].split('/')[0]} @ ${trade_data['price']:.4f} {emoji_set[1]}",
        f"24h Change: {price_change_str}% {emoji_set[2]}",
        f"Volume: ${trade_data.get('volume_24h', 0):,.2f}"
    ]
    
    # Add liquidity information
    if trade_data.get("liquidity", 0) > 0:
        tweet_parts.append(f"Liquidity: ${trade_data.get('liquidity', 0):,.2f}")
    
    # Add buy/sell ratio if available
    if buy_sell_ratio:
        tweet_parts.append(buy_sell_ratio)
    
    # Add market cap if available
    if market_cap_info:
        tweet_parts.append(market_cap_info)
    
    # Add sentiment content if available and short enough
    if "sentiment_content" in trade_data and len(trade_data["sentiment_content"]) < 50:
        tweet_parts.append(f"Sentiment: {trade_data['sentiment_content']}")
    
    # Add whale alert information if available
    if "whale_alert" in trade_data:
        whale = trade_data["whale_alert"]
        wallet_short = whale["wallet"][:6] + "..." + whale["wallet"][-4:]
        movement_type = whale["type"].capitalize()
        volume = whale["volume"]
        
        if movement_type.lower() == "loading" and volume > 0:
            whale_msg = f"🐋 Whale Alert: {wallet_short} accumulating ${volume:,.0f} in volume!"
        elif movement_type.lower() == "shaving" and volume > 0:
            whale_msg = f"🐋 Whale Alert: {wallet_short} selling ${volume:,.0f} in volume!"
        else:
            whale_msg = f"🐋 Whale Alert: {wallet_short} making moves with ${volume:,.0f}!"
            
        tweet_parts.append(whale_msg)
    
    # Add sentiment analysis and conclusion
    tweet_parts.extend([
        f"{sentiment_phrase} {conclusion}",
        "#SONIC #DeFi #CrossChain"
    ])
    
    # Join all parts with appropriate spacing
    tweet = "\n\n".join(tweet_parts)
    
    # Ensure tweet is under 280 characters
    if len(tweet) > 280:
        logger.warning(f"Tweet too long ({len(tweet)} chars), trimming...")
        # Simplify the tweet to fit the character limit
        tweet_parts = [
            f"{emoji_set[0]} SONIC MARKET UPDATE {emoji_set[0]}",
            f"{action_phrase} ${trade_data['pair'].split('/')[0]} @ ${trade_data['price']:.4f}",
            f"24h: {price_change_str}% | Vol: ${trade_data.get('volume_24h', 0)/1000000:.1f}M",
            f"{conclusion}",
            "#SONIC #DeFi"
        ]
        tweet = "\n\n".join(tweet_parts)
        
        if len(tweet) > 280:
            # Final fallback for extremely long tweets
            tweet = tweet[:277] + "..."
    
    return tweet

async def test_post_sonic_tweet():
    """Test posting a SonicKid style tweet"""
    logger.info("Starting SonicKid tweet test")
    
    # Generate tweet
    tweet_text = await generate_sonic_kid_tweet()
    logger.info(f"Generated tweet: {tweet_text}")
    
    # Create Twitter client and authenticate
    client = TwitterPostClient()
    auth_success = await client.authenticate()
    
    if not auth_success:
        logger.error("Authentication failed, cannot post tweet")
        return
    
    # Post the tweet
    post_success = await client.post_tweet(tweet_text)
    logger.info(f"Tweet posting result: {'Success' if post_success else 'Failed'}")
    
async def generate_tweet_only():
    """Generate tweet only without posting"""
    logger.info("Generating tweet only (no posting)")
    tweet_text = await generate_sonic_kid_tweet()
    logger.info(f"Generated tweet content: {tweet_text}")
    logger.info(f"Tweet length: {len(tweet_text)} characters")
    return tweet_text

async def main():
    """Main entry point"""
    logger.info("Starting Twitter posting test")
    
    # Choose which test to run
    test_mode = os.getenv("TEST_MODE", "generate_only").lower()
    
    if test_mode == "generate_only":
        await generate_tweet_only()
    elif test_mode == "post":
        await test_post_sonic_tweet()
    else:
        logger.warning(f"Unknown test mode: {test_mode}, defaulting to generate_only")
        await generate_tweet_only()
    
    logger.info("Twitter posting test completed")

if __name__ == "__main__":
    asyncio.run(main())