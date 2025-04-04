/**
 * Setup Twitter Authentication Script
 * 
 * This script provides helper functions to authenticate with Twitter
 * using either credentials or auth token cookies.
 */

const { Scraper } = require('agent-twitter-client');

/**
 * Authenticate with Twitter using auth token
 * @param {string} authToken - Twitter auth token
 * @returns {Promise<{success: boolean, message: string, cookies: Array<any>}>}
 */
async function authenticateWithToken(authToken) {
  try {
    console.log('Creating Twitter scraper...');
    const scraper = new Scraper({ debug: true });
    
    // Create the auth token cookie
    console.log('Setting auth token cookie...');
    const cookie = {
      name: 'auth_token',
      value: authToken,
      domain: '.twitter.com',
      path: '/',
      expires: -1,
      httpOnly: true,
      secure: true
    };
    
    // Set the cookie
    await scraper.setCookies([cookie]);
    
    // Check if we're logged in
    console.log('Checking authentication status...');
    const isLoggedIn = await scraper.isLoggedIn();
    
    if (isLoggedIn) {
      // Get full cookies if logged in successfully
      const cookies = await scraper.getCookies();
      return {
        success: true, 
        message: 'Successfully authenticated with auth token',
        cookies
      };
    } else {
      return {
        success: false,
        message: 'Failed to authenticate with auth token',
        cookies: []
      };
    }
  } catch (error) {
    return {
      success: false,
      message: `Error during authentication: ${error.message}`,
      cookies: []
    };
  }
}

/**
 * Authenticate with Twitter using credentials
 * @param {string} username - Twitter username
 * @param {string} password - Twitter password
 * @param {string} email - Twitter email
 * @returns {Promise<{success: boolean, message: string, cookies: Array<any>}>}
 */
async function authenticateWithCredentials(username, password, email) {
  try {
    console.log('Creating Twitter scraper...');
    const scraper = new Scraper({ debug: true });
    
    // Login with credentials
    console.log('Logging in with credentials...');
    await scraper.login(username, password, email);
    
    // Check if we're logged in
    console.log('Checking authentication status...');
    const isLoggedIn = await scraper.isLoggedIn();
    
    if (isLoggedIn) {
      // Get cookies if logged in successfully
      const cookies = await scraper.getCookies();
      return {
        success: true,
        message: 'Successfully authenticated with credentials',
        cookies
      };
    } else {
      return {
        success: false,
        message: 'Failed to authenticate with credentials',
        cookies: []
      };
    }
  } catch (error) {
    return {
      success: false,
      message: `Error during authentication: ${error.message}`,
      cookies: []
    };
  }
}

/**
 * Test Twitter functions without authentication
 * @returns {Promise<{success: boolean, message: string}>}
 */
async function testWithoutAuth() {
  try {
    console.log('Creating Twitter scraper...');
    const scraper = new Scraper({ debug: true });
    
    // Try to get trends (which doesn't require auth)
    console.log('Getting trends...');
    const trends = await scraper.getTrends();
    
    if (trends && trends.length > 0) {
      return {
        success: true,
        message: `Successfully retrieved ${trends.length} trends without authentication`,
        trends: trends.slice(0, 5) // Return first 5 trends
      };
    } else {
      return {
        success: false,
        message: 'Failed to retrieve trends without authentication',
        trends: []
      };
    }
  } catch (error) {
    return {
      success: false,
      message: `Error during trends test: ${error.message}`,
      trends: []
    };
  }
}

// Export functions for use in other scripts
module.exports = {
  authenticateWithToken,
  authenticateWithCredentials,
  testWithoutAuth
};

// If this script is run directly, execute the test function
if (require.main === module) {
  // Get auth token from command line or environment
  const authToken = process.argv[2] || process.env.TWITTER_AUTH_TOKEN;
  
  if (authToken) {
    console.log('Testing authentication with auth token...');
    authenticateWithToken(authToken)
      .then(result => {
        console.log('AUTH_RESULT:', JSON.stringify(result, null, 2));
      })
      .catch(error => {
        console.error('Error:', error.message);
      });
  } else {
    console.log('Testing without authentication...');
    testWithoutAuth()
      .then(result => {
        console.log('TEST_RESULT:', JSON.stringify(result, null, 2));
      })
      .catch(error => {
        console.error('Error:', error.message);
      });
  }
}