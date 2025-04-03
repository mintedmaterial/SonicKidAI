import { Router } from 'express';
import { z } from 'zod';
import { db } from '../db';
import { desc, sql } from 'drizzle-orm';
import { twitterScrapeData, insertTwitterScrapeDataSchema } from '@shared/schema';
import axios from 'axios';
import { AnthropicService } from '../services/anthropic_service';

const router = Router();

// Database-backed storage for tweets (replacing in-memory storage)
const MAX_TWEETS = 10;

// Schema validation for Discord webhook payload
const discordWebhookSchema = z.object({
  content: z.string(),
  embeds: z.array(z.object({
    title: z.string().optional(),
    description: z.string().optional(),
    timestamp: z.string().optional(),
    author: z.object({
      name: z.string().optional(),
      icon_url: z.string().optional(),
      url: z.string().optional()
    }).optional()
  })).optional()
});

// Format tweet from Discord webhook
const formatTweetFromDiscord = (payload: any) => {
  // This implementation extracts tweet data from the Discord webhook
  // and formats it to match the TwitterFeed component's expected schema
  
  const generateId = () => `tweet-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
  
  // If there are embeds present, we may have more structured data
  if (payload.embeds && payload.embeds.length > 0) {
    const embed = payload.embeds[0];
    
    // Use the embed's timestamp or current time
    const timestamp = embed.timestamp || new Date().toISOString();
    
    // Extract author information
    let username = 'crypto_user';
    let name = 'Crypto User';
    let profileImage = null;
    
    if (embed.author) {
      // Handle author in format "Name@username"
      if (embed.author.name && embed.author.name.includes('@')) {
        const authorParts = embed.author.name.split('@');
        name = authorParts[0].trim();
        username = authorParts[1].trim();
      } else if (embed.author.name) {
        name = embed.author.name;
        // Create username from name if not provided
        username = name.toLowerCase().replace(/\s+/g, '_');
      }
      
      profileImage = embed.author.icon_url;
    }
    
    // Use embed description or fall back to payload content
    const tweetText = embed.description || payload.content;
    
    return {
      id: generateId(),
      text: tweetText,
      author: {
        username: username,
        name: name,
        profile_image_url: profileImage
      },
      created_at: timestamp,
      public_metrics: {
        reply_count: 0,
        retweet_count: 0,
        like_count: 0
      }
    };
  }
  
  // Fallback to using content with minimal formatting
  // Look for hashtags and mentions in the content to infer topic/author
  const content = payload.content || '';
  let username = 'crypto_updates';
  let name = 'Crypto Updates';
  
  // Check for $TICKER pattern to infer topic
  const tickerMatch = content.match(/\$([A-Z]+)/);
  if (tickerMatch && tickerMatch[1]) {
    const ticker = tickerMatch[1];
    username = ticker.toLowerCase() + '_updates';
    name = ticker + ' Updates';
  }
  
  return {
    id: generateId(),
    text: content,
    author: {
      username: username,
      name: name,
      profile_image_url: null
    },
    created_at: new Date().toISOString(),
    public_metrics: {
      reply_count: 0,
      retweet_count: 0,
      like_count: 0
    }
  };
};

// Endpoint to receive Discord webhook
router.post('/webhook', async (req, res) => {
  try {
    console.log('Received webhook payload:', JSON.stringify(req.body));
    
    // Check for the channel ID (extract from headers or payload)
    const channelId = req.body.channel_id || req.headers['x-discord-channel-id'];
    const TWITTER_FEED_CHANNEL_ID = '1333615004305330348';
    
    // Only process messages from the specific Twitter feed channel
    if (channelId && channelId !== TWITTER_FEED_CHANNEL_ID) {
      console.log(`Ignoring webhook from non-Twitter feed channel: ${channelId}`);
      return res.status(200).send({ 
        success: true,
        processed: false,
        reason: 'Not from Twitter feed channel'
      });
    }
    
    // Validate webhook payload
    const payload = discordWebhookSchema.parse(req.body);
    
    // Format tweet data
    const tweet = formatTweetFromDiscord(payload);
    
    // Parse contract addresses from tweet text (if available)
    const contractAddressRegex = /(0x[a-fA-F0-9]{40})/g;
    const contractAddressMatches = tweet.text.match(contractAddressRegex);
    const contractAddresses = contractAddressMatches || [];
    
    // Store tweet in the database
    await db.insert(twitterScrapeData).values({
      username: tweet.author.username,
      tweetId: tweet.id,
      content: tweet.text,
      contractAddresses: contractAddresses,
      timestamp: new Date(tweet.created_at),
      metadata: {
        authorName: tweet.author.name,
        profileImageUrl: tweet.author.profile_image_url,
        publicMetrics: tweet.public_metrics,
        source: 'discord_webhook',
        channelId: channelId || TWITTER_FEED_CHANNEL_ID
      }
    });
    
    console.log(`Processed and stored tweet from channel ${channelId}: ${tweet.text.substring(0, 30)}...`);
    
    // Analyze and tag the agent if needed based on content
    const shouldTagAgent = await analyzeAndTagAgent(tweet);
    
    // Respond to Discord that we received the webhook
    res.status(200).send({ 
      success: true,
      processed: true,
      taggedAgent: shouldTagAgent,
      tweetId: tweet.id
    });
  } catch (error) {
    console.error('Error processing webhook:', error);
    res.status(400).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Endpoint to get recent tweets from database
router.get('/tweets', async (req, res) => {
  try {
    // Extract query parameters for search and filtering
    const creator = req.query.creator as string | undefined;
    const tweetId = req.query.tweetId as string | undefined;
    const limit = Math.min(parseInt(req.query.limit as string || '10'), 50);
    
    // Build the query
    let query = db.select().from(twitterScrapeData).orderBy(desc(twitterScrapeData.timestamp));
    
    // Apply filters if provided
    if (creator) {
      query = query.where(sql`${twitterScrapeData.username} ILIKE ${`%${creator}%`}`);
    }
    
    if (tweetId) {
      query = query.where(sql`${twitterScrapeData.tweetId} = ${tweetId}`);
    }
    
    // Apply limit
    query = query.limit(limit);
    
    // Execute the query
    const dbTweets = await query;
    
    // Format tweets for frontend
    const tweets = dbTweets.map(tweet => {
      const metadata = tweet.metadata as Record<string, any> || {};
      return {
        id: tweet.tweetId,
        text: tweet.content,
        author: {
          username: tweet.username,
          name: metadata.authorName || tweet.username,
          profile_image_url: metadata.profileImageUrl
        },
        created_at: tweet.timestamp.toISOString(),
        public_metrics: metadata.publicMetrics || {
          reply_count: 0,
          retweet_count: 0,
          like_count: 0
        }
      };
    });
    
    console.log(`Fetched ${tweets.length} tweets from database`);
    
    res.json({
      success: true,
      tweets
    });
  } catch (error) {
    console.error('Error fetching tweets:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Endpoint to test tweet analysis and agent tagging
router.post('/analyze-tweet', async (req, res) => {
  console.log('----- TWEET ANALYSIS ENDPOINT CALLED -----');
  console.log('Request body:', req.body);
  
  try {
    // Validate request body
    const { tweetText, tweetId } = req.body;
    
    console.log('Tweet text received:', tweetText);
    
    if (!tweetText) {
      console.log('❌ Invalid request: Missing tweet text');
      return res.status(400).json({
        success: false,
        error: 'Tweet text is required'
      });
    }
    
    // Create a mock tweet object for analysis
    const mockTweet = {
      id: tweetId || `test-${Date.now()}`,
      text: tweetText,
      author: {
        username: 'test_user',
        name: 'Test User',
        profile_image_url: null
      },
      created_at: new Date().toISOString(),
      public_metrics: {
        reply_count: 0,
        retweet_count: 0,
        like_count: 0
      }
    };
    
    // Analyze the tweet
    console.log(`Testing agent tagging analysis for tweet: "${tweetText.substring(0, 50)}..."`);
    console.log('OpenAI API Key available:', !!process.env.OPENAI_API_KEY);
    
    // Skip actual Discord notification for test requests
    // Store original function
    const originalSendNotification = sendAgentTagNotification;
    
    // Create mock version that just logs instead of sending notifications
    const mockSendNotification = async (
      tweetObj: any, 
      reasonType: 'CRITICAL' | 'MARKET_EVENT' | 'AI_RECOMMENDED', 
      context?: string
    ): Promise<void> => {
      console.log(`[TEST MODE] Would send Discord notification with tag reason: ${reasonType}`);
      console.log(`[TEST MODE] Tweet: "${tweetObj.text.substring(0, 50)}..."`);
      console.log(`[TEST MODE] Discord channel ID: #1333615004305330348`);
      if (context) console.log(`[TEST MODE] Additional context: ${context}`);
      return;
    };
    
    // Replace the global function temporarily
    (global as any).sendAgentTagNotificationTemp = sendAgentTagNotification; 
    (global as any).sendAgentTagNotification = mockSendNotification;
    
    // Analyze the tweet
    const shouldTag = await analyzeAndTagAgent(mockTweet);
    
    // Restore original function after test
    (global as any).sendAgentTagNotification = (global as any).sendAgentTagNotificationTemp;
    
    // Log analysis result for better debugging
    console.log(`Tweet analysis complete. Result: ${shouldTag ? 'SHOULD TAG AGENT ✓' : 'Should not tag agent ✗'}`);
    console.log(`Discord channel ID for notification: #1333615004305330348`);
    
    // Return detailed result with analysis
    const detectedKeywords = getDetectedKeywords(tweetText.toLowerCase());
    
    // Return the result
    return res.json({
      success: true,
      shouldTag,
      tweet: mockTweet,
      analysis: {
        detectedKeywords,
        discordChannel: '1333615004305330348',
        usingAI: !!process.env.OPENAI_API_KEY
      }
    });
  } catch (error) {
    console.error('Error analyzing tweet:', error);
    return res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Helper function to extract detected keywords for better UI feedback
function getDetectedKeywords(tweetText: string): {
  critical: string[],
  marketEvents: string[], 
  monitoredAssets: string[]
} {
  // Critical keywords that trigger immediate tagging
  const criticalKeywords = [
    'urgent', 'emergency', 'hack', 'exploit', 'vulnerability', 'scam', 
    'warning', 'alert', 'critical', 'security', 'breach', 'stolen',
    'rug pull', 'attack', 'SEC', 'regulation'
  ];
  
  // Market event keywords
  const marketEventKeywords = [
    'partnership', 'listing', 'acquisition', 'launched', 'release', 
    'announces', 'update', 'upgraded', 'integration', 'collaboration',
    'breaking', 'exclusive'
  ];
  
  // Monitored assets
  const monitoredAssets = [
    'sonic', 'ethereum', 'bitcoin', 'btc', 'eth', '$eth', '$btc', '$sonic',
    'sol', '$sol', 'solana', 'arbitrum', 'optimism', 'base'
  ];
  
  // Get matches
  return {
    critical: criticalKeywords.filter(keyword => tweetText.includes(keyword.toLowerCase())),
    marketEvents: marketEventKeywords.filter(keyword => tweetText.includes(keyword.toLowerCase())),
    monitoredAssets: monitoredAssets.filter(asset => tweetText.includes(asset.toLowerCase()))
  };
}

// Function to seed the database with sample tweets if necessary
async function seedDatabaseWithSampleTweets() {
  try {
    // Check if we already have tweets in the database
    const existingTweetCount = await db
      .select({ count: sql`count(*)` })
      .from(twitterScrapeData)
      .then(result => parseInt(result[0].count.toString(), 10));
    
    // If we already have tweets, don't seed
    if (existingTweetCount > 0) {
      console.log(`Database already has ${existingTweetCount} tweets, skipping seeding`);
      return;
    }
    
    // Sample tweets for testing when no real data exists
    const sampleTweets = [
      {
        tweetId: 'sample-tweet-1',
        content: 'Just deployed a new update to $SONIC network! 🚀 Check out the improved cross-chain swaps and lower fees. #SONIC #Crypto',
        username: 'SonicDev',
        timestamp: new Date(),
        contractAddresses: [],
        metadata: {
          authorName: 'Sonic Developer',
          profileImageUrl: 'https://pbs.twimg.com/profile_images/1234567890/profile.jpg',
          publicMetrics: {
            reply_count: 12,
            retweet_count: 34,
            like_count: 89
          },
          source: 'seeded_data'
        }
      },
      {
        tweetId: 'tweet-1742671181800-vv1fqm7',
        content: 'SONIC price up 15% in the last 24 hours! Volume has increased significantly with new exchange listings.',
        username: 'whale_watcher',
        timestamp: new Date('2025-03-22T18:55:52Z'),
        contractAddresses: [],
        metadata: {
          authorName: 'CryptoWhale',
          profileImageUrl: 'https://pbs.twimg.com/profile_images/1234567890/crypto_whale.jpg',
          publicMetrics: {
            reply_count: 5,
            retweet_count: 12,
            like_count: 45
          },
          source: 'seeded_data'
        }
      },
      {
        tweetId: 'tweet-1742671191332-xur6ko6',
        content: 'Sonic network showing impressive growth metrics. Transaction volume is up 25% month-over-month with gas fees down 10%.',
        username: 'crypto_tech',
        timestamp: new Date('2025-03-22T19:10:00Z'),
        contractAddresses: [],
        metadata: {
          authorName: 'TechAnalyst',
          profileImageUrl: 'https://pbs.twimg.com/profile_images/2345678901/tech_analyst.jpg',
          publicMetrics: {
            reply_count: 3,
            retweet_count: 8,
            like_count: 22
          },
          source: 'seeded_data'
        }
      },
      {
        tweetId: 'tweet-1742671202101-gu6djn6',
        content: 'SonicLidz NFT collection seeing massive adoption. Floor price up 30% in 48 hours with 500+ sales. Looks like this project has real staying power!',
        username: 'nft_insights',
        timestamp: new Date('2025-03-22T19:20:00Z'),
        contractAddresses: [],
        metadata: {
          authorName: 'NFTExpert',
          profileImageUrl: 'https://pbs.twimg.com/profile_images/3456789012/nft_expert.jpg',
          publicMetrics: {
            reply_count: 7,
            retweet_count: 15,
            like_count: 38
          },
          source: 'seeded_data'
        }
      },
      {
        tweetId: 'tweet-1742671202102-yu9fqt2',
        content: 'Yohaan (@YJN58) ✧ Who is building a dex that mimics the liquidity customisation of @LFJ_gg but with dynamic fees that increases or decreases the tick / bin width based on volatility to reduce IL? Sonic has a very high gas limit so you can do up to 100 bins / ticks of liquidity on each side',
        username: 'YJN58',
        timestamp: new Date('2025-03-22T20:05:00Z'),
        contractAddresses: [],
        metadata: {
          authorName: 'Yohaan',
          profileImageUrl: null,
          publicMetrics: {
            reply_count: 2,
            retweet_count: 5,
            like_count: 18
          },
          source: 'discord_webhook'
        }
      }
    ];
    
    // Insert all sample tweets into the database
    for (const tweet of sampleTweets) {
      await db.insert(twitterScrapeData).values(tweet);
    }
    
    console.log(`Seeded database with ${sampleTweets.length} sample tweets`);
  } catch (error) {
    console.error('Error seeding database with sample tweets:', error);
  }
}

/**
 * Analyzes tweet content to determine if the agent should be tagged on Discord
 * Uses Anthropic API to provide AI-based assessment
 * @param tweet The tweet object to analyze
 * @returns Boolean indicating whether the agent should be tagged
 */
async function analyzeAndTagAgent(tweet: any): Promise<boolean> {
  try {
    // Check for critical keywords that always trigger agent tagging
    const criticalKeywords = [
      'urgent', 'emergency', 'hack', 'exploit', 'vulnerability', 'scam', 
      'warning', 'alert', 'critical', 'security', 'breach', 'stolen',
      'rug pull', 'attack', 'SEC', 'regulation'
    ];
    
    // Check for important market events
    const marketEventKeywords = [
      'partnership', 'listing', 'acquisition', 'launched', 'release', 
      'announces', 'update', 'upgraded', 'integration', 'collaboration',
      'breaking', 'exclusive'
    ];
    
    // Check for specific tokens/networks we are monitoring
    const monitoredAssets = [
      'sonic', 'ethereum', 'bitcoin', 'btc', 'eth', '$eth', '$btc', '$sonic',
      'sol', '$sol', 'solana', 'arbitrum', 'optimism', 'base'
    ];
    
    // Convert tweet text to lowercase for case-insensitive matching
    const lowerText = tweet.text.toLowerCase();
    
    // Check for critical keywords (immediate tagging)
    for (const keyword of criticalKeywords) {
      if (lowerText.includes(keyword.toLowerCase())) {
        console.log(`🚨 Critical keyword '${keyword}' detected in tweet. Tagging agent...`);
        
        // Send notification to Discord with @mention
        await sendAgentTagNotification(tweet, 'CRITICAL');
        
        return true;
      }
    }
    
    // Check for combination of market events and monitored assets
    let hasMarketEvent = false;
    let hasMonitoredAsset = false;
    
    for (const keyword of marketEventKeywords) {
      if (lowerText.includes(keyword.toLowerCase())) {
        hasMarketEvent = true;
        break;
      }
    }
    
    for (const asset of monitoredAssets) {
      if (lowerText.includes(asset.toLowerCase())) {
        hasMonitoredAsset = true;
        break;
      }
    }
    
    // If both conditions are met, tag the agent
    if (hasMarketEvent && hasMonitoredAsset) {
      console.log(`📊 Market event detected for monitored asset in tweet. Tagging agent...`);
      
      // Send notification to Discord with @mention
      await sendAgentTagNotification(tweet, 'MARKET_EVENT');
      
      return true;
    }
    
    // For more complex content, use AI to determine if it's important
    const anthropicService = new AnthropicService();
    const aiAnalysis = await anthropicService.analyzeTweetImportance(tweet.text);
    
    if (aiAnalysis.shouldTag) {
      console.log(`🤖 AI determined tweet is important (${aiAnalysis.reason}). Tagging agent...`);
      
      // Send notification to Discord with @mention
      await sendAgentTagNotification(tweet, 'AI_RECOMMENDED', aiAnalysis.reason);
      
      return true;
    }
    
    // No conditions met for tagging
    console.log('Tweet analyzed but does not meet criteria for agent tagging');
    return false;
  } catch (error) {
    console.error('Error analyzing tweet for agent tagging:', error);
    return false;
  }
}

/**
 * Sends a notification to Discord with agent tagging
 * @param tweet The tweet that triggered the notification
 * @param tagReason The reason for tagging
 * @param additionalContext Optional additional context
 */
async function sendAgentTagNotification(tweet: any, tagReason: 'CRITICAL' | 'MARKET_EVENT' | 'AI_RECOMMENDED', additionalContext?: string): Promise<void> {
  try {
    // Discord webhook URL for the agent notification channel
    // This would be different from the webhook that's sending the tweets in
    const webhookUrl = process.env.DISCORD_AGENT_WEBHOOK_URL;
    
    if (!webhookUrl) {
      console.warn('No Discord agent webhook URL configured. Skipping notification.');
      return;
    }
    
    // Format the message with appropriate tagging
    // Using the specific Discord chat ID provided by the user
    let message = `**<#1333615004305330348>** New important tweet detected!\n\n`;
    
    switch (tagReason) {
      case 'CRITICAL':
        message += `⚠️ **CRITICAL ALERT** ⚠️\n\n`;
        break;
      case 'MARKET_EVENT':
        message += `📈 **MARKET EVENT** 📈\n\n`;
        break;
      case 'AI_RECOMMENDED':
        message += `🤖 **AI FLAGGED CONTENT** 🤖\n\n`;
        break;
    }
    
    // Add tweet details
    message += `**Author:** ${tweet.author.name} (@${tweet.author.username})\n`;
    message += `**Content:** ${tweet.text}\n`;
    message += `**Tweet ID:** ${tweet.id}\n`;
    
    // Add additional context if provided
    if (additionalContext) {
      message += `\n**Context:** ${additionalContext}\n`;
    }
    
    message += `\n*Use the dashboard search to find this tweet using creator:${tweet.author.username} or tweetId:${tweet.id}*`;
    
    // Send the webhook
    await axios.post(webhookUrl, {
      content: message,
      username: 'Tweet Alert Bot',
      avatar_url: 'https://cdn-icons-png.flaticon.com/512/733/733579.png' // Twitter logo
    });
    
    console.log(`Successfully sent agent notification for tweet ID ${tweet.id}`);
  } catch (error) {
    console.error('Error sending agent notification to Discord:', error);
  }
}

// Call the seeding function on module load
seedDatabaseWithSampleTweets();

// Add the AnthropicService method to analyze tweet importance
// This extends the existing AnthropicService to include tweet importance analysis
AnthropicService.prototype.analyzeTweetImportance = async function(tweetText: string): Promise<{shouldTag: boolean, reason?: string}> {
  try {
    // Default response if API call fails
    const defaultResponse = { shouldTag: false };
    
    // Skip if no API key available
    if (!process.env.OPENAI_API_KEY) {
      console.warn('No Anthropic API key configured. Skipping AI tweet analysis.');
      return defaultResponse;
    }
    
    // Prepare the prompt for Claude
    const prompt = `
    You are analyzing a tweet from the crypto/web3 space to determine if it's important enough to tag a team member.
    
    Tweet: "${tweetText}"
    
    Please analyze if this tweet contains:
    1. Breaking news that could impact crypto markets
    2. Significant project announcements, partnerships, or launches
    3. Security threats, exploits, or warnings
    4. Regulatory developments
    5. Major market movements
    
    Return a JSON object with:
    - shouldTag: boolean (true if important enough to notify, false otherwise)
    - reason: string (brief explanation if shouldTag is true, omit if false)
    
    Format: {shouldTag: boolean, reason?: string}
    `;
    
    // Call the Claude API through OpenRouter
    const response = await this.getChatCompletion(prompt);
    
    // Parse the JSON response
    try {
      // Look for a JSON object in the response
      const jsonMatch = response.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        const jsonResponse = JSON.parse(jsonMatch[0]);
        return {
          shouldTag: Boolean(jsonResponse.shouldTag),
          reason: jsonResponse.reason
        };
      }
    } catch (parseError) {
      console.error('Error parsing AI response as JSON:', parseError);
      console.log('Raw AI response:', response);
    }
    
    // Fallback to conservative response
    return defaultResponse;
  } catch (error) {
    console.error('Error analyzing tweet importance with Anthropic:', error);
    return { shouldTag: false };
  }
};

export default router;