
// Use CommonJS syntax for requiring the module
const twitterClient = require('agent-twitter-client');
const Scraper = twitterClient.Scraper;
const fs = require('fs');

async function getCookies() {
    try {
        // Initialize the scraper
        const scraper = new Scraper();
        
        // Use auth token directly
        await scraper.setCookies([
            {
                name: "auth_token",
                value: "d0e3dbfa1b5e520cc06c3890231b7acea1b19298",
                domain: ".twitter.com",
                path: "/",
                expires: -1,
                httpOnly: true,
                secure: true
            }
        ]);
        
        // Get and save cookies for verification
        const cookies = await scraper.getCookies();
        fs.writeFileSync('twitter_cookies.json', JSON.stringify(cookies, null, 2));
        console.log("Cookies saved to twitter_cookies.json");
        
    } catch (error) {
        console.error('Error:', error.message);
        process.exit(1);
    }
}

getCookies();
