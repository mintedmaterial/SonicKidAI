/**
 * Twitter Authentication Script
 * 
 * This script authenticates with Twitter and validates credentials.
 * Enhanced with better debugging and error handling.
 */

const { Scraper } = require('agent-twitter-client');

async function authenticate() {
    try {
        // Log environment variables being used (without showing values)
        console.log('Using environment variables:');
        console.log('- TWITTER_USERNAME: ' + (process.env.TWITTER_USERNAME ? 'Set' : 'Not set'));
        console.log('- TWITTER_PASSWORD: ' + (process.env.TWITTER_PASSWORD ? 'Set' : 'Not set'));
        console.log('- TWITTER_EMAIL: ' + (process.env.TWITTER_EMAIL ? 'Set' : 'Not set'));
        
        // Validate that all required variables are set
        if (!process.env.TWITTER_USERNAME || !process.env.TWITTER_PASSWORD || !process.env.TWITTER_EMAIL) {
            console.error('ERROR: One or more required environment variables are not set');
            process.exit(1);
        }
        
        // Create a new scraper instance
        const scraper = new Scraper();
        console.log('Created new scraper instance');
        
        // Login with credentials - wrapped in try/catch for better error reporting
        console.log('Attempting to login with environment credentials');
        try {
            await scraper.login(
                process.env.TWITTER_USERNAME,
                process.env.TWITTER_PASSWORD,
                process.env.TWITTER_EMAIL
            );
            console.log('Login method completed without throwing');
        } catch (loginError) {
            console.error('ERROR during login step:', loginError.message);
            console.error(loginError.stack);
            process.exit(1);
        }
        
        // Check if login was successful
        console.log('Checking login status...');
        const isLoggedIn = await scraper.isLoggedIn();
        console.log('Login successful?', isLoggedIn);
        
        if (isLoggedIn) {
            // Get user profile
            try {
                console.log('Getting user profile...');
                const profile = await scraper.me();
                console.log('User profile:', JSON.stringify(profile, null, 2));
                
                // Get the cookies for future use
                console.log('Getting cookies...');
                const cookies = await scraper.getCookies();
                
                // Log the count and types of cookies (without exposing values)
                console.log(`Retrieved ${cookies.length} cookies`);
                const cookieNames = cookies.map(c => c.key).join(', ');
                console.log(`Cookie names: ${cookieNames}`);
                
                // Check specifically for auth_token
                const authCookie = cookies.find(c => c.key === 'auth_token');
                if (authCookie) {
                    console.log('✓ Found auth_token cookie');
                } else {
                    console.log('⚠ No auth_token cookie found');
                }
            } catch (profileError) {
                console.error('Error getting profile, but login was successful:', profileError.message);
                // Continue with exit code 0 since login was successful
            }
        }
        
        process.exit(isLoggedIn ? 0 : 1);
    } catch (error) {
        console.error('ERROR during authentication (outer try/catch):', error.message);
        console.error(error.stack);
        process.exit(1);
    }
}

authenticate();