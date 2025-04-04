// Simple script to test Twitter authentication with ElizaOS Twitter client
const twitterClient = require('agent-twitter-client');
const Scraper = twitterClient.Scraper;
const fs = require('fs');

async function testAuth() {
    try {
        // Initialize the scraper with debug options
        const scraper = new Scraper({ debug: true });
        
        // Try to get trends without authentication (public data)
        console.log("Attempting to get trends without auth...");
        try {
            const trends = await scraper.getTrends();
            console.log("Got trends without auth, count:", trends.length);
        } catch (e) {
            console.log("Could not get trends without auth:", e.message);
        }

        // Try search without auth
        console.log("Attempting search without auth...");
        try {
            const tweets = await scraper.searchTweets("bitcoin", 3);
            console.log("Search successful, found tweets:", tweets.length);
        } catch (e) {
            console.log("Search failed:", e.message);
        }

        console.log("Basic functionality test completed.");
    } catch (error) {
        console.error('Error:', error.message);
        process.exit(1);
    }
}

testAuth();
