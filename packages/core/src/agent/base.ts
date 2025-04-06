import { MarketService } from '../services/market'
import { TradingService } from '../services/trading'
import { DefiService } from '../services/defi'
import { SocialService } from '../services/social'
import { NFTService } from '../services/nft'
import { TVLService } from '../services/tvl'
import { ProtocolService } from '../services/protocols'
import { SubgraphService } from '../services/subgraph'
import { ThirdWebService, ContractWriteConfig } from '../services/thirdweb'
import { PairData } from '../services/subgraph'
import { 
  AgentConfig, 
  Trade, 
  MarketAnalysis,
  TradeType,
  TradeStatus,
  NFTMarketStats,
  TVLData,
  NFTSale,
  Protocol,
  LiquidityPool
} from '../types'

export abstract class BaseAgent {
  protected marketService: MarketService
  protected tradingService: TradingService
  protected defiService: DefiService
  protected socialService: SocialService
  protected nftService: NFTService
  protected tvlService: TVLService
  protected protocolService: ProtocolService
  protected subgraphService: SubgraphService
  protected thirdwebService: ThirdWebService
  protected config: AgentConfig

  constructor(config: AgentConfig) {
    this.config = config
    this.marketService = new MarketService(config.serviceConfig.cryptoPanicApiKey)
    this.tradingService = new TradingService()
    this.defiService = new DefiService()
    this.socialService = new SocialService()
    this.nftService = new NFTService(config.serviceConfig.paintswapApiKey)
    this.tvlService = new TVLService()
    this.protocolService = new ProtocolService(config.serviceConfig)
    this.subgraphService = new SubgraphService(config.serviceConfig)
    this.thirdwebService = new ThirdWebService(config.serviceConfig)
  }

  abstract start(): Promise<void>
  abstract stop(): Promise<void>

  // Blockchain operations
  protected async deployContract(
    name: string,
    abi: any[],
    bytecode: string,
    wallet: string,
    args: any[] = []
  ): Promise<string> {
    try {
      await this.thirdwebService.initialize()
      return await this.thirdwebService.deployContract(name, abi, bytecode, wallet, args)
    } catch (error) {
      console.error('Contract deployment failed:', error)
      throw error
    }
  }

  protected async readContract(
    contractName: string,
    functionName: string,
    args: any[] = []
  ): Promise<any> {
    try {
      await this.thirdwebService.initialize()
      return await this.thirdwebService.readContract(contractName, functionName, args)
    } catch (error) {
      console.error('Contract read failed:', error)
      throw error
    }
  }

  protected async writeContract(
    contractName: string,
    functionName: string,
    args: any[] = [],
    wallet: string,
    config: ContractWriteConfig = {}
  ): Promise<string> {
    try {
      await this.thirdwebService.initialize()
      return await this.thirdwebService.writeContract(contractName, functionName, args, wallet, config)
    } catch (error) {
      console.error('Contract write failed:', error)
      throw error
    }
  }

  // Wallet Management
  protected async addWallet(name: string, privateKey: string): Promise<string> {
    try {
      await this.thirdwebService.initialize()
      return await this.thirdwebService.addWallet(name, privateKey)
    } catch (error) {
      console.error('Add wallet failed:', error)
      throw error
    }
  }

  protected async createSmartAccount(chain: number, sponsorGas: boolean = true): Promise<string> {
    try {
      await this.thirdwebService.initialize()
      return await this.thirdwebService.createSmartAccount({
        chain,
        sponsorGas
      })
    } catch (error) {
      console.error('Smart account creation failed:', error)
      throw error
    }
  }

  protected async createInAppWallet(
    authMode: 'popup' | 'redirect' = 'popup',
    options: string[] = ['google', 'email'],
    smartAccount?: { chain: number; sponsorGas: boolean }
  ): Promise<string> {
    try {
      await this.thirdwebService.initialize()
      return await this.thirdwebService.createInAppWallet({
        auth: {
          mode: authMode,
          options
        },
        smartAccount
      })
    } catch (error) {
      console.error('In-app wallet creation failed:', error)
      throw error
    }
  }

  // NFT operations with pre-configured contract
  protected async mintNFT(
    to: string,
    metadata: {
      name: string
      description: string
      image: string
      attributes?: { trait_type: string; value: string }[]
    }
  ): Promise<string> {
    try {
      await this.thirdwebService.initialize()
      return await this.thirdwebService.mintNFT(to, metadata)
    } catch (error) {
      console.error('NFT minting failed:', error)
      throw error
    }
  }

  protected async getNFTBalance(address: string): Promise<number> {
    try {
      await this.thirdwebService.initialize()
      return await this.thirdwebService.getNFTBalance(address)
    } catch (error) {
      console.error('Get NFT balance failed:', error)
      throw error
    }
  }

  // Generic contract operations

  async analyzeMarket(token: string): Promise<MarketAnalysis> {
    const [
      price, 
      volume, 
      liquidity, 
      tvlData,
      tokenMetrics
    ] = await Promise.all([
      this.marketService.getPrice(token),
      this.marketService.getVolume(token),
      this.defiService.getLiquidity(token),
      this.tvlService.getChainTVL('sonic'),
      this.subgraphService.analyzeTokenMetrics(token)
    ])

    const sentiment = await this.analyzeSentiment(token)
    const signals = await this.getSignals(token, tvlData, tokenMetrics)

    return {
      timestamp: Date.now(),
      price,
      volume24h: volume,
      liquidity,
      priceChange: tokenMetrics.priceChange24h,
      sentiment,
      recommendation: this.generateRecommendation(signals),
      signals
    }
  }

  async analyzeSentiment(token: string): Promise<number> {
    const [social, news] = await Promise.all([
      this.socialService.getSentiment(token),
      this.marketService.getNewsAnalysis(token)
    ])

    // Weighted average: 60% social, 40% news
    return (social * 0.6) + (news * 0.4)
  }

  async validateTrade(trade: Trade): Promise<boolean> {
    // Basic validation
    if (trade.amount < this.config.tradingParams.minAmount ||
        trade.amount > this.config.tradingParams.maxAmount) {
      return false
    }

    // Check liquidity
    const liquidity = await this.defiService.getLiquidity(trade.token)
    if (liquidity < this.config.defiParams.minLiquidity) {
      return false
    }

    // Check volume using subgraph data
    const tokenData = await this.subgraphService.getToken(trade.token)
    const volume = parseFloat(tokenData.volume)
    if (volume < this.config.defiParams.minVolume) {
      return false
    }

    // Find best protocol for trade
    const protocol = await this.findBestProtocol(trade)
    if (!protocol) {
      return false
    }

    // Check price impact
    const priceImpact = await this.protocolService.calculatePriceImpact(protocol.name, trade)
    if (priceImpact > this.config.defiParams.maxPriceImpact) {
      return false
    }

    return true
  }

  protected async executeTrade(trade: Trade): Promise<boolean> {
    if (!await this.validateTrade(trade)) {
      return false
    }

    try {
      // Find best protocol for trade
      const protocol = await this.findBestProtocol(trade)
      if (!protocol) {
        throw new Error('No suitable protocol found for trade')
      }

      // Execute trade through protocol
      const txHash = await this.protocolService.executeTrade(protocol.name, trade)
      
      // Post trade update
      await this.socialService.postTradeUpdate(trade)

      return true
    } catch (error) {
      console.error('Trade execution failed:', error)
      return false
    }
  }

  async analyzeNFTMarket(collection?: string): Promise<{
    marketStats: NFTMarketStats
    trend: 'up' | 'down' | 'stable'
    confidence: number
    summary: string
    recentSales: NFTSale[]
  }> {
    const analysis = await this.nftService.analyzeMarket(collection)
    return {
      marketStats: analysis.stats,
      trend: analysis.trend,
      confidence: analysis.confidence,
      summary: analysis.summary,
      recentSales: analysis.recentSales
    }
  }

  async analyzeTVLTrends(): Promise<{
    tvlData: TVLData
    trend: 'growing' | 'declining' | 'stable'
    confidence: number
    summary: string
  }> {
    const analysis = await this.tvlService.analyzeTVLTrends('sonic')
    const tvlData = await this.tvlService.getChainTVL('sonic')
    return {
      tvlData,
      trend: analysis.trend,
      confidence: analysis.confidence,
      summary: analysis.summary
    }
  }

  async analyzeProtocols(): Promise<{
    protocols: Protocol[]
    bestForTrading: string
    bestForYield: string
    summary: string
  }> {
    const protocols = await Promise.all(
      ['SHADOW', 'METRO', 'BEETS', 'SWPX', 'EQUALIZER'].map(name =>
        this.protocolService.getProtocolInfo(name)
      )
    )

    // Find best protocols
    const dexes = protocols.filter(p => p.type === 'DEX')
    const yieldProtocols = protocols.filter(p => p.type === 'YIELD')

    const bestForTrading = dexes.reduce((a, b) => a.tvl > b.tvl ? a : b).name
    const bestForYield = yieldProtocols.reduce((a, b) => (a.apr || 0) > (b.apr || 0) ? a : b).name

    // Generate summary
    const totalTVL = protocols.reduce((sum, p) => sum + p.tvl, 0)
    const summary = `Total TVL across protocols: $${totalTVL.toFixed(2)}M. ` +
      `${bestForTrading} leads in trading volume. ` +
      `${bestForYield} offers highest yields.`

    return {
      protocols,
      bestForTrading,
      bestForYield,
      summary
    }
  }

  async analyzeTokenPairs(token: string): Promise<{
    pairs: PairData[]
    topPairsByVolume: string[]
    topPairsByLiquidity: string[]
    summary: string
  }> {
    // Get all pairs involving the token
    const [volumePairs, liquidityPairs] = await Promise.all([
      this.subgraphService.getTopPairs(10, 'volumeUSD'),
      this.subgraphService.getTopPairs(10, 'reserveUSD')
    ])

    const tokenPairs = [...volumePairs, ...liquidityPairs].filter(pair => 
      pair.token0.id.toLowerCase() === token.toLowerCase() ||
      pair.token1.id.toLowerCase() === token.toLowerCase()
    )

    const uniquePairs = Array.from(new Set(tokenPairs.map(p => p.id)))
      .map(id => tokenPairs.find(p => p.id === id)!)

    // Sort by volume and liquidity
    const byVolume = [...uniquePairs].sort((a, b) => 
      parseFloat(b.volumeUSD) - parseFloat(a.volumeUSD)
    )
    const byLiquidity = [...uniquePairs].sort((a, b) => 
      parseFloat(b.reserveUSD) - parseFloat(a.reserveUSD)
    )

    // Generate summary
    const totalVolume = uniquePairs.reduce((sum, p) => sum + parseFloat(p.volumeUSD), 0)
    const totalLiquidity = uniquePairs.reduce((sum, p) => sum + parseFloat(p.reserveUSD), 0)
    const summary = `Found ${uniquePairs.length} active pairs with ` +
      `$${totalVolume.toFixed(2)} 24h volume and ` +
      `$${totalLiquidity.toFixed(2)} total liquidity.`

    return {
      pairs: uniquePairs,
      topPairsByVolume: byVolume.slice(0, 5).map(p => p.id),
      topPairsByLiquidity: byLiquidity.slice(0, 5).map(p => p.id),
      summary
    }
  }

  private async findBestProtocol(trade: Trade): Promise<Protocol | null> {
    try {
      const protocols = await Promise.all(
        ['SHADOW', 'METRO', 'BEETS', 'SWPX', 'EQUALIZER'].map(async name => {
          try {
            const protocol = await this.protocolService.getProtocolInfo(name)
            const impact = await this.protocolService.calculatePriceImpact(name, trade)
            return { ...protocol, priceImpact: impact }
          } catch {
            return null
          }
        })
      )

      // Filter out failed queries and sort by price impact
      return protocols
        .filter((p): p is Protocol & { priceImpact: number } => 
          p !== null && p.type === 'DEX' && p.tvl >= this.config.defiParams.minLiquidity
        )
        .sort((a, b) => a.priceImpact - b.priceImpact)[0] || null
    } catch {
      return null
    }
  }

  private async getSignals(
    token: string, 
    tvlData: TVLData,
    tokenMetrics: {
      volumeChange24h: number
      liquidityChange24h: number
      priceChange24h: number
      trend: 'up' | 'down' | 'stable'
      confidence: number
    }
  ) {
    const [technical, fundamental, social] = await Promise.all([
      this.marketService.getTechnicalSignals(token),
      this.marketService.getFundamentalSignals(token),
      this.socialService.getSocialSignals(token)
    ])

    // Add TVL signals
    if (tvlData.tvlChange24h > 5) {
      fundamental.push('Strong TVL growth in last 24h')
    } else if (tvlData.tvlChange24h < -5) {
      fundamental.push('Significant TVL decline in last 24h')
    }

    // Add protocol dominance signals
    const topProtocol = tvlData.protocols[0]
    if (topProtocol && topProtocol.dominance > 50) {
      fundamental.push(`High protocol dominance: ${topProtocol.name}`)
    }

    // Add on-chain signals
    if (tokenMetrics.volumeChange24h > 20) {
      technical.push('Significant volume increase')
    }
    if (tokenMetrics.liquidityChange24h > 10) {
      fundamental.push('Strong liquidity growth')
    }
    if (tokenMetrics.trend === 'up' && tokenMetrics.confidence > 0.7) {
      technical.push('Strong on-chain momentum')
    }

    return {
      technical,
      fundamental,
      social
    }
  }

  private generateRecommendation(signals: MarketAnalysis['signals']): string {
    // Count positive and negative signals
    const counts = {
      positive: 0,
      negative: 0,
      neutral: 0
    }

    const allSignals = [
      ...signals.technical,
      ...signals.fundamental,
      ...signals.social
    ]

    allSignals.forEach(signal => {
      if (signal.includes('buy') || signal.includes('bullish') || signal.includes('growth')) {
        counts.positive++
      } else if (signal.includes('sell') || signal.includes('bearish') || signal.includes('decline')) {
        counts.negative++
      } else {
        counts.neutral++
      }
    })

    // Generate recommendation based on signal counts
    if (counts.positive > counts.negative * 2) {
      return 'Strong Buy'
    } else if (counts.positive > counts.negative) {
      return 'Buy'
    } else if (counts.negative > counts.positive * 2) {
      return 'Strong Sell'
    } else if (counts.negative > counts.positive) {
      return 'Sell'
    } else {
      return 'Hold'
    }
  }
}
