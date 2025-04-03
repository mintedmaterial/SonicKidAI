import axios from ;
import { db } from '../server/db';
import { insertTwitterScrapeDataSchema, insertAddressCacheSchema } from '../shared/schema';
import { eq } from 'drizzle-orm';
import { twitterScrapeData, addressCache } from '../shared/schema';
import { logger } from '../utils/logger';

interface Tweet {
  username: string;
  tweet_id: string;
  content: string;
  timestamp: string;
  metadata?: any;
}

export class ApifyConnection {
  private readonly apiToken: string;
  private readonly endpoint: string;
  private static instance: ApifyConnection;

  private constructor() {
    this.apiToken = process.env.APIFY_API_TOKEN || '';
    this.endpoint = 'https://api.apify.com/v2/acts/apidojo~tweet-scraper/run-sync-get-dataset-items';
  }

  public static getInstance(): ApifyConnection {
    if (!ApifyConnection.instance) {
      ApifyConnection.instance = new ApifyConnection();
    }
    return ApifyConnection.instance;
  }

  private extractContractAddresses(content: string): string[] {
    // Match Ethereum addresses (0x followed by 40 hex characters)
    const addressRegex = /0x[a-fA-F0-9]{40}/g;
    return Array.from(new Set(content.match(addressRegex) || []));
  }

  private async updateAddressCache(address: string, tweetId: string): Promise<void> {
    try {
      const existingAddress = await db.query.addressCache.findFirst({
        where: eq(addressCache.address, address)
      });

      if (existingAddress) {
        await db
          .update(addressCache)
          .set({ lastSeen: new Date() })
          .where(eq(addressCache.address, address));
      } else {
        await db.insert(addressCache).values({
          address,
          source: 'twitter',
          sourceId: tweetId,
          metadata: { initialTweetId: tweetId }
        });
      }
    } catch (error) {
      logger.error(`Error updating address cache: ${error}`);
    }
  }

  public async fetchAndStoreTweets(): Promise<void> {
    try {
      const response = await axios.get(`${this.endpoint}?token=${this.apiToken}`);
      const tweets: Tweet[] = response.data;

      for (const tweet of tweets) {
        try {
          const contractAddresses = this.extractContractAddresses(tweet.content);
          
          // Store tweet data
          await db.insert(twitterScrapeData).values({
            username: tweet.username,
            tweetId: tweet.tweet_id,
            content: tweet.content,
            contractAddresses,
            timestamp: new Date(tweet.timestamp),
            metadata: tweet.metadata
          });

          // Update address cache for each contract address found
          for (const address of contractAddresses) {
            await this.updateAddressCache(address, tweet.tweet_id);
          }
        } catch (error) {
          logger.error(`Error processing tweet ${tweet.tweet_id}: ${error}`);
        }
      }
    } catch (error) {
      logger.error(`Error fetching tweets from Apify: ${error}`);
      throw error;
    }
  }
}

// Setup scheduled task (to be called from main application)
export const setupTwitterScraping = (): void => {
  const TWO_HOURS = 2 * 60 * 60 * 1000;
  const apifyConnection = ApifyConnection.getInstance();

  setInterval(async () => {
    try {
      await apifyConnection.fetchAndStoreTweets();
      logger.info('Successfully completed Twitter scraping cycle');
    } catch (error) {
      logger.error(`Error in Twitter scraping cycle: ${error}`);
    }
  }, TWO_HOURS);

  // Run initial scraping
  apifyConnection.fetchAndStoreTweets()
    .catch(error => logger.error(`Error in initial Twitter scraping: ${error}`));
};
