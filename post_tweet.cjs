/**
 * Twitter Post Script
 * 
 * This script posts a tweet to Twitter using the agent-twitter-client library.
 */

require('dotenv').config();
const { Scraper } = require('agent-twitter-client');
const fs = require('fs');

const tweetText = `🚀 SONIC MARKET UPDATE 🚀

Just aped into $SONIC @ $0.872 💰

24h Change: -2.53% 📊

Volume: $394,908.00

Testing tweet posting with our updated auth token! The market is looking interesting today. Let's see if this posts correctly!

#SONIC #DeFi #Crypto #Test`;

async function postTweet() {
  try {
    // Use the auth token provided directly
    const authToken = "30a88ac3c27a5a2b88742e38d6cbe71cf3663cb3";
    console.log('Using auth token:', authToken);
    
    // Use cookies with the auth token directly
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
    console.log('Using cookies:', cookies);
    
    console.log('Authenticating with Twitter...');
    // Try both authentication methods
    let client;
    let isAuthenticated = false;
    
    try {
      // Method 1: Use auth_token
      console.log('Trying auth_token authentication...');
      client = new Scraper({ auth_token: authToken });
      isAuthenticated = await client.isLoggedIn();
      console.log('Auth token authentication result:', isAuthenticated);
    } catch (e) {
      console.error('Error with auth_token authentication:', e.message);
    }
    
    if (!isAuthenticated && cookies) {
      try {
        // Method 2: Use cookies
        console.log('Trying cookies authentication...');
        client = new Scraper({ cookies });
        isAuthenticated = await client.isLoggedIn();
        console.log('Cookies authentication result:', isAuthenticated);
      } catch (e) {
        console.error('Error with cookies authentication:', e.message);
      }
    }
    
    if (!isAuthenticated) {
      // Method 3: Try the username/password approach
      try {
        console.log('Trying username/password authentication...');
        const username = "MintedMaterial";
        const password = "Myrecovery@1";
        const email = "MintedMaterial@gmail.com";
        
        console.log(`Using credentials: ${username}, ${email}`);
        client = new Scraper({ username, password, email });
        isAuthenticated = await client.isLoggedIn();
        console.log('Username/password authentication result:', isAuthenticated);
      } catch (e) {
        console.error('Error with username/password authentication:', e.message);
      }
    }
    
    if (!isAuthenticated) {
      console.error('All authentication methods failed');
      process.exit(1);
    }
    
    console.log('Authentication successful, posting tweet...');
    console.log(`Tweet content (${tweetText.length} chars):\n${tweetText}`);
    
    // Post the tweet
    const result = await client.tweet(tweetText);
    console.log('Tweet posted successfully:', JSON.stringify(result));
  } catch (error) {
    console.error('Error:', error.message);
    // Print the stack trace for debugging
    console.error(error.stack);
    process.exit(1);
  }
}

// Run the function
postTweet();