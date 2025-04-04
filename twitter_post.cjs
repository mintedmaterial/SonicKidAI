/**
 * Twitter Post Script
 * 
 * This script posts a tweet to Twitter using content from a file.
 * The file containing the tweet text is passed as the first command-line argument.
 */

const { Scraper } = require('agent-twitter-client');
const fs = require('fs');

async function postTweet() {
    try {
        // Get the path to the tweet file
        const tweetFilePath = process.argv[2];
        
        if (!tweetFilePath) {
            console.error('No tweet file provided. Usage: node twitter_post.cjs tweet.txt');
            process.exit(1);
        }
        
        // Read tweet text from file
        const tweetText = fs.readFileSync(tweetFilePath, 'utf8');
        
        if (!tweetText.trim()) {
            console.error('Tweet file is empty');
            process.exit(1);
        }
        
        // Create a new scraper instance
        const scraper = new Scraper();
        console.log('Created new scraper instance');
        
        // Login with credentials
        console.log('Logging in with credentials from environment variables');
        await scraper.login(
            process.env.TWITTER_USERNAME,
            process.env.TWITTER_PASSWORD,
            process.env.TWITTER_EMAIL
        );
        
        // Check if login was successful
        const isLoggedIn = await scraper.isLoggedIn();
        console.log('Login successful?', isLoggedIn);
        
        if (!isLoggedIn) {
            console.error('Failed to log in to Twitter');
            process.exit(1);
        }
        
        // Tweet content
        console.log(`Tweet content (${tweetText.length} chars):\n${tweetText}`);
        
        // Post the tweet
        console.log('Posting tweet...');
        const result = await scraper.sendTweet(tweetText);
        console.log('Tweet posted successfully:', JSON.stringify(result));
        process.exit(0);
    } catch (error) {
        console.error('Error posting tweet:', error.message);
        console.error(error.stack);
        process.exit(1);
    }
}

postTweet();