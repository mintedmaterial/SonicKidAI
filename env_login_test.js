// Environment Login Test
// This script tests Twitter authentication using environment variables

import * as dotenv from 'dotenv';
import { Scraper } from 'agent-twitter-client';

// Load .env file
dotenv.config();

// Test tweet text
const tweetText = `Market Update: SONIC trading at $0.872 with moderate volume. 
Market sentiment: bullish on recent developments.

#SONIC #DeFi #Crypto #Test`;

async function testEnvLogin() {
  try {
    // Log environment variables (but not their values)
    console.log('Environment variables used for login:');
    console.log('- TWITTER_USERNAME: ' + (process.env.TWITTER_USERNAME ? 'Set' : 'Not set'));
    console.log('- TWITTER_PASSWORD: ' + (process.env.TWITTER_PASSWORD ? 'Set' : 'Not set'));
    console.log('- TWITTER_EMAIL: ' + (process.env.TWITTER_EMAIL ? 'Set' : 'Not set'));
    console.log('- TWITTER_AUTH_TOKEN: ' + (process.env.TWITTER_AUTH_TOKEN ? 'Set' : 'Not set'));
    
    // Set environment variables manually as fallback
    process.env.TWITTER_USERNAME = process.env.TWITTER_USERNAME || "MintedMaterial";
    process.env.TWITTER_PASSWORD = process.env.TWITTER_PASSWORD || "Myrecovery@1";
    process.env.TWITTER_EMAIL = process.env.TWITTER_EMAIL || "MintedMaterial@gmail.com";
    process.env.TWITTER_AUTH_TOKEN = process.env.TWITTER_AUTH_TOKEN || "30a88ac3c27a5a2b88742e38d6cbe71cf3663cb3";
    
    // Create a new scraper instance
    console.log('Creating new scraper instance');
    const scraper = new Scraper();
    
    // Login using environment variables
    console.log('Logging in with credentials from environment variables');
    await scraper.login(
      process.env.TWITTER_USERNAME,
      process.env.TWITTER_PASSWORD,
      process.env.TWITTER_EMAIL
    );
    
    // Check if login was successful
    const isLoggedIn = await scraper.isLoggedIn();
    console.log('Login successful?', isLoggedIn);
    
    if (isLoggedIn) {
      console.log('Getting user profile...');
      const profile = await scraper.me();
      console.log('Profile:', JSON.stringify(profile, null, 2));
      
      console.log('Posting tweet...');
      const result = await scraper.sendTweet(tweetText);
      console.log('Tweet posted successfully:', JSON.stringify(result));
      
      // Get the cookies for future use
      const cookies = await scraper.getCookies();
      console.log('Cookies for future use:', JSON.stringify(cookies));
    } else {
      console.error('Failed to log in to Twitter with environment variables');
    }
  } catch (error) {
    console.error('Error during environment login test:', error.message);
    console.error(error.stack);
  }
}

// Run the function
testEnvLogin();