"""
Twitter Market Tweet Test

This script tests posting a market update tweet using the agent-twitter-client.
"""

import os
import asyncio
import json
import subprocess
from datetime import datetime
import logging
from decimal import Decimal
from typing import Dict, Any, Optional

# Try to import optional dependencies
try:
    import asyncpg
except ImportError:
    asyncpg = None

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        """Dummy function if dotenv is not available"""
        print("python-dotenv not available, using environment variables as is")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def get_sonic_market_data() -> Dict[str, Any]:
    """Get SONIC market data from the database"""
    # If asyncpg is not available, use Node.js to fetch data from the database
    if asyncpg is None:
        logger.warning("asyncpg not available, using Node.js to fetch market data")
        return await get_market_data_via_nodejs()
    
    try:
        logger.info("Connecting to database with asyncpg...")
        conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
        
        # Check if market_data table exists
        table_check = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'market_data'
            );
        """)
        
        if table_check:
            logger.info("Fetching SONIC data from market_data table...")
            market_data = await conn.fetchrow("""
                SELECT 
                    price::float as price,
                    price_change_24h::float as price_change_24h,
                    volume::float as volume_24h,
                    timestamp as updated_at
                FROM market_data
                WHERE token = 'SONIC'
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            
            if market_data:
                logger.info(f"Found SONIC data: {market_data}")
                result = dict(market_data)
                await conn.close()
                return result
        
        # If we reach here, no data was found
        logger.warning("No SONIC data found in database with asyncpg, using backup method")
        await conn.close()
        return await get_market_data_via_nodejs()
        
    except Exception as e:
        logger.error(f"Error fetching market data with asyncpg: {str(e)}")
        return await get_market_data_via_nodejs()

async def get_market_data_via_nodejs() -> Dict[str, Any]:
    """Get market data via Node.js using a subprocess call"""
    try:
        logger.info("Fetching market data using Node.js...")
        # Create a temporary file to store the output
        temp_output_file = "market_data_output.json"
        
        # Node.js script to fetch market data and write to file
        node_script = f'''
        require('dotenv').config();
        const {{ Pool }} = require('pg');

        async function fetchMarketData() {{
          const pool = new Pool({{
            connectionString: process.env.DATABASE_URL
          }});
          
          try {{
            const client = await pool.connect();
            const result = await client.query(`
              SELECT 
                price::float as price,
                price_change_24h::float as price_change_24h,
                volume::float as volume_24h,
                timestamp as updated_at
              FROM market_data
              WHERE token = 'SONIC'
              ORDER BY timestamp DESC
              LIMIT 1
            `);
            
            client.release();
            await pool.end();
            
            if (result.rows.length > 0) {{
              const fs = require('fs');
              fs.writeFileSync('{temp_output_file}', JSON.stringify(result.rows[0]));
              console.log('Market data fetched successfully');
              return true;
            }} else {{
              console.log('No market data found');
              return false;
            }}
          }} catch (error) {{
            console.error('Error:', error.message);
            await pool.end();
            return false;
          }}
        }}

        fetchMarketData();
        '''
        
        # Write script to temporary file - using .cjs extension for CommonJS
        node_script_file = "fetch_market_data.cjs"
        with open(node_script_file, "w") as f:
            f.write(node_script)
        
        # Execute the Node.js script
        logger.info("Running Node.js script to fetch market data...")
        process = subprocess.run(["node", node_script_file], capture_output=True, text=True)
        
        if process.returncode == 0 and "Market data fetched successfully" in process.stdout:
            # Read the data from output file
            if os.path.exists(temp_output_file):
                with open(temp_output_file, "r") as f:
                    market_data = json.load(f)
                
                logger.info(f"Successfully fetched market data via Node.js: {market_data}")
                
                # Clean up temporary files
                try:
                    os.remove(temp_output_file)
                    os.remove(node_script_file)
                except:
                    pass
                    
                return market_data
        
        # If we reach here, something went wrong
        logger.error(f"Failed to fetch market data via Node.js. Output: {process.stdout}")
        if process.stderr:
            logger.error(f"Error: {process.stderr}")
    except Exception as e:
        logger.error(f"Error fetching market data via Node.js: {str(e)}")
    
    # Return fallback data if all methods fail - deliberately different from real values
    logger.warning("Using OBVIOUSLY FAKE fallback market data")
    return {
        "price": 9.99,
        "price_change_24h": 99.9,
        "volume_24h": 9999999,
        "updated_at": datetime.now()
    }

def format_price(price: float) -> str:
    """Format price with 3 decimal places"""
    return f"${price:.3f}"

def format_percentage(change: float) -> str:
    """Format percentage change with + for positive values"""
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.2f}%"

def format_volume(volume: float) -> str:
    """Format volume with commas and fixed decimal places"""
    return f"${int(volume):,}"

def get_formatted_date() -> str:
    """Get formatted date in EST timezone"""
    from datetime import datetime
    import pytz
    
    # Get current time in EST
    est = pytz.timezone('America/New_York')
    now = datetime.now(est)
    
    # Format the date
    return now.strftime("%m/%d/%Y, %I:%M:%S %p")

async def generate_market_tweet(market_data: Dict[str, Any]) -> str:
    """Generate a tweet with market data"""
    # Format the updated time
    updated_time = market_data["updated_at"]
    if isinstance(updated_time, datetime):
        import pytz
        est = pytz.timezone('America/New_York')
        updated_time = updated_time.astimezone(est).strftime("%m/%d/%Y, %I:%M:%S %p")
    
    # Generate tweet text
    tweet_text = f"""🚀 SONIC MARKET UPDATE 🚀

Price: {format_price(market_data["price"])}
24h Change: {format_percentage(market_data["price_change_24h"])} 📊
Volume: {format_volume(market_data["volume_24h"])}

Data as of: {updated_time}
#BanditKid Tweet - {get_formatted_date()}

#SONIC #DeFi #Crypto"""

    return tweet_text

async def post_tweet(tweet_text: str) -> bool:
    """Post a tweet using Node.js script for agent-twitter-client"""
    try:
        # Instead of using Python module (which isn't available), 
        # we'll save the tweet content to a file and use the Node.js script
        
        # Save tweet content to a temporary file
        temp_tweet_file = "temp_tweet_content.txt"
        with open(temp_tweet_file, "w") as f:
            f.write(tweet_text)
        
        logger.info(f"Saved tweet content to {temp_tweet_file}")
        
        # Execute the Node.js script to post the tweet
        import subprocess
        
        # Command to run the Node.js script with the tweet content from file
        cmd = f'node -e "require(\\"dotenv\\").config(); const fs = require(\\"fs\\"); const {{ Scraper }} = require(\\"agent-twitter-client\\"); async function postTweet() {{ try {{ const tweetText = fs.readFileSync(\\"{temp_tweet_file}\\", \\"utf8\\"); const scraper = new Scraper(); await scraper.login(process.env.TWITTER_USERNAME, process.env.TWITTER_PASSWORD, process.env.TWITTER_EMAIL); const isLoggedIn = await scraper.isLoggedIn(); if (isLoggedIn) {{ await scraper.sendTweet(tweetText); console.log(\\"Tweet posted successfully\\"); }} else {{ console.error(\\"Login failed\\"); }} }} catch (error) {{ console.error(\\"Error posting tweet:\\", error.message); }} }} postTweet();"'
        
        logger.info("Executing Node.js script to post tweet...")
        process = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if process.returncode == 0:
            logger.info("Node.js script executed successfully")
            logger.info(f"Output: {process.stdout}")
            
            # Check if the output indicates success
            if "Tweet posted successfully" in process.stdout:
                logger.info("Tweet posted successfully via Node.js")
                return True
            else:
                logger.warning(f"Tweet may not have been posted. Output: {process.stdout}")
                if process.stderr:
                    logger.error(f"Error output: {process.stderr}")
                return False
        else:
            logger.error(f"Node.js script failed with return code {process.returncode}")
            logger.error(f"Error output: {process.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error posting tweet: {str(e)}")
        return False

async def main():
    """Main function"""
    try:
        # Get market data
        market_data = await get_sonic_market_data()
        
        # Generate tweet text
        tweet_text = await generate_market_tweet(market_data)
        logger.info(f"Generated tweet:\n{tweet_text}")
        
        # Post the tweet
        success = await post_tweet(tweet_text)
        
        if success:
            logger.info("Tweet posted successfully!")
        else:
            logger.error("Failed to post tweet")
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())