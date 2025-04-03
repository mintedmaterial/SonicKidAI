"""
Discord Webhook Service for Twitter Feed

This script runs a specialized service that:
1. Sets up the database connection for storing tweets
2. Exposes a webhook endpoint to receive tweets from Discord
3. Processes and analyzes tweets for sentiment and important content
4. Stores tweets in the database for display in the Dashboard Twitter Feed

Usage:
    python run_discord_webhook_service.py
"""
import os
import asyncio
import signal
import logging
from dotenv import load_dotenv
import json
import aiohttp
from aiohttp import web
import asyncpg
from datetime import datetime, timezone
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global database connection pool
db_pool = None

# Global shutdown flag
shutdown_requested = False

# Constants
TWITTER_FEED_CHANNEL_ID = "1333615004305330348"
DISCORD_AGENT_WEBHOOK_URL = None

# Signal handlers
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating shutdown...")
    shutdown_requested = True

async def shutdown():
    """Perform graceful shutdown"""
    logger.info("Shutting down Discord webhook service...")

    # Close database connection pool if it exists
    global db_pool
    if db_pool:
        logger.info("Closing database connection pool...")
        await db_pool.close()
        logger.info("Database connection pool closed")

    logger.info("Shutdown complete")

# Database functions
async def init_db():
    """Initialize database connection pool"""
    global db_pool
    
    try:
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            return False
            
        # Create connection pool
        logger.info("Creating database connection pool...")
        db_pool = await asyncpg.create_pool(database_url)
        
        logger.info("✅ Database connection established")
        return True
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        return False

async def store_tweet(tweet_data):
    """Store tweet data in the database"""
    if not db_pool:
        logger.error("Database connection not established")
        return False
        
    try:
        # Extract data from tweet payload
        username = tweet_data.get('author', {}).get('username', 'unknown_user')
        tweet_id = tweet_data.get('id', f"tweet-{datetime.now(timezone.utc).timestamp()}")
        content = tweet_data.get('text', '')
        
        # Extract contract addresses if present
        contract_addresses = []
        contract_regex = re.compile(r'0x[a-fA-F0-9]{40}')
        matches = contract_regex.findall(content)
        if matches:
            contract_addresses = matches
            
        # Build metadata
        metadata = {
            'authorName': tweet_data.get('author', {}).get('name', username),
            'profileImageUrl': tweet_data.get('author', {}).get('profile_image_url'),
            'publicMetrics': tweet_data.get('public_metrics', {
                'reply_count': 0,
                'retweet_count': 0,
                'like_count': 0
            }),
            'source': 'discord_webhook',
            'channelId': TWITTER_FEED_CHANNEL_ID
        }
        
        # Store in database
        query = """
        INSERT INTO twitter_scrape_data 
        (username, tweet_id, content, contract_addresses, timestamp, metadata)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (tweet_id) 
        DO UPDATE SET
            content = EXCLUDED.content,
            contract_addresses = EXCLUDED.contract_addresses,
            metadata = EXCLUDED.metadata
        RETURNING id
        """
        
        result = await db_pool.fetchval(
            query, 
            username, 
            tweet_id, 
            content, 
            contract_addresses, 
            datetime.now(timezone.utc),
            json.dumps(metadata)
        )
        
        logger.info(f"Stored tweet in database with ID: {result}")
        return True
    except Exception as e:
        logger.error(f"Error storing tweet in database: {str(e)}")
        return False

async def analyze_tweet_content(text):
    """Analyze tweet content for importance and sentiment"""
    # Check for critical keywords
    critical_keywords = [
        'urgent', 'emergency', 'hack', 'exploit', 'vulnerability', 'scam', 
        'warning', 'alert', 'critical', 'security', 'breach', 'stolen',
        'rug pull', 'attack', 'SEC', 'regulation'
    ]
    
    # Check for market event keywords
    market_event_keywords = [
        'partnership', 'listing', 'acquisition', 'launched', 'release', 
        'announces', 'update', 'upgraded', 'integration', 'collaboration',
        'breaking', 'exclusive'
    ]
    
    # Check for monitored assets
    monitored_assets = [
        'sonic', 'ethereum', 'bitcoin', 'btc', 'eth', '$eth', '$btc', '$sonic',
        'sol', '$sol', 'solana', 'arbitrum', 'optimism', 'base'
    ]
    
    # Analyze content
    text_lower = text.lower()
    
    # Check for critical keywords
    critical_found = [kw for kw in critical_keywords if kw in text_lower]
    
    # Check for market events
    events_found = [kw for kw in market_event_keywords if kw in text_lower]
    
    # Check for monitored assets
    assets_found = [kw for kw in monitored_assets if kw in text_lower]
    
    # Determine importance level
    importance = 'low'
    tag_agent = False
    reason = None
    
    if critical_found:
        importance = 'critical'
        tag_agent = True
        reason = f"Critical keywords found: {', '.join(critical_found)}"
    elif events_found and assets_found:
        importance = 'high'
        tag_agent = True
        reason = f"Market event keywords for monitored assets: {', '.join(events_found)} + {', '.join(assets_found)}"
    elif assets_found:
        importance = 'medium'
        reason = f"Mentions monitored assets: {', '.join(assets_found)}"
        
    return {
        'importance': importance,
        'tag_agent': tag_agent,
        'reason': reason,
        'critical_keywords': critical_found,
        'market_events': events_found,
        'assets': assets_found
    }

async def send_discord_notification(tweet_data, analysis):
    """Send notification to Discord for important tweets"""
    if not DISCORD_AGENT_WEBHOOK_URL:
        logger.warning("Discord agent webhook URL not configured. Skipping notification.")
        return False
    
    try:
        # Format the message
        message = f"**<#{TWITTER_FEED_CHANNEL_ID}>** New important tweet detected!\n\n"
        
        if analysis['importance'] == 'critical':
            message += f"⚠️ **CRITICAL ALERT** ⚠️\n\n"
        elif analysis['importance'] == 'high':
            message += f"📈 **MARKET EVENT** 📈\n\n"
        else:
            message += f"🤖 **NOTABLE CONTENT** 🤖\n\n"
        
        # Add tweet details
        message += f"**Author:** {tweet_data['author']['name']} (@{tweet_data['author']['username']})\n"
        message += f"**Content:** {tweet_data['text']}\n"
        message += f"**Tweet ID:** {tweet_data['id']}\n"
        
        # Add analysis
        if analysis['reason']:
            message += f"\n**Reason flagged:** {analysis['reason']}\n"
        
        message += f"\n*Use the dashboard search to find this tweet using creator:{tweet_data['author']['username']} or tweetId:{tweet_data['id']}*"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(DISCORD_AGENT_WEBHOOK_URL, json={
                'content': message,
                'username': 'Tweet Alert Bot',
                'avatar_url': 'https://cdn-icons-png.flaticon.com/512/733/733579.png'
            }) as response:
                if response.status == 200 or response.status == 204:
                    logger.info(f"Successfully sent agent notification for tweet ID {tweet_data['id']}")
                    return True
                else:
                    logger.error(f"Error sending Discord notification. Status: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"Error sending Discord notification: {str(e)}")
        return False

# Discord webhook endpoint handler
async def format_discord_webhook(payload):
    """Format Discord webhook payload into tweet format"""
    # Generate a unique ID
    tweet_id = f"tweet-{datetime.now(timezone.utc).timestamp()}-{hash(str(payload)) % 10000}"
    
    # Extract content from different possible payload formats
    content = payload.get('content', '')
    
    # Check for embeds
    embeds = payload.get('embeds', [])
    if embeds and len(embeds) > 0:
        # Use embed description if available
        embed = embeds[0]
        if 'description' in embed and embed['description']:
            content = embed['description']
        
        # Extract author information if available
        author = {}
        if 'author' in embed and embed['author']:
            author_info = embed['author']
            
            # Handle author in format "Name@username"
            author_name = author_info.get('name', 'Unknown')
            username = 'unknown_user'
            
            if '@' in author_name:
                parts = author_name.split('@')
                author_name = parts[0].strip()
                username = parts[1].strip()
            else:
                # Create username from name
                username = author_name.lower().replace(' ', '_')
            
            author = {
                'name': author_name,
                'username': username,
                'profile_image_url': author_info.get('icon_url')
            }
        else:
            # Default author if not found
            author = {
                'name': 'Discord User',
                'username': 'discord_user',
                'profile_image_url': None
            }
    else:
        # Default author for plain text messages
        author = {
            'name': 'Discord User',
            'username': 'discord_user',
            'profile_image_url': None
        }
    
    # Format as tweet
    tweet = {
        'id': tweet_id,
        'text': content,
        'author': author,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'public_metrics': {
            'reply_count': 0,
            'retweet_count': 0,
            'like_count': 0
        }
    }
    
    return tweet

# Web server routes
async def handle_webhook(request):
    """Handle incoming Discord webhook"""
    try:
        # Parse JSON payload
        payload = await request.json()
        logger.info(f"Received webhook payload from {request.remote}")
        
        # Check channel ID 
        channel_id = payload.get('channel_id', '')
        if channel_id and channel_id != TWITTER_FEED_CHANNEL_ID:
            logger.info(f"Ignoring webhook from non-Twitter feed channel: {channel_id}")
            return web.json_response({
                'success': True,
                'processed': False,
                'reason': 'Not from Twitter feed channel'
            })
        
        # Format tweet
        tweet = await format_discord_webhook(payload)
        logger.info(f"Formatted tweet: {tweet['text'][:30]}...")
        
        # Analyze tweet
        analysis = await analyze_tweet_content(tweet['text'])
        logger.info(f"Tweet analysis: importance={analysis['importance']}, tag_agent={analysis['tag_agent']}")
        
        # Store in database
        stored = await store_tweet(tweet)
        if not stored:
            return web.json_response({
                'success': False,
                'error': 'Failed to store tweet in database'
            }, status=500)
        
        # Send notification if needed
        if analysis['tag_agent']:
            await send_discord_notification(tweet, analysis)
        
        # Return success
        return web.json_response({
            'success': True,
            'processed': True,
            'tweetId': tweet['id'],
            'analysis': analysis
        })
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=400)

async def handle_status(request):
    """Return service status"""
    return web.json_response({
        'status': 'running',
        'database_connected': db_pool is not None,
        'channel_id': TWITTER_FEED_CHANNEL_ID
    })

# Main service functions
async def run_webhook_service():
    """Run the Discord webhook service"""
    global DISCORD_AGENT_WEBHOOK_URL
    
    try:
        # Load environment variables
        load_dotenv()
        
        # Set agent webhook URL
        DISCORD_AGENT_WEBHOOK_URL = os.getenv('DISCORD_AGENT_WEBHOOK_URL')
        if not DISCORD_AGENT_WEBHOOK_URL:
            logger.warning("DISCORD_AGENT_WEBHOOK_URL not set. Agent notifications will be disabled.")
        
        # Initialize database
        db_connected = await init_db()
        if not db_connected:
            logger.error("Failed to connect to database. Exiting.")
            return False
        
        # Create web application
        app = web.Application()
        app.add_routes([
            web.post('/webhook', handle_webhook),
            web.get('/status', handle_status)
        ])
        
        # Start web server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8888)
        await site.start()
        
        logger.info("✅ Discord webhook service is running on port 8888")
        logger.info(f"✅ Listening for tweets from Discord channel {TWITTER_FEED_CHANNEL_ID}")
        
        # Keep service running until shutdown requested
        while not shutdown_requested:
            await asyncio.sleep(1)
        
        # Shutdown web server
        logger.info("Stopping web server...")
        await runner.cleanup()
        
        return True
    except Exception as e:
        logger.error(f"Error in Discord webhook service: {str(e)}")
        await shutdown()
        return False

async def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    
    logger.info("Starting Discord webhook service...")
    
    try:
        # Run the service
        await run_webhook_service()
    except Exception as e:
        logger.error(f"Unhandled error in main: {str(e)}")
        await shutdown()

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())