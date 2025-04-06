// Re-export subgraph types
export type { TokenData, PairData, SwapData } from '../services/subgraph'

// Common Types
export type ErrorResponse = {
  error: string
  code: number
  details?: any
  message?: string
}

// Trade Types
export type TradeType = 'BUY' | 'SELL'
export type TradeStatus = 'PENDING' | 'COMPLETED' | 'FAILED'

export interface Trade {
  id: string
  timestamp: number
  type: TradeType
  token: string
  amount: number
  price?: number
  slippage?: number
  deadline?: number
  pair: string
  status: TradeStatus
}

// Network Types
export interface NetworkConfig {
  rpcUrl: string
  chainId: number
  name: string
  nativeCurrency: {
    name: string
    symbol: string
    decimals: number
  }
}

// Trading Types
export interface TradingParams {
  maxAmount: number
  minAmount: number
  slippageTolerance: number
  gasLimit: number
  defaultPairs: string[]
}

// Social Types
export interface SocialParams {
  postInterval: number
  engagementThreshold: number
  autoReply: boolean
  sentimentThreshold: number
}

export interface SocialPost {
  id: string
  content: string
  timestamp: number
  platform: string
  engagement?: {
    likes: number
    replies: number
    shares: number
  }
}

export interface MarketUpdate {
  type: 'PRICE' | 'VOLUME' | 'TRADE' | 'ANALYSIS'
  content: string
  data: any
  timestamp: number
}

// Platform Interface
export interface SocialPlatform {
  name: string
  post(content: string): Promise<string>
  delete?(messageId: string): Promise<boolean>
  getEngagement?(messageId: string): Promise<{
    likes?: number
    retweets?: number
    replies?: number
  }>
  replyToMessage?(messageId: string, content: string): Promise<string>
}

// DeFi Types
export interface DefiParams {
  minLiquidity: number
  minVolume: number
  maxPriceImpact: number
  targetDex: string[]
}

export interface Protocol {
  name: string
  address: string
  type: 'DEX' | 'LENDING' | 'YIELD'
  tvl: number
  apr?: number
}

export interface LiquidityPool {
  address: string
  token0: string
  token1: string
  reserve0: number
  reserve1: number
  totalSupply: number
  apr: number
}

export interface StrategyAnalysis {
  protocol: Protocol
  pool: LiquidityPool
  expectedReturn: number
  risk: 'LOW' | 'MEDIUM' | 'HIGH'
  recommendation: string
}

// API Keys and Service Configs
export interface ServiceConfig {
  // News and Market Data
  cryptoPanicApiKey: string
  
  // NFT Marketplace
  paintswapApiKey: string
  
  // Social Media
  twitterApiKey: string
  twitterApiSecret: string
  twitterAccessToken: string
  twitterAccessTokenSecret: string
  twitterBearerToken: string
  twitterAuthToken: string
  
  discordBotToken: string
  discordWebhookUrl?: string
  
  telegramBotToken: string
  telegramChatId: string
  
  // Third Web Engine
  thirdwebApiKey: string
  thirdwebSecretKey: string
  
  // Additional Services
  defiLlamaEnabled: boolean
  subgraphEndpoint: string
}

// Agent Types
export interface AgentConfig {
  name: string
  networks: NetworkConfig[]
  tradingParams: TradingParams
  socialParams: SocialParams
  defiParams: DefiParams
  serviceConfig: ServiceConfig
}

// Market Analysis Types
export interface MarketAnalysis {
  timestamp: number
  price: number
  volume24h: number
  liquidity: number
  priceChange: number
  sentiment: number
  recommendation: string
  signals: {
    technical: string[]
    fundamental: string[]
    social: string[]
  }
}

// Service Types
export interface MarketDataProvider {
  getPrice(token: string): Promise<number>
  getVolume(token: string): Promise<number>
  getPriceChange(token: string): Promise<number>
}

export interface TradingProvider {
  executeTrade(trade: Trade): Promise<boolean>
  calculatePriceImpact(trade: Trade): Promise<number>
  findOpportunities(): Promise<Trade[]>
}

export interface DefiProvider {
  getLiquidity(token: string): Promise<number>
  getYield(token: string): Promise<number>
  getPoolInfo(token: string): Promise<any>
}

export interface SocialProvider {
  post(content: string): Promise<string>
  getSentiment(token: string): Promise<number>
  getSocialSignals(token: string): Promise<string[]>
  postTradeUpdate(trade: Trade): Promise<void>
}

// Re-export service interfaces
export * from '../services/nft'
export * from '../services/tvl'
