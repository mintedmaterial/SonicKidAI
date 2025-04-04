// Direct Login Test
// This script attempts to directly log in to Twitter using the agent-twitter-client

import { Scraper } from 'agent-twitter-client';

const AUTH_TOKEN = "30a88ac3c27a5a2b88742e38d6cbe71cf3663cb3";
const USERNAME = "MintedMaterial";
const PASSWORD = "Myrecovery@1";
const EMAIL = "MintedMaterial@gmail.com";

// Test tweet text
const tweetText = `Market Update: SONIC trading at $0.872 with moderate volume. 
Market sentiment: bullish on recent developments.

#SONIC #DeFi #Crypto #Test`;

async function testDirectLogin() {
  try {
    // Create a new scraper instance
    const scraper = new Scraper();
    console.log('Created new scraper instance');
    
    // Attempt login with username/password
    console.log(`Attempting to login with username: ${USERNAME}, email: ${EMAIL}`);
    await scraper.login(USERNAME, PASSWORD, EMAIL);
    
    // Check if login was successful
    const isLoggedIn = await scraper.isLoggedIn();
    console.log('Login successful?', isLoggedIn);
    
    if (isLoggedIn) {
      console.log('Posting tweet...');
      const result = await scraper.sendTweet(tweetText);
      console.log('Tweet posted successfully:', JSON.stringify(result));
      
      // Get the cookies for future use
      const cookies = await scraper.getCookies();
      console.log('Cookies for future use:', JSON.stringify(cookies));
    } else {
      console.error('Failed to log in to Twitter');
    }
  } catch (error) {
    console.error('Error during direct login test:', error.message);
    console.error(error.stack);
  }
}

// Run the function
testDirectLogin();