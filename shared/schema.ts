import { pgTable, text, serial, numeric, timestamp, jsonb } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

// Keep existing tables
export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
});

// Add telegram channels table
export const telegramChannels = pgTable("telegram_channels", {
  id: serial("id").primaryKey(),
  channelId: text("channel_id").notNull(),
  channelName: text("channel_name"),
  isActive: boolean("is_active").notNull().default(true),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  lastMessageAt: timestamp("last_message_at"),
  metadata: jsonb("metadata"),
});

// Add schema for telegram channels
export const insertTelegramChannelSchema = createInsertSchema(telegramChannels).omit({
  id: true,
  createdAt: true,
  lastMessageAt: true,
});

// Export types
export type InsertTelegramChannel = z.infer<typeof insertTelegramChannelSchema>;
export type TelegramChannel = typeof telegramChannels.$inferSelect;

// Update whale tracker tables to reflect buy/sell semantics
export const whaleKlineData = pgTable("whale_kline_data", {
  id: serial("id").primaryKey(),
  walletAddress: text("wallet_address").notNull(),
  timestamp: timestamp("timestamp").notNull(),
  openPrice: numeric("open_price").notNull(),  // Used for buy price
  closePrice: numeric("close_price").notNull(), // Used for sell price
  highPrice: numeric("high_price").notNull(),
  lowPrice: numeric("low_price").notNull(),
  volume: numeric("volume").notNull(),
  quoteVolume: numeric("quote_volume"),
  buyAmount: numeric("buy_amount"),
  isLoading: boolean("is_loading").notNull().default(false)
});

export const whaleAlerts = pgTable("whale_alerts", {
  id: serial("id").primaryKey(),
  walletAddress: text("wallet_address").notNull(),
  timestamp: timestamp("timestamp").notNull(),
  movementType: text("movement_type").notNull(), // 'loading' or 'shaving'
  priceChange: numeric("price_change").notNull(),
  volumeChange: numeric("volume_change"),
  volatility: numeric("volatility"),
  details: jsonb("details"),
});

// Update sonicPriceFeed table with consistent naming
export const sonicPriceFeed = pgTable("sonic_price_feed", {
  id: serial("id").primaryKey(),
  pairAddress: text("pair_address").notNull(),
  pairSymbol: text("pair_symbol").notNull(),
  baseToken: text("base_token").notNull(),
  quoteToken: text("quote_token").notNull(),
  price: numeric("price").notNull(),
  priceUsd: numeric("price_usd").notNull(),
  priceChange24h: numeric("price_change_24h"),
  volume24h: numeric("volume_24h"),
  liquidity: numeric("liquidity"),
  chain: text("chain").notNull(),
  timestamp: timestamp("timestamp").notNull().defaultNow(),
  metadata: jsonb("metadata"), // For additional pair data
});

// Add price feed tables
export const priceFeedData = pgTable("price_feed_data", {
  id: serial("id").primaryKey(),
  symbol: text("symbol").notNull(),
  price: numeric("price").notNull(),
  source: text("source").notNull(), // e.g., 'dexscreener', 'cryptopanic', etc.
  chainId: text("chain_id"), // Optional chain ID for DEX prices
  volume24h: numeric("volume_24h"),
  priceChange24h: numeric("price_change_24h"),
  timestamp: timestamp("timestamp").notNull().defaultNow(),
  metadata: jsonb("metadata"), // Additional price-related data
});

// Update trading activity table to support both activity and signals
export const tradingActivity = pgTable("trading_activity", {
  id: serial("id").primaryKey(),
  // Common fields
  timestamp: timestamp("timestamp").notNull().defaultNow(),
  status: text("status").notNull(),
  metadata: jsonb("metadata"), // Additional trade-specific data

  // Trading activity specific fields
  actionType: text("action_type"),
  fromToken: text("from_token"),
  toToken: text("to_token"),
  fromAmount: numeric("from_amount"),
  toAmount: numeric("to_amount"),
  chainId: text("chain_id"),
  platform: text("platform"),
  txHash: text("tx_hash"),

  // Trading signal specific fields
  asset: text("asset"),
  signalType: text("signal_type"),
  confidence: numeric("confidence"),
  timeframe: text("timeframe"),
  entryPrice: numeric("entry_price"),
  stopLoss: numeric("stop_loss"),
  takeProfit: numeric("take_profit"),
  indicators: jsonb("indicators")
});

// Add market sentiment data
export const marketSentiment = pgTable("market_sentiment", {
  id: serial("id").primaryKey(),
  source: text("source").notNull(), // e.g., 'cryptopanic', 'social_media'
  sentiment: text("sentiment").notNull(), // 'positive', 'negative', 'neutral'
  score: numeric("score"), // Sentiment score if available
  symbol: text("symbol"), // Optional specific token
  content: text("content"), // The actual content/text
  timestamp: timestamp("timestamp").notNull().defaultNow(),
  metadata: jsonb("metadata"), // Additional sentiment-related data
});

// Keep existing crypto data tables
export const cryptoData = pgTable("crypto_data", {
  id: serial("id").primaryKey(),
  proxyImageUrl: text("proxy_image_url"),
  description: text("description"),
  financialInfo: jsonb("financial_info").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const historicalPrices = pgTable("historical_prices", {
  id: serial("id").primaryKey(),
  symbol: text("symbol").notNull(),
  price: numeric("price").notNull(),
  volume: numeric("volume"),
  marketCap: numeric("market_cap"),
  timestamp: timestamp("timestamp").notNull(),
  source: text("source").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

// Keep existing schemas
export const insertUserSchema = createInsertSchema(users).pick({
  username: true,
  password: true,
});

export const insertCryptoDataSchema = createInsertSchema(cryptoData).omit({
  id: true,
  createdAt: true,
});

export const insertHistoricalPriceSchema = createInsertSchema(historicalPrices).omit({
  id: true,
  createdAt: true,
});

// Add schema for sonic price feed
export const insertSonicPriceFeedSchema = createInsertSchema(sonicPriceFeed).omit({
  id: true,
  timestamp: true,
});

// Update schema for trading activity
export const insertTradingActivitySchema = createInsertSchema(tradingActivity).omit({
  id: true,
  timestamp: true,
});

export const insertMarketSentimentSchema = createInsertSchema(marketSentiment).omit({
  id: true,
  timestamp: true,
});

export const insertPriceFeedSchema = createInsertSchema(priceFeedData).omit({
  id: true,
  timestamp: true,
});

// Update insert schemas
export const insertWhaleKlineSchema = createInsertSchema(whaleKlineData).omit({
  id: true,
});

export const insertWhaleAlertSchema = createInsertSchema(whaleAlerts).omit({
  id: true,
});

// Keep existing types
export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;
export type InsertCryptoData = z.infer<typeof insertCryptoDataSchema>;
export type CryptoData = typeof cryptoData.$inferSelect;
export type InsertHistoricalPrice = z.infer<typeof insertHistoricalPriceSchema>;
export type HistoricalPrice = typeof historicalPrices.$inferSelect;

// Add types for new tables
export type InsertPriceFeed = z.infer<typeof insertPriceFeedSchema>;
export type PriceFeed = typeof priceFeedData.$inferSelect;

// Export types
export type InsertWhaleKline = z.infer<typeof insertWhaleKlineSchema>;
export type WhaleKline = typeof whaleKlineData.$inferSelect;

export type InsertWhaleAlert = z.infer<typeof insertWhaleAlertSchema>;
export type WhaleAlert = typeof whaleAlerts.$inferSelect;

// Export types
export type InsertSonicPriceFeed = z.infer<typeof insertSonicPriceFeedSchema>;
export type SonicPriceFeed = typeof sonicPriceFeed.$inferSelect;

// Export types
export type InsertTradingActivity = z.infer<typeof insertTradingActivitySchema>;
export type TradingActivity = typeof tradingActivity.$inferSelect;

export type InsertMarketSentiment = z.infer<typeof insertMarketSentimentSchema>;
export type MarketSentiment = typeof marketSentiment.$inferSelect;


// Add chat messages table
export const chatMessages = pgTable("chat_messages", {
  id: serial("id").primaryKey(),
  // Remove foreign key constraint and make it nullable
  userId: integer("user_id"),
  agentType: text("agent_type").notNull(), // 'anthropic', 'hyperbolic', or 'tophat'
  role: text("role").notNull(), // 'user' or 'assistant'
  content: text("content").notNull(),
  metadata: jsonb("metadata"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

// Add schema for chat messages
export const insertChatMessageSchema = createInsertSchema(chatMessages).omit({
  id: true,
  createdAt: true,
}).extend({
  // Make userId optional
  userId: z.number().optional(),
});

// Add types for chat messages
export type InsertChatMessage = z.infer<typeof insertChatMessageSchema>;
export type ChatMessage = typeof chatMessages.$inferSelect;

// Add documentation tables
export const routerDocumentation = pgTable("router_documentation", {
  id: serial("id").primaryKey(),
  routerName: text("router_name").notNull(),
  title: text("title").notNull(),
  content: text("content").notNull(),
  docType: text("doc_type").notNull(), // 'documentation' or 'example'
  category: text("category"),  // 'router', 'router_examples'
  source: text("source").notNull(),
  metadata: jsonb("metadata"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Add new tables for AI agent analysis and tweet tracking
export const aiAnalysis = pgTable("ai_analysis", {
  id: serial("id").primaryKey(),
  agentType: text("agent_type").notNull(), // 'main_instructor', 'market_analysis', 'sentiment_analysis'
  modelName: text("model_name").notNull(),
  analysisType: text("analysis_type").notNull(), // 'trade', 'market', 'sentiment'
  content: text("content").notNull(),
  confidence: numeric("confidence"),
  metadata: jsonb("metadata"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

// Add schemas
export const insertAiAnalysisSchema = createInsertSchema(aiAnalysis).omit({
  id: true,
  createdAt: true,
});

// Add types
export type InsertAiAnalysis = z.infer<typeof insertAiAnalysisSchema>;
export type AiAnalysis = typeof aiAnalysis.$inferSelect;


export const twitterData = pgTable("twitter_data", {
  id: serial("id").primaryKey(),
  tweetId: text("tweet_id").notNull().unique(),
  content: text("content").notNull(),
  author: text("author").notNull(),
  sentiment: text("sentiment"),
  category: text("category"), // 'market', 'technical', 'news', etc.
  tradeRelated: boolean("trade_related").default(false),
  confidence: numeric("confidence"),
  aiAnalysisId: integer("ai_analysis_id").references(() => aiAnalysis.id),
  metadata: jsonb("metadata"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

// Add dashboard posts table after twitterData table
export const dashboardPosts = pgTable("dashboard_posts", {
  id: serial("id").primaryKey(),
  type: text("type").notNull(), // 'tweet', 'trade', 'market_analysis', etc.
  content: text("content").notNull(),
  title: text("title"),
  sourceId: text("source_id"), // ID from original source (tweet_id, trade_id, etc)
  metadata: jsonb("metadata"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

// Add schemas
export const insertTwitterDataSchema = createInsertSchema(twitterData).omit({
  id: true,
  createdAt: true,
});

// Add schemas
export const insertDashboardPostSchema = createInsertSchema(dashboardPosts).omit({
  id: true,
  createdAt: true,
});


// Add types
export type InsertTwitterData = z.infer<typeof insertTwitterDataSchema>;
export type TwitterData = typeof twitterData.$inferSelect;

// Add types
export type InsertDashboardPost = z.infer<typeof insertDashboardPostSchema>;
export type DashboardPost = typeof dashboardPosts.$inferSelect;

// Add schemas
export const insertRouterDocumentationSchema = createInsertSchema(routerDocumentation).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

// Add types
export type InsertRouterDocumentation = z.infer<typeof insertRouterDocumentationSchema>;
export type RouterDocumentation = typeof routerDocumentation.$inferSelect;


// Add transactions table
export const transactions = pgTable("transactions", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").references(() => users.id),
  amount: text("amount").notNull(),
  tokenSymbol: text("token_symbol").notNull(),
  toAddress: text("to_address").notNull(),
  status: text("status").notNull().default("pending"),
  txHash: text("tx_hash"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Add transaction schema
export const insertTransactionSchema = createInsertSchema(transactions).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
  status: true,
  txHash: true,
});

// Add transaction types
export type InsertTransaction = z.infer<typeof insertTransactionSchema>;
export type Transaction = typeof transactions.$inferSelect;


// Add twitter scraping tables after existing twitter data table
export const twitterScrapeData = pgTable("twitter_scrape_data", {
  id: serial("id").primaryKey(),
  username: text("username").notNull(),
  tweetId: text("tweet_id").notNull().unique(),
  content: text("content").notNull(),
  contractAddresses: text("contract_addresses").array(),
  timestamp: timestamp("timestamp").notNull(),
  metadata: jsonb("metadata"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const addressCache = pgTable("address_cache", {
  id: serial("id").primaryKey(),
  address: text("address").notNull().unique(),
  source: text("source").notNull(), // e.g., 'twitter', 'telegram'
  sourceId: text("source_id").notNull(), // e.g., tweet_id or message_id
  firstSeen: timestamp("first_seen").defaultNow().notNull(),
  lastSeen: timestamp("last_seen").defaultNow().notNull(),
  metadata: jsonb("metadata"),
});

// Add insert schemas
export const insertTwitterScrapeDataSchema = createInsertSchema(twitterScrapeData).omit({
  id: true,
  createdAt: true,
});

export const insertAddressCacheSchema = createInsertSchema(addressCache).omit({
  id: true,
  firstSeen: true,
  lastSeen: true,
});

// Add types
export type InsertTwitterScrapeData = z.infer<typeof insertTwitterScrapeDataSchema>;
export type TwitterScrapeData = typeof twitterScrapeData.$inferSelect;

export type InsertAddressCache = z.infer<typeof insertAddressCacheSchema>;
export type AddressCache = typeof addressCache.$inferSelect;

// Add market_updates table to track update status
export const marketUpdates = pgTable("market_updates", {
  id: serial("id").primaryKey(),
  updateType: text("update_type").notNull(), // 'dexscreener', 'defillama', etc.
  status: text("status").notNull(), // 'success', 'failed'
  lastUpdated: timestamp("last_updated").notNull().defaultNow(),
  details: jsonb("details"),
});

// Add schemas
export const insertMarketUpdateSchema = createInsertSchema(marketUpdates).omit({
  id: true,
  lastUpdated: true,
});

// Add types
export type InsertMarketUpdate = z.infer<typeof insertMarketUpdateSchema>;
export type MarketUpdate = typeof marketUpdates.$inferSelect;

// Add agent actions table for monitoring and performance tracking
export const agentActions = pgTable("agent_actions", {
  id: serial("id").primaryKey(),
  agentId: text("agent_id").notNull(), // Identifier for the agent
  agentType: text("agent_type").notNull(), // Type of agent (e.g., trading, market_analysis, etc.)
  actionType: text("action_type").notNull(), // Type of action performed
  status: text("status").notNull(), // success, failure, pending
  errorMessage: text("error_message"), // Error message if status is failure
  duration: numeric("duration"), // Duration in milliseconds
  metadata: jsonb("metadata"), // Additional details about the action
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

// Add schema for agent actions
export const insertAgentActionSchema = createInsertSchema(agentActions).omit({
  id: true,
  createdAt: true,
});

// Add types for agent actions
export type InsertAgentAction = z.infer<typeof insertAgentActionSchema>;
export type AgentAction = typeof agentActions.$inferSelect;

import { integer, boolean } from "drizzle-orm/pg-core";

// Add new tables after existing ones

// Add LazyBear token tracking
export const lazyBearTokens = pgTable("lazy_bear_tokens", {
  id: serial("id").primaryKey(),
  tokenName: text("token_name").notNull(),
  tokenSymbol: text("token_symbol").notNull(),
  description: text("description"),
  walletAddress: text("wallet_address").notNull(),
  transactionHash: text("transaction_hash"),
  shareUrl: text("share_url"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

// Add DEX pool tracking
export const dexPools = pgTable("dex_pools", {
  id: serial("id").primaryKey(),
  dexName: text("dex_name").notNull(), // 'shadow', 'metro', 'equalizer'
  poolName: text("pool_name").notNull(),
  tvlUsd: numeric("tvl_usd"),
  aprPercentage: numeric("apr_percentage"),
  dailyRewardsUsd: numeric("daily_rewards_usd"),
  volume24h: numeric("volume_24h"),
  timestamp: timestamp("timestamp").defaultNow().notNull(),
});

// Add schemas
export const insertLazyBearTokenSchema = createInsertSchema(lazyBearTokens).omit({
  id: true,
  createdAt: true,
});

export const insertDexPoolSchema = createInsertSchema(dexPools).omit({
  id: true,
  timestamp: true,
});

// Add types
export type InsertLazyBearToken = z.infer<typeof insertLazyBearTokenSchema>;
export type LazyBearToken = typeof lazyBearTokens.$inferSelect;

export type InsertDexPool = z.infer<typeof insertDexPoolSchema>;
export type DexPool = typeof dexPools.$inferSelect;

// Add API keys table for external integrations management
// API keys are managed through environment variables
// This approach avoids database storage for sensitive credentials