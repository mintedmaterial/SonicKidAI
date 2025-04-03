import { db } from '../db';
import { dashboardPosts, InsertDashboardPost } from '@shared/schema';
import { desc } from 'drizzle-orm';
import { randomUUID } from 'crypto';
import { AnthropicService } from './anthropic_service';

// Define market data types
interface TokenData {
  price?: number;
  volume24h?: number;
  tvl?: number;
  priceChange24h?: number;
}

interface MarketData {
  tokens: Record<string, TokenData>;
  market: {
    sentiment: string;
    confidence: number;
    trending_topics?: Array<{ topic: string }>;
    dex_volume?: {
      volume24h: number;
      volumeChange24h: number;
    };
  };
}

interface PostHistoryItem {
  category: string;
  title: string;
  timestamp: string;
}

/**
 * Agent Activity Service - Generates and posts regular updates to the dashboard
 */
export class AgentActivityService {
  private anthropic: AnthropicService | null = null;
  private postHistory: PostHistoryItem[] = [];
  private running = false;
  private postInterval: number; 
  private timer: NodeJS.Timeout | null = null;
  
  // Post category weights
  private postCategories: Record<string, number> = {
    "market_analysis": 30,  // Market trends and analysis
    "token_spotlight": 20,  // Focus on specific tokens/coins
    "trading_signals": 15,  // Trading signals and opportunities
    "sentiment_analysis": 15,  // Market sentiment analysis
    "nft_trends": 10,        // NFT market updates
    "defi_updates": 10,      // DeFi protocol updates
  };

  constructor(config?: { 
    openaiApiKey?: string; 
    anthropicApiKey?: string;
    postIntervalMinutes?: number;
  }) {
    // Set defaults
    this.postInterval = (config?.postIntervalMinutes || 180) * 60 * 1000; // Convert minutes to ms
    
    // Initialize Anthropic service if API key is provided
    // Note: For OpenRouter, we should use the OPENROUTER_API_KEY in the environment
    // or pass it directly as anthropicApiKey
    const apiKey = config?.anthropicApiKey || process.env.OPENROUTER_API_KEY || config?.openaiApiKey;
    if (apiKey) {
      this.anthropic = new AnthropicService(apiKey);
    }
    
    console.log(`Agent Activity Service initialized with post interval: ${this.postInterval / (60 * 1000)} minutes`);
  }

  /**
   * Start the service
   */
  public start(): boolean {
    if (this.running) {
      console.warn('Agent Activity Service is already running');
      return false;
    }
    
    this.running = true;
    
    // Create initial post
    this.createAndPostActivity();
    
    // Schedule regular posts
    this.timer = setInterval(() => {
      if (this.running) {
        this.createAndPostActivity();
      }
    }, this.postInterval);
    
    console.log('Agent Activity Service started');
    return true;
  }
  
  /**
   * Stop the service
   */
  public stop(): boolean {
    if (!this.running) {
      console.warn('Agent Activity Service is not running');
      return false;
    }
    
    this.running = false;
    
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
    
    console.log('Agent Activity Service stopped');
    return true;
  }
  
  /**
   * Create and post a new activity
   */
  public async createAndPostActivity(): Promise<boolean> {
    try {
      console.log('Creating new agent activity post...');
      
      // 1. Select post category
      const category = this.selectPostCategory();
      console.log(`Selected category: ${category}`);
      
      // 2. Collect market data for context
      const marketData = await this.collectMarketData();
      
      // 3. Generate content using selected category and market data
      const postData = await this.generatePostContent(category, marketData);
      if (!postData) {
        console.error('Failed to generate post content');
        return false;
      }
      
      // 4. Store post to database
      const success = await this.storeDashboardPost({
        type: category,
        content: postData.content,
        title: postData.title,
        metadata: postData.metadata
      });
      
      if (success) {
        // 5. Update post history to avoid repetition
        this.updatePostHistory({
          category: category,
          title: postData.title,
          timestamp: new Date().toISOString()
        });
        
        console.log('Successfully created and posted agent activity');
        return true;
      } else {
        console.error('Failed to store dashboard post');
        return false;
      }
    } catch (error) {
      console.error('Error creating agent activity:', error);
      return false;
    }
  }
  
  /**
   * Select a post category with weighted preferences based on importance
   */
  private selectPostCategory(): string {
    // Filter out recently used categories if possible
    const recentCategories = new Set(
      this.postHistory.length >= 3 
        ? this.postHistory.slice(-3).map(item => item.category) 
        : []
    );
    
    const availableCategories = Object.entries(this.postCategories)
      .filter(([category]) => !recentCategories.has(category))
      .reduce((acc, [category, weight]) => {
        acc[category] = weight;
        return acc;
      }, {} as Record<string, number>);
    
    // If all categories were recently used, use all categories
    const categoriesToUse = Object.keys(availableCategories).length > 0 
      ? availableCategories 
      : this.postCategories;
    
    // Calculate total weight
    const totalWeight = Object.values(categoriesToUse).reduce((sum, weight) => sum + weight, 0);
    
    // Make weighted random selection
    const r = Math.random() * totalWeight;
    let runningSum = 0;
    
    for (const [category, weight] of Object.entries(categoriesToUse)) {
      runningSum += weight;
      if (r <= runningSum) {
        return category;
      }
    }
    
    // Fallback to first category (should never reach here)
    return Object.keys(categoriesToUse)[0];
  }
  
  /**
   * Collect market data for post context
   */
  private async collectMarketData(): Promise<MarketData> {
    try {
      const marketData: MarketData = {
        tokens: {},
        market: {
          sentiment: 'neutral',
          confidence: 50,
          trending_topics: []
        }
      };
      
      const BASE_URL = 'http://localhost:3000';
      
      // Get SONIC token data
      try {
        const sonicData = await fetch(`${BASE_URL}/api/market/sonic`).then(res => res.ok ? res.json() : null);
        if (sonicData) {
          marketData.tokens['SONIC'] = sonicData;
        }
      } catch (error) {
        console.error('Error fetching SONIC data:', error);
      }
      
      // Get sentiment data
      try {
        const sentimentData = await fetch(`${BASE_URL}/api/market/sentiment`).then(res => res.ok ? res.json() : null);
        if (sentimentData) {
          marketData.market.sentiment = sentimentData.sentiment || 'neutral';
          marketData.market.confidence = sentimentData.confidence || 50;
          marketData.market.trending_topics = sentimentData.trending || [];
        }
      } catch (error) {
        console.error('Error fetching sentiment data:', error);
      }
      
      // Get DEX volume data
      try {
        const volumeData = await fetch(`${BASE_URL}/api/market/dex-volume`).then(res => res.ok ? res.json() : null);
        if (volumeData && volumeData.data) {
          marketData.market.dex_volume = volumeData.data;
        }
      } catch (error) {
        console.error('Error fetching DEX volume data:', error);
      }
      
      return marketData;
    } catch (error) {
      console.error('Error collecting market data:', error);
      return {
        tokens: {},
        market: {
          sentiment: 'neutral',
          confidence: 50
        }
      };
    }
  }
  
  /**
   * Generate content for a post based on category and market data
   */
  private async generatePostContent(category: string, marketData: MarketData): Promise<{
    title: string;
    content: string;
    category: string;
    metadata: Record<string, any>;
  } | null> {
    try {
      // Prepare market context string
      const marketContext = this.prepareMarketContext(marketData);
      
      // Get prompt for specific category
      const prompt = this.getCategoryPrompt(category, marketData);
      
      // Generate content with Anthropic (via OpenRouter) if available
      if (this.anthropic) {
        try {
          // Use the Anthropic service to generate content
          const userMessage = `Market Context: ${marketContext}\n\nTask: ${prompt}`;
          
          // Use the standard (non-instructor) mode for dashboard content
          const generatedText = await this.anthropic.generateChatCompletion(
            userMessage,
            false // not using instructor mode
          );
          
          if (generatedText) {
            // Extract title and clean content
            const title = this.extractTitle(generatedText, category);
            const content = this.cleanContent(generatedText);
            
            return {
              category,
              title,
              content,
              metadata: {
                source: 'anthropic',
                model: 'claude-3-sonnet',
                category,
                sentiment: marketData.market.sentiment,
                confidence: marketData.market.confidence
              }
            };
          }
        } catch (error) {
          console.error('Error generating content with Anthropic:', error);
        }
      }
      
      // Fallback to hardcoded templates
      console.warn('Using fallback hardcoded post template');
      return this.getFallbackPost(category, marketData);
    } catch (error) {
      console.error('Error generating post content:', error);
      return null;
    }
  }
  
  /**
   * Prepare market context string for prompt
   */
  private prepareMarketContext(marketData: MarketData): string {
    const contextParts = [];
    
    // Add SONIC token data if available
    const sonic = marketData.tokens['SONIC'];
    if (sonic) {
      contextParts.push(
        `SONIC Token: Price $${sonic.price?.toFixed(2) || '0.00'}, ` +
        `24h Volume: $${sonic.volume24h?.toLocaleString() || '0'}, ` +
        `TVL: $${sonic.tvl?.toLocaleString() || '0'}, ` +
        `Price Change 24h: ${sonic.priceChange24h?.toFixed(2) || '0.00'}%`
      );
    }
    
    // Add market sentiment
    contextParts.push(
      `Market Sentiment: ${marketData.market.sentiment.charAt(0).toUpperCase() + marketData.market.sentiment.slice(1)} ` +
      `(Confidence: ${marketData.market.confidence}%)`
    );
    
    // Add DEX volume if available
    if (marketData.market.dex_volume) {
      const volume = marketData.market.dex_volume.volume24h;
      const change = marketData.market.dex_volume.volumeChange24h;
      contextParts.push(`DEX 24h Volume: $${volume.toLocaleString()} (${change.toFixed(2)}% change)`);
    }
    
    // Add trending topics if available
    if (marketData.market.trending_topics && marketData.market.trending_topics.length > 0) {
      const topics = marketData.market.trending_topics.slice(0, 3)
        .map(t => t.topic)
        .join(', ');
      
      contextParts.push(`Trending Topics: ${topics}`);
    }
    
    return contextParts.join('\n');
  }
  
  /**
   * Get prompt template for specific category
   */
  private getCategoryPrompt(category: string, marketData: MarketData): string {
    const prompts: Record<string, string> = {
      "market_analysis": 
        "Generate a concise market analysis for the Sonic ecosystem. " +
        "Include insights on price movements, trading volume, and overall market conditions. " +
        "Keep it under 100 words.",
      
      "token_spotlight": 
        "Create a brief spotlight on SONIC token's recent performance. " +
        "Highlight key metrics and noteworthy changes. " +
        "Keep it under 100 words.",
      
      "trading_signals": 
        "Identify a potential trading opportunity or signal based on current market conditions. " +
        "Be specific but avoid overly prescriptive language. " +
        "Include factors that support this signal. " +
        "Keep it under 100 words.",
      
      "sentiment_analysis": 
        "Analyze the current market sentiment for the Sonic ecosystem. " +
        "How are investors feeling? What's driving the sentiment? " +
        "Keep it under 100 words.",
      
      "nft_trends": 
        "Generate insights about the latest NFT trends in the crypto space. " +
        "Include popular collections, trade volumes, or unique developments. " +
        "Keep it under 100 words.",
      
      "defi_updates": 
        "Provide updates on DeFi protocols in the Sonic ecosystem. " +
        "Include TVL changes, yield opportunities, or protocol developments. " +
        "Keep it under 100 words."
    };
    
    return prompts[category] || prompts["market_analysis"];
  }
  
  /**
   * Convert category to default title
   */
  private categoryToTitle(category: string): string {
    const titles: Record<string, string> = {
      "market_analysis": "Market Analysis Update",
      "token_spotlight": "SONIC Token Spotlight",
      "trading_signals": "Trading Signal Alert",
      "sentiment_analysis": "Market Sentiment Report",
      "nft_trends": "NFT Market Trends",
      "defi_updates": "DeFi Ecosystem Update"
    };
    
    return titles[category] || "Agent Update";
  }
  
  /**
   * Extract title from generated text or create default
   */
  private extractTitle(text: string, category: string): string {
    // Check if text starts with a title on the first line
    const lines = text.trim().split('\n');
    if (lines.length > 1 && lines[0].length < 80 && !lines[0].endsWith('.')) {
      return lines[0].trim();
    }
    
    // Return default title based on category
    return this.categoryToTitle(category);
  }
  
  /**
   * Clean up generated content
   */
  private cleanContent(text: string): string {
    // Remove title line if it exists
    const lines = text.trim().split('\n');
    let content = text.trim();
    
    if (lines.length > 1 && lines[0].length < 80 && !lines[0].endsWith('.')) {
      content = lines.slice(1).join('\n').trim();
    }
    
    // Remove quotes if present
    if (content.startsWith('"') && content.endsWith('"')) {
      content = content.slice(1, -1).trim();
    }
    
    return content;
  }
  
  /**
   * Update post history for avoiding repetition
   */
  private updatePostHistory(post: PostHistoryItem): void {
    this.postHistory.push(post);
    
    // Keep only the last 10 posts in history
    if (this.postHistory.length > 10) {
      this.postHistory = this.postHistory.slice(-10);
    }
  }
  
  /**
   * Store post to database
   */
  private async storeDashboardPost(post: InsertDashboardPost): Promise<boolean> {
    try {
      await db.insert(dashboardPosts).values(post);
      console.log('Successfully stored dashboard post');
      return true;
    } catch (error) {
      console.error('Error storing dashboard post:', error);
      return false;
    }
  }
  
  /**
   * Get fallback post data when API generation fails
   */
  private getFallbackPost(category: string, marketData: MarketData): {
    title: string;
    content: string;
    category: string;
    metadata: Record<string, any>;
  } {
    // Get default title for category
    const title = this.categoryToTitle(category);
    
    // Get sentiment from market data
    const sentiment = marketData.market.sentiment;
    const confidence = marketData.market.confidence;
    
    // Get price and volume if available
    const price = marketData.tokens['SONIC']?.price || 0.45;
    const volume = marketData.tokens['SONIC']?.volume24h || 750000;
    const priceChange = marketData.tokens['SONIC']?.priceChange24h || 0;
    
    // Create fallback content based on category
    const contentTemplates: Record<string, string> = {
      "market_analysis": 
        `SONIC currently trading at $${price.toFixed(2)} with ${priceChange > 0 ? 'positive' : priceChange < 0 ? 'negative' : 'neutral'} momentum. ` +
        `Trading volume at $${volume.toLocaleString()} over the past 24 hours. ` +
        `Market sentiment remains ${sentiment} with continued interest from traders.`,
      
      "token_spotlight": 
        `SONIC Token showing ${priceChange > 0 ? 'strength' : priceChange < 0 ? 'weakness' : 'stability'} at $${price.toFixed(2)}. ` +
        `24-hour volume holding at $${volume.toLocaleString()} with ${Math.abs(priceChange).toFixed(2)}% ` +
        `${priceChange > 0 ? 'gain' : priceChange < 0 ? 'loss' : 'change'} since yesterday.`,
      
      "trading_signals": 
        `${sentiment === 'bullish' ? 'Potential buying opportunity' : sentiment === 'bearish' ? 'Potential selling pressure' : 'Market consolidation'} ` +
        `for SONIC at $${price.toFixed(2)}. ` +
        `${priceChange < 0 ? 'Watch support levels carefully' : `Resistance at $${(price + price * 0.05).toFixed(2)}`} ` +
        `with volume indicators ${volume > 800000 ? 'strengthening' : 'weakening'}.`,
      
      "sentiment_analysis": 
        `Market sentiment analysis: ${sentiment.charAt(0).toUpperCase() + sentiment.slice(1)} with ${confidence}% confidence. ` +
        `${sentiment === 'bullish' ? 'Increasing bullish momentum' : sentiment === 'bearish' ? 'Bearish pressure mounting' : 'Mixed signals with neutral bias'}. ` +
        `Social mentions ${confidence > 60 ? 'up' : 'down'} compared to previous week.`,
      
      "nft_trends": 
        `NFT market showing signs of renewed interest with collectible sales increasing 15% week-over-week. ` +
        `Profile picture projects remain popular while utility-focused NFTs gain momentum in the Sonic ecosystem.`,
      
      "defi_updates": 
        `DeFi protocols in the Sonic ecosystem maintain stable TVL despite market fluctuations. ` +
        `Yield farming opportunities averaging 8-12% APY with liquidity mining programs attracting new users. ` +
        `Trading volume at $${volume.toLocaleString()} over the past 24 hours.`
    };
    
    const content = contentTemplates[category] || contentTemplates["market_analysis"];
    
    return {
      category,
      title,
      content,
      metadata: {
        source: 'fallback',
        category,
        sentiment,
        confidence,
        id: randomUUID()
      }
    };
  }
  
  /**
   * Force creation of a new post immediately
   */
  public async forcePost(category?: string): Promise<boolean> {
    const selectedCategory = category || this.selectPostCategory();
    const marketData = await this.collectMarketData();
    return this.createAndPostActivity();
  }
  
  /**
   * Get recent posts from database
   */
  public async getRecentPosts(limit: number = 10): Promise<any[]> {
    try {
      const posts = await db
        .select()
        .from(dashboardPosts)
        .orderBy(desc(dashboardPosts.createdAt))
        .limit(limit);
      
      return posts;
    } catch (error) {
      console.error('Error getting recent posts:', error);
      return [];
    }
  }
}

// Singleton instance
let serviceInstance: AgentActivityService | null = null;

export function getAgentActivityService(config?: { 
  openaiApiKey?: string; 
  anthropicApiKey?: string;
  postIntervalMinutes?: number;
}): AgentActivityService {
  if (!serviceInstance) {
    serviceInstance = new AgentActivityService(config);
  }
  
  return serviceInstance;
}