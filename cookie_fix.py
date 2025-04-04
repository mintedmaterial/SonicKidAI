import os
import subprocess

# Let's get the Twitter username/password and auth token directly for testing
auth_token = "d0e3dbfa1b5e520cc06c3890231b7acea1b19298"

# Create a JavaScript file that will use the Twitter client to log in and export cookies
with open('get_cookies.cjs', 'w') as f:
    f.write('''
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
                value: "''' + auth_token + '''",
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
''')

print("Created cookie script, running...")
# Run the Node.js script to get the cookies
subprocess.run(['node', 'get_cookies.cjs'], check=True)
print("Script completed, now updating .env file")

# Read the generated cookies
try:
    with open('twitter_cookies.json', 'r') as f:
        cookie_data = f.read().strip()
        
    # Update the .env file with the proper cookies format
    subprocess.run([
        'sed', '-i', 
        '/TWITTER_COOKIES=/c\\TWITTER_COOKIES=' + cookie_data.replace('\n', '\\n'),
        '.env'
    ])
    print("Updated .env file with proper cookie format")
except FileNotFoundError:
    print("Cookie file not found, could not update .env")
