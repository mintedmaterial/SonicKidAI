// Simple script to test Twitter authentication with ElizaOS Twitter client
const twitterClient = require('agent-twitter-client');
const Scraper = twitterClient.Scraper;

async function testAuth() {
    try {
        // Initialize the scraper
        const scraper = new Scraper();
        
        // Login with username/password 
        console.log("Attempting to log in...");
        await scraper.login('MintedMaterial', process.argv[2]);
        
        // Test getting public data
        console.log("Getting trends...");
        const trends = await scraper.getTrends();
        console.log("Successfully retrieved trends");
        
        // Get cookies for future use
        console.log("Getting cookies...");
        const cookies = await scraper.getCookies();
        console.log("Cookies retrieved:", JSON.stringify(cookies));
        
        console.log("Test completed successfully");
    } catch (error) {
        console.error('Error:', error.message);
        process.exit(1);
    }
}

if (process.argv.length < 3) {
    console.error("Please provide your Twitter password as a command line argument");
    process.exit(1);
}

testAuth();
