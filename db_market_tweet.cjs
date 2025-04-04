/**
 * Database-connected Market Tweet Generator
 * 
 * This script fetches real market data from the database and posts a tweet.
 */

require('dotenv').config();
const { Scraper } = require('agent-twitter-client');
const { Pool } = require('pg');

// Create database connection pool
const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

// Helper function to format date with EST timezone
function getFormattedDate() {
  // Create date object for EST timezone (UTC-5)
  const options = {
    timeZone: 'America/New_York',
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
    second: 'numeric',
    hour12: true
  };
  
  return new Intl.DateTimeFormat('en-US', options).format(new Date());
}

// Format price with 3 decimal places
function formatPrice(price) {
  if (!price) return '$0.000';
  return `$${parseFloat(price).toFixed(3)}`;
}

// Format percentage change with + for positive values
function formatPercentage(change) {
  if (!change) return '0.00%';
  const value = parseFloat(change);
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

// Format volume with commas and fixed decimal places
function formatVolume(volume) {
  if (!volume) return '$0';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(volume);
}

// Fetch the latest SONIC price data from the database
async function fetchLatestSonicData() {
  try {
    console.log('Fetching the latest SONIC price data from database...');
    
    // Connect to database
    const client = await pool.connect();
    
    // Check for market_data table that we know exists and has SONIC data
    const marketDataCheck = await client.query(`
      SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'market_data'
      );
    `);
    
    if (marketDataCheck.rows[0].exists) {
      console.log('Using market_data table for SONIC price information...');
      
      // Query for SONIC data from market_data
      const query = `
        SELECT 
          price::float AS price,
          price_change_24h::float AS price_change_24h,
          volume::float AS volume_24h,
          timestamp AS updated_at
        FROM market_data
        WHERE token = 'SONIC'
        ORDER BY timestamp DESC
        LIMIT 1
      `;
      
      const result = await client.query(query);
      client.release();
      
      if (result.rows.length > 0) {
        console.log('Found SONIC data in market_data:', result.rows[0]);
        return result.rows[0];
      }
    }
    
    // Try alternatives if market_data didn't work
    // Check for sonic_price_feed
    const sonicPriceFeedCheck = await client.query(`
      SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'sonic_price_feed'
      );
    `);
    
    if (sonicPriceFeedCheck.rows[0].exists) {
      console.log('Using sonic_price_feed table...');
      
      // Query for data from sonic_price_feed
      const query = `
        SELECT 
          price::float AS price,
          price_change_24h::float AS price_change_24h,
          volume::float AS volume_24h,
          updated_at
        FROM sonic_price_feed
        ORDER BY updated_at DESC
        LIMIT 1
      `;
      
      const result = await client.query(query);
      
      if (result.rows.length > 0) {
        console.log('Found data in sonic_price_feed:', result.rows[0]);
        client.release();
        return result.rows[0];
      }
    }
    
    // No suitable data found, use obviously fake fallback data
    console.warn('No SONIC price data found, using FAKE FALLBACK VALUES');
    client.release();
    return {
      price: 9.99,
      price_change_24h: 99.9,
      volume_24h: 9999999.00,
      updated_at: new Date()
    };
    
  } catch (error) {
    console.error('Error fetching SONIC data from database:', error.message);
    // Return obviously fake fallback data in case of error
    return {
      price: 9.99,
      price_change_24h: 99.9,
      volume_24h: 9999999.00,
      updated_at: new Date()
    };
  }
}

// Generate tweet with real-time data from database
async function generateMarketTweet() {
  // Fetch real data from database
  const marketData = await fetchLatestSonicData();
  
  // Get updated time in EST
  const updatedTime = marketData.updated_at ? 
    new Date(marketData.updated_at).toLocaleString('en-US', {
      timeZone: 'America/New_York'
    }) : getFormattedDate();
  
  // Generate tweet text with proper formatting
  const tweetText = `🚀 SONIC MARKET UPDATE 🚀

Price: ${formatPrice(marketData.price)} 
24h Change: ${formatPercentage(marketData.price_change_24h)} 📊
Volume: ${formatVolume(marketData.volume_24h)}

Data as of: ${updatedTime}
#BanditKid Tweet - ${getFormattedDate()}

#SONIC #DeFi #Crypto`;

  return tweetText;
}

async function postTweet() {
  try {
    // Generate the tweet content with real market data
    const tweetText = await generateMarketTweet();
    console.log('Generated tweet text:', tweetText);
    
    // Create a new scraper instance
    const scraper = new Scraper();
    console.log('Created new scraper instance');
    
    // Authenticate with credentials from environment variables
    console.log('Attempting login with environment credentials');
    await scraper.login(
      process.env.TWITTER_USERNAME,
      process.env.TWITTER_PASSWORD,
      process.env.TWITTER_EMAIL
    );
    
    // Check if login was successful
    const isLoggedIn = await scraper.isLoggedIn();
    console.log('Login successful?', isLoggedIn);
    
    if (!isLoggedIn) {
      console.error('Failed to authenticate with Twitter');
      process.exit(1);
    }
    
    // Post the tweet
    console.log('Posting tweet...');
    const result = await scraper.sendTweet(tweetText);
    console.log('Tweet posted successfully');
    
    // Close the database pool
    await pool.end();
    
    process.exit(0);
  } catch (error) {
    console.error('Error posting tweet:', error.message);
    console.error(error.stack);
    
    // Make sure to close the database pool on error
    try {
      await pool.end();
    } catch (e) {
      console.error('Error closing database pool:', e.message);
    }
    
    process.exit(1);
  }
}

// Run the function
postTweet();