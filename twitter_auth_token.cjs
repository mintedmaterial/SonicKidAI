/**
 * Twitter Authentication with Auth Token
 * 
 * This script authenticates with Twitter using the auth token approach.
 */

const { Scraper } = require('agent-twitter-client');

async function authenticateWithToken() {
    try {
        // Log environment variables being used (without showing values)
        console.log('Using auth token from environment');
        
        // Create a new scraper instance
        const scraper = new Scraper();
        console.log('Created new scraper instance');
        
        // The auth token should be in the environment variable
        const authToken = process.env.TWITTER_AUTH_TOKEN;
        
        if (!authToken) {
            console.error('TWITTER_AUTH_TOKEN environment variable is not set');
            process.exit(1);
        }
        
        // Try using the loginTwitterToken method from the library
        // This appears to be a specific method for token-based authentication
        await scraper.loginTwitterToken(authToken);
        console.log('Used loginTwitterToken method for authentication');
        
        // Check if login was successful
        const isLoggedIn = await scraper.isLoggedIn();
        console.log('Login successful?', isLoggedIn);
        
        if (isLoggedIn) {
            // Get user profile
            try {
                const profile = await scraper.me();
                console.log('User profile:', JSON.stringify(profile, null, 2));
            } catch (profileError) {
                console.error('Error getting profile, but login was successful:', profileError.message);
                // Continue with exit code 0 since login was successful
            }
        }
        
        process.exit(isLoggedIn ? 0 : 1);
    } catch (error) {
        console.error('Error during authentication:', error.message);
        console.error(error.stack);
        process.exit(1);
    }
}

authenticateWithToken();