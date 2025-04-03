import { 
  users, transactions, cryptoData, historicalPrices, routerDocumentation, twitterData,
  type User, type InsertUser, type Transaction, type InsertTransaction, 
  type CryptoData, type InsertCryptoData, type HistoricalPrice, type InsertHistoricalPrice,
  type RouterDocumentation, type InsertRouterDocumentation,
  type TwitterData, type InsertTwitterData,
  type MarketUpdate, type InsertMarketUpdate
} from "@shared/schema";
import { sonicPriceFeed, type SonicPriceFeed, type InsertSonicPriceFeed } from "@shared/schema";
import { and, eq, gte, lte, desc } from "drizzle-orm";
import { db } from "./db";
import { subDays } from "date-fns";

// Cache configuration
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes
const CACHE_SIZE = 1000; // Maximum cache entries

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

class Cache<T> {
  private cache: Map<string, CacheEntry<T>> = new Map();

  set(key: string, value: T): void {
    if (this.cache.size >= CACHE_SIZE) {
      // Remove oldest entry if cache is full
      const oldestKey = this.cache.keys().next().value;
      this.cache.delete(oldestKey);
    }
    this.cache.set(key, { data: value, timestamp: Date.now() });
  }

  get(key: string): T | undefined {
    const entry = this.cache.get(key);
    if (!entry) return undefined;
    if (Date.now() - entry.timestamp > CACHE_TTL) {
      this.cache.delete(key);
      return undefined;
    }
    return entry.data;
  }

  clear(): void {
    this.cache.clear();
  }
}

export interface IStorage {
  // User methods
  getUser(id: number): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;

  // Transaction methods
  createTransaction(transaction: InsertTransaction): Promise<Transaction>;
  getUserTransactions(userId: number): Promise<Transaction[]>;
  updateTransactionStatus(id: number, status: string, hash?: string): Promise<Transaction | undefined>;

  // Crypto data methods
  createCryptoData(data: InsertCryptoData): Promise<CryptoData>;
  getCryptoData(id: number): Promise<CryptoData | undefined>;
  listCryptoData(limit?: number, offset?: number): Promise<CryptoData[]>;

  // Historical price methods
  createHistoricalPrice(data: InsertHistoricalPrice): Promise<HistoricalPrice>;
  getHistoricalPrices(symbol: string, limit?: number): Promise<HistoricalPrice[]>;
  getHistoricalPricesByDateRange(symbol: string, startDate: Date, endDate: Date): Promise<HistoricalPrice[]>;

  // Sonic price feed methods
  insertPriceFeed(data: InsertSonicPriceFeed): Promise<SonicPriceFeed>;
  getPriceHistory(pairAddress: string, startTime: Date, endTime: Date): Promise<SonicPriceFeed[]>;
  cleanupOldPrices(): Promise<void>;

  // Add router documentation methods
  createRouterDocumentation(data: InsertRouterDocumentation): Promise<RouterDocumentation>;
  getRouterDocumentation(routerName: string): Promise<RouterDocumentation[]>;
  listRouterDocumentation(limit?: number, offset?: number): Promise<RouterDocumentation[]>;

  // Add Twitter data methods  
  createTwitterData(data: InsertTwitterData): Promise<TwitterData>;
  getTwitterData(limit?: number, offset?: number): Promise<TwitterData[]>;
  getTwitterDataByCategory(category: string): Promise<TwitterData[]>;

  // Market data methods
  savePriceFeed(data: InsertSonicPriceFeed): Promise<SonicPriceFeed>;
  getLatestPrices(chain: string, limit?: number): Promise<SonicPriceFeed[]>;
  getPricesByPair(pairAddress: string, startTime: Date, endTime: Date): Promise<SonicPriceFeed[]>;
  logMarketUpdate(data: InsertMarketUpdate): Promise<MarketUpdate>;
  getLastMarketUpdate(updateType: string): Promise<MarketUpdate | undefined>;
}

export class DatabaseStorage implements IStorage {
  private userCache = new Cache<User>();
  private transactionCache = new Cache<Transaction[]>();
  private historicalPriceCache = new Cache<HistoricalPrice[]>();
  private priceHistoryCache = new Cache<SonicPriceFeed[]>();
  private routerDocCache = new Cache<RouterDocumentation[]>();
  private twitterDataCache = new Cache<TwitterData[]>();
  private priceCache = new Cache<SonicPriceFeed[]>();
  private updateCache = new Cache<MarketUpdate>();

  // User methods
  async getUser(id: number): Promise<User | undefined> {
    const cacheKey = `user_${id}`;
    const cached = this.userCache.get(cacheKey);
    if (cached) return cached;

    const user = await db.select().from(users).where(eq(users.id, id)).limit(1);
    if (user.length > 0) {
      this.userCache.set(cacheKey, user[0]);
      return user[0];
    }
    return undefined;
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    const cacheKey = `user_${username}`;
    const cached = this.userCache.get(cacheKey);
    if (cached) return cached;

    const user = await db.select().from(users).where(eq(users.username, username)).limit(1);
    if (user.length > 0) {
      this.userCache.set(cacheKey, user[0]);
      return user[0];
    }
    return undefined;
  }

  async createUser(user: InsertUser): Promise<User> {
    const [newUser] = await db.insert(users).values(user).returning();
    this.userCache.set(`user_${newUser.id}`, newUser);
    return newUser;
  }

  // Transaction methods with caching
  async createTransaction(transaction: InsertTransaction): Promise<Transaction> {
    const [newTransaction] = await db.insert(transactions).values(transaction).returning();

    // Invalidate user transactions cache
    if (transaction.userId) {
      this.transactionCache.get(`user_transactions_${transaction.userId}`);
    }

    return newTransaction;
  }

  async getUserTransactions(userId: number): Promise<Transaction[]> {
    const cacheKey = `user_transactions_${userId}`;
    const cached = this.transactionCache.get(cacheKey);
    if (cached) return cached;

    const userTransactions = await db
      .select()
      .from(transactions)
      .where(eq(transactions.userId, userId))
      .orderBy(transactions.timestamp);

    this.transactionCache.set(cacheKey, userTransactions);
    return userTransactions;
  }

  async updateTransactionStatus(id: number, status: string, hash?: string): Promise<Transaction | undefined> {
    const [updated] = await db
      .update(transactions)
      .set({ status, transactionHash: hash })
      .where(eq(transactions.id, id))
      .returning();

    if (updated && updated.userId) {
      // Invalidate cache
      this.transactionCache.get(`user_transactions_${updated.userId}`);
    }

    return updated;
  }

  // Historical price methods with caching
  async createHistoricalPrice(data: InsertHistoricalPrice): Promise<HistoricalPrice> {
    const [price] = await db
      .insert(historicalPrices)
      .values(data)
      .returning();

    // Invalidate symbol cache
    this.historicalPriceCache.get(`prices_${data.symbol}`);

    return price;
  }

  async getHistoricalPrices(symbol: string, limit: number = 100): Promise<HistoricalPrice[]> {
    const cacheKey = `prices_${symbol}_${limit}`;
    const cached = this.historicalPriceCache.get(cacheKey);
    if (cached) return cached;

    const prices = await db
      .select()
      .from(historicalPrices)
      .where(eq(historicalPrices.symbol, symbol))
      .orderBy(historicalPrices.timestamp)
      .limit(limit);

    this.historicalPriceCache.set(cacheKey, prices);
    return prices;
  }

  async getHistoricalPricesByDateRange(
    symbol: string,
    startDate: Date,
    endDate: Date
  ): Promise<HistoricalPrice[]> {
    const cacheKey = `prices_${symbol}_${startDate.toISOString()}_${endDate.toISOString()}`;
    const cached = this.historicalPriceCache.get(cacheKey);
    if (cached) return cached;

    const prices = await db
      .select()
      .from(historicalPrices)
      .where(
        and(
          eq(historicalPrices.symbol, symbol),
          gte(historicalPrices.timestamp, startDate),
          lte(historicalPrices.timestamp, endDate)
        )
      )
      .orderBy(historicalPrices.timestamp);

    this.historicalPriceCache.set(cacheKey, prices);
    return prices;
  }

  // Sonic price feed methods with caching
  async insertPriceFeed(data: InsertSonicPriceFeed): Promise<SonicPriceFeed> {
    const [price] = await db
      .insert(sonicPriceFeed)
      .values(data)
      .returning();

    // Invalidate relevant cache entries
    const cacheKey = `price_history_${data.pairAddress}`;
    this.priceHistoryCache.get(cacheKey);

    return price;
  }

  async getPriceHistory(
    pairAddress: string,
    startTime: Date,
    endTime: Date
  ): Promise<SonicPriceFeed[]> {
    const cacheKey = `price_history_${pairAddress}_${startTime.toISOString()}_${endTime.toISOString()}`;
    const cached = this.priceHistoryCache.get(cacheKey);
    if (cached) return cached;

    const prices = await db
      .select()
      .from(sonicPriceFeed)
      .where(
        and(
          eq(sonicPriceFeed.pairAddress, pairAddress),
          gte(sonicPriceFeed.timestamp, startTime),
          lte(sonicPriceFeed.timestamp, endTime)
        )
      )
      .orderBy(sonicPriceFeed.timestamp);

    this.priceHistoryCache.set(cacheKey, prices);
    return prices;
  }

  async cleanupOldPrices(): Promise<void> {
    const oneWeekAgo = subDays(new Date(), 7);
    await db
      .delete(sonicPriceFeed)
      .where(lte(sonicPriceFeed.timestamp, oneWeekAgo));

    // Clear all caches since data was deleted
    this.priceHistoryCache.clear();
  }

  // Add router documentation implementation
  async createRouterDocumentation(data: InsertRouterDocumentation): Promise<RouterDocumentation> {
    const [newDoc] = await db
      .insert(routerDocumentation)
      .values(data)
      .returning();

    // Invalidate router cache
    this.routerDocCache.get(`router_${data.routerName}`);

    return newDoc;
  }

  async getRouterDocumentation(routerName: string): Promise<RouterDocumentation[]> {
    const cacheKey = `router_${routerName}`;
    const cached = this.routerDocCache.get(cacheKey);
    if (cached) return cached;

    const docs = await db
      .select()
      .from(routerDocumentation)
      .where(eq(routerDocumentation.routerName, routerName))
      .orderBy(routerDocumentation.createdAt);

    this.routerDocCache.set(cacheKey, docs);
    return docs;
  }

  async listRouterDocumentation(limit: number = 100, offset: number = 0): Promise<RouterDocumentation[]> {
    return await db
      .select()
      .from(routerDocumentation)
      .limit(limit)
      .offset(offset)
      .orderBy(routerDocumentation.createdAt);
  }

  // Add Twitter data implementation
  async createTwitterData(data: InsertTwitterData): Promise<TwitterData> {
    const [tweet] = await db
      .insert(twitterData)
      .values(data)
      .returning();

    // Invalidate category cache
    if (data.category) {
      this.twitterDataCache.get(`category_${data.category}`);
    }

    return tweet;
  }

  async getTwitterData(limit: number = 100, offset: number = 0): Promise<TwitterData[]> {
    return await db
      .select()
      .from(twitterData)
      .limit(limit)
      .offset(offset)
      .orderBy(twitterData.createdAt);
  }

  async getTwitterDataByCategory(category: string): Promise<TwitterData[]> {
    const cacheKey = `category_${category}`;
    const cached = this.twitterDataCache.get(cacheKey);
    if (cached) return cached;

    const tweets = await db
      .select()
      .from(twitterData)
      .where(eq(twitterData.category, category))
      .orderBy(twitterData.createdAt);

    this.twitterDataCache.set(cacheKey, tweets);
    return tweets;
  }

  async savePriceFeed(data: InsertSonicPriceFeed): Promise<SonicPriceFeed> {
    const [price] = await db
      .insert(sonicPriceFeed)
      .values(data)
      .returning();

    // Invalidate cache
    this.priceCache.clear();
    return price;
  }

  async getLatestPrices(chain: string, limit: number = 100): Promise<SonicPriceFeed[]> {
    const cacheKey = `prices_${chain}_${limit}`;
    const cached = this.priceCache.get(cacheKey);
    if (cached) return cached;

    const prices = await db
      .select()
      .from(sonicPriceFeed)
      .where(eq(sonicPriceFeed.chain, chain))
      .orderBy(desc(sonicPriceFeed.timestamp))
      .limit(limit);

    this.priceCache.set(cacheKey, prices);
    return prices;
  }

  async getPricesByPair(
    pairAddress: string,
    startTime: Date,
    endTime: Date
  ): Promise<SonicPriceFeed[]> {
    const cacheKey = `pair_${pairAddress}_${startTime.toISOString()}_${endTime.toISOString()}`;
    const cached = this.priceCache.get(cacheKey);
    if (cached) return cached;

    const prices = await db
      .select()
      .from(sonicPriceFeed)
      .where(
        and(
          eq(sonicPriceFeed.pairAddress, pairAddress),
          gte(sonicPriceFeed.timestamp, startTime),
          lte(sonicPriceFeed.timestamp, endTime)
        )
      )
      .orderBy(sonicPriceFeed.timestamp);

    this.priceCache.set(cacheKey, prices);
    return prices;
  }

  async logMarketUpdate(data: InsertMarketUpdate): Promise<MarketUpdate> {
    const [update] = await db
      .insert(marketUpdates)
      .values(data)
      .returning();

    // Invalidate cache
    this.updateCache.clear();
    return update;
  }

  async getLastMarketUpdate(updateType: string): Promise<MarketUpdate | undefined> {
    const cacheKey = `update_${updateType}`;
    const cached = this.updateCache.get(cacheKey);
    if (cached) return cached[0];

    const [update] = await db
      .select()
      .from(marketUpdates)
      .where(eq(marketUpdates.updateType, updateType))
      .orderBy(desc(marketUpdates.lastUpdated))
      .limit(1);

    if (update) {
      this.updateCache.set(cacheKey, [update]);
    }
    return update;
  }
}

export const storage = new DatabaseStorage();