
const { Scraper } = require('agent-twitter-client');

async function postTweet() {
  try {
    console.log('Attempting to post tweet...');
    
    // Get credentials from environment
    const username = process.env.TWITTER_USERNAME;
    const password = process.env.TWITTER_PASSWORD;
    const email = process.env.TWITTER_EMAIL;
    
    if (!username || !password || !email) {
      console.error('Missing Twitter credentials in environment variables');
      process.exit(1);
    }
    
    // Create a new scraper instance
    const scraper = new Scraper();
    
    // Login with username/password/email
    console.log(`Logging in as ${username}...`);
    await scraper.login(username, password, email);
    
    console.log('Login successful!');
    
    // Tweet text to post
    const tweetText = "#BanditKid $SONIC Market Update - Apr 04 \ud83d\udcc9\n\n\ud83d\udcb0 Price: $0.495 (-2.53%)\n\ud83d\udcca 24h Volume: $394,908.03\n\nHODL strong! \ud83d\udcaa #Sonic #SOL #Crypto #DeFi";
    
    // Post the tweet
    console.log('Posting tweet...');
    const result = await scraper.sendTweet(tweetText);
    
    console.log('Tweet posted successfully!');
    console.log('TWEET_SUCCESS');
    process.exit(0);
  } catch (error) {
    console.error('Error posting tweet:', error);
    process.exit(1);
  }
}

postTweet();
