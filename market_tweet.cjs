/**
 * Market Tweet Script
 * 
 * This script generates and posts a market data tweet to Twitter.
 * It uses fixed data for testing purposes.
 */

require('dotenv').config();
const { Scraper } = require('agent-twitter-client');

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

// Sample market data for testing
const marketData = {
  price: 1.25,
  price_change_24h: 4.2,
  volume_24h: 1500000,
  updated_at: new Date()
};

// Format price with 3 decimal places
function formatPrice(price) {
  return `$${parseFloat(price).toFixed(3)}`;
}

// Format percentage change with + for positive values
function formatPercentage(change) {
  const value = parseFloat(change);
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

// Format volume with commas and fixed decimal places
function formatVolume(volume) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(volume);
}

// Generate tweet text
function generateMarketTweet() {
  // Get updated time in EST
  const updatedTime = getFormattedDate();
  
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
    // Generate the tweet content
    const tweetText = generateMarketTweet();
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
    
    process.exit(0);
  } catch (error) {
    console.error('Error posting tweet:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

// Run the function
postTweet();