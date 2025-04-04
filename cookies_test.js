// Cookies Test
// This script tests Twitter authentication using cookies

import { Scraper } from 'agent-twitter-client';

// Test tweet text
const tweetText = `Market Update: SONIC trading at $0.872 with moderate volume. 
Market sentiment: bullish on recent developments.

#SONIC #DeFi #Crypto #Test`;

// Create the cookies array with auth token
const cookies = [
  {
    name: 'auth_token',
    value: '30a88ac3c27a5a2b88742e38d6cbe71cf3663cb3',
    domain: '.twitter.com',
    path: '/',
    expires: -1,
    httpOnly: true,
    secure: true
  }
];

async function testCookies() {
  try {
    console.log('Testing with cookies:', JSON.stringify(cookies, null, 2));
    
    // Create a new scraper instance with cookies
    const scraper = new Scraper({ cookies });
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
      const updatedCookies = await scraper.getCookies();
      console.log('Updated cookies for future use:', JSON.stringify(updatedCookies));
    } else {
      console.error('Failed to log in to Twitter with cookies');
    }
  } catch (error) {
    console.error('Error during cookies test:', error.message);
    console.error(error.stack);
  }
}

// Run the function
testCookies();