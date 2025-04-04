/**
 * Twitter Post Script
 * 
 * This script posts a tweet to Twitter using the agent-twitter-client library.
 */

require('dotenv').config();
const { Scraper } = require('agent-twitter-client');

const tweetText = `🚀 SONIC MARKET UPDATE 🚀

Just aped into $SONIC @ $0.872 💰

24h Change: -2.53% 📊

Volume: $394,908.00

Testing tweet posting with our updated auth token! The market is looking interesting today. Let's see if this posts correctly!

#SONIC #DeFi #Crypto #Test`;

async function postTweet() {
  try {
    // Get auth token from environment variables
    const authToken = process.env.TWITTER_AUTH_TOKEN;
    if (!authToken) {
      console.error('TWITTER_AUTH_TOKEN not found in environment variables');
      process.exit(1);
    }

    console.log('Authenticating with Twitter...');
    const auth = { auth_token: authToken };
    const client = new Scraper(auth);
    
    // Check if authenticated
    const isAuthenticated = await client.isLoggedIn();
    if (!isAuthenticated) {
      console.error('Authentication failed');
      process.exit(1);
    }
    
    console.log('Authentication successful, posting tweet...');
    console.log(`Tweet content (${tweetText.length} chars):\n${tweetText}`);
    
    // Post the tweet
    const result = await client.tweet(tweetText);
    console.log('Tweet posted successfully:', JSON.stringify(result));
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
}

// Run the function
postTweet();