"""
Twitter Feed Webhook Service

This script provides a webhook endpoint at /webhook that receives incoming
tweets from Discord and stores them in the database for display in the 
Dashboard Twitter Feed.

Usage:
    python run_twitter_feed_webhook.py
"""
import os
import sys
import json
import asyncio
import logging
import signal
from datetime import datetime, timezone
import re
from aiohttp import web
import asyncpg
from dotenv import load_dotenv

# Configure logging
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

# Signal handlers
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating shutdown...")
    shutdown_requested = True

async def shutdown():
    """Perform graceful shutdown"""
    global db_pool
    logger.info("Shutting down webhook service...")
    
    # Close database connection if it exists
    if db_pool:
        logger.info("Closing database connection pool...")
        await db_pool.close()
        logger.info("Database connection pool closed")
    
    logger.info("Webhook service shutdown complete")

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
        
        # Test connection
        test = await db_pool.fetchval("SELECT 1")
        if test == 1:
            logger.info("✅ Database connection established and tested")
            return True
        else:
            logger.error("Database connection test failed")
            return False
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        return False

async def store_tweet(tweet_data):
    """Store tweet in database"""
    try:
        # Extract data
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
        
        # Insert into database (handling timezone correctly)
        query = """
        INSERT INTO twitter_scrape_data 
        (username, tweet_id, content, contract_addresses, timestamp, metadata, created_at)
        VALUES ($1, $2, $3, $4, NOW(), $5, NOW())
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
            json.dumps(metadata)
        )
        
        logger.info(f"✅ Stored tweet in database with ID: {result}")
        return True
    except Exception as e:
        logger.error(f"Error storing tweet in database: {str(e)}")
        return False

# Webhook processing
async def format_discord_webhook(payload):
    """Format Discord webhook payload into tweet format"""
    # Generate a unique ID
    tweet_id = f"tweet-{datetime.now(timezone.utc).timestamp()}"
    
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

# Web server handlers
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
        logger.info(f"Formatted tweet: {tweet['text'][:50]}...")
        
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
        'channel_id': TWITTER_FEED_CHANNEL_ID,
        'tweet_count': await db_pool.fetchval("SELECT COUNT(*) FROM twitter_scrape_data") if db_pool else 0,
        'webhook_url': '/webhook'
    })

async def handle_test(request):
    """Handle test endpoint"""
    try:
        # Insert test tweet
        test_tweet = {
            'id': f"test-{datetime.now(timezone.utc).timestamp()}",
            'text': "This is a test tweet from the webhook service at " + datetime.now().isoformat(),
            'author': {
                'name': 'Test User',
                'username': 'test_user',
                'profile_image_url': None
            },
            'created_at': datetime.now(timezone.utc).isoformat(),
            'public_metrics': {
                'reply_count': 0,
                'retweet_count': 0,
                'like_count': 0
            }
        }
        
        # Store in database
        stored = await store_tweet(test_tweet)
        
        return web.json_response({
            'success': stored,
            'message': 'Test tweet created successfully!' if stored else 'Failed to create test tweet',
            'tweet': test_tweet
        })
    except Exception as e:
        logger.error(f"Error creating test tweet: {str(e)}")
        return web.json_response({
            'success': False,
            'error': str(e)
        }, status=500)

async def run_webhook_service():
    """Run the webhook service"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Initialize database
        db_connected = await init_db()
        if not db_connected:
            logger.error("Failed to connect to database. Exiting.")
            return False
        
        # Create web application
        app = web.Application()
        app.add_routes([
            web.post('/webhook', handle_webhook),
            web.get('/status', handle_status),
            web.get('/test', handle_test)
        ])
        
        # Start web server
        port = 8888
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        
        logger.info(f"✅ Discord webhook service is running on port {port}")
        logger.info(f"✅ Listening for tweets from Discord channel {TWITTER_FEED_CHANNEL_ID}")
        logger.info(f"✅ Webhook URL: http://localhost:{port}/webhook")
        logger.info(f"✅ Status URL: http://localhost:{port}/status")
        logger.info(f"✅ Test URL: http://localhost:{port}/test")
        
        # Keep the service running until shutdown is requested
        while not shutdown_requested:
            await asyncio.sleep(1)
        
        # Shutdown web server
        logger.info("Stopping web server...")
        await runner.cleanup()
        
        return True
    except Exception as e:
        logger.error(f"Error in webhook service: {str(e)}")
        await shutdown()
        return False

async def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    
    logger.info("Starting Twitter Feed webhook service...")
    
    try:
        # Run the webhook service
        await run_webhook_service()
    except Exception as e:
        logger.error(f"Unhandled error in main: {str(e)}")
        await shutdown()
    finally:
        await shutdown()

if __name__ == "__main__":
    # Run the main function
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    finally:
        loop.close()