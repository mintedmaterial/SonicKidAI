/**
 * Twitter Client Test
 * 
 * This script tests the Twitter client functionality directly from Node.js
 */

const { Scraper } = require('agent-twitter-client');

async function testTwitterClient() {
    try {
        console.log('Testing Twitter client...');
        
        // Create a new scraper instance
        const scraper = new Scraper();
        console.log('Created new scraper instance');
        
        // Login with credentials
        console.log('Attempting to login with environment credentials');
        await scraper.login(
            process.env.TWITTER_USERNAME,
            process.env.TWITTER_PASSWORD,
            process.env.TWITTER_EMAIL
        );
        
        // Check if login was successful
        const isLoggedIn = await scraper.isLoggedIn();
        console.log('Login successful?', isLoggedIn);
        
        if (isLoggedIn) {
            // Get user profile
            const profile = await scraper.me();
            console.log('User profile:', JSON.stringify(profile, null, 2));
            
            // Generate a test tweet
            const date = new Date().toLocaleString();
            const tweetText = `#BanditKid Test Tweet - ${date}\n\nThis is a test tweet from Node.js.\n\n#Test #Automation`;
            console.log(`Tweet content (${tweetText.length} chars):\n${tweetText}`);
            
            // Post the tweet
            console.log('Posting tweet...');
            const result = await scraper.sendTweet(tweetText);
            console.log('Tweet posted successfully:', JSON.stringify(result));
        } else {
            console.error('Failed to log in to Twitter');
            process.exit(1);
        }
    } catch (error) {
        console.error('Error during Twitter test:', error.message);
        console.error(error.stack);
        process.exit(1);
    }
}

// Run the test
testTwitterClient();