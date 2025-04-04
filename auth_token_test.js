// Auth Token Test
// This script tests Twitter authentication using only the auth token

import { Scraper } from 'agent-twitter-client';

// We'll try both auth tokens to be sure
const AUTH_TOKEN_1 = "30a88ac3c27a5a2b88742e38d6cbe71cf3663cb3";
const AUTH_TOKEN_2 = "4371764d7a20e8c3f3acccb9b0b2e335f81ca074";

// Test tweet text
const tweetText = `Market Update: SONIC trading at $0.872 with moderate volume. 
Market sentiment: bullish on recent developments.

#SONIC #DeFi #Crypto #Test`;

async function testAuthToken(authToken) {
  try {
    console.log(`\nTesting with auth token: ${authToken}`);
    // Create a new scraper instance with auth token
    const scraper = new Scraper({ auth_token: authToken });
    console.log('Created new scraper instance');
    
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
      
      return true;
    } else {
      console.error('Failed to log in to Twitter with auth token');
      return false;
    }
  } catch (error) {
    console.error('Error during auth token test:', error.message);
    console.error(error.stack);
    return false;
  }
}

// Run the test with both tokens
async function testBothTokens() {
  let success = await testAuthToken(AUTH_TOKEN_1);
  if (!success) {
    success = await testAuthToken(AUTH_TOKEN_2);
  }
  
  if (success) {
    console.log('\nSuccessfully authenticated with Twitter!');
  } else {
    console.error('\nFailed to authenticate with either auth token.');
  }
}

// Run the function
testBothTokens();