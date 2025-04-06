import { 
  BaseAgent, 
  AgentConfig, 
  Trade, 
  TradeType, 
  MarketAnalysis
} from '@sonickid/core'
import { TelegramProvider } from '@sonickid/social-providers'

export interface TelegramAgentConfig extends AgentConfig {
  telegram: {
    botToken: string
    chatId: string
    ownerIds: string[]
  }
}

export class TelegramAgent extends BaseAgent {
  private provider: TelegramProvider
  private readonly ownerIds: string[]

  constructor(config: TelegramAgentConfig) {
    super(config)
    this.ownerIds = config.telegram.ownerIds
    this.provider = new TelegramProvider({
      botToken: config.telegram.botToken,
      chatId: config.telegram.chatId
    })
  }

  async start(): Promise<void> {
    try {
      // Send startup message
      await this.provider.post('🟢 Telegram Agent is now online and monitoring markets')
      
      // Start market monitoring
      await this.startMarketMonitoring()

      // Start trading if enabled
      if (this.config.tradingParams.maxAmount > 0) {
        await this.startTradingService()
      }
    } catch (err) {
      const error = err as Error
      await this.provider.post(`❌ Error starting agent: ${error.message}`)
      throw error
    }
  }

  async stop(): Promise<void> {
    try {
      await this.provider.post('🔴 Telegram Agent is shutting down')
    } catch (err) {
      const error = err as Error
      console.error('Error during shutdown:', error)
    }
  }

  private async startMarketMonitoring() {
    // Monitor key metrics and post updates
    setInterval(async () => {
      try {
        const metrics = await this.marketService.getKeyMetrics()
        const update = this.formatMarketUpdate(metrics)
        await this.provider.post(update)
      } catch (err) {
        const error = err as Error
        console.error('Market monitoring error:', error)
      }
    }, this.config.socialParams.postInterval)
  }

  private async startTradingService() {
    // Monitor trading opportunities
    setInterval(async () => {
      try {
        const opportunities = await this.tradingService.findOpportunities()
        for (const opp of opportunities) {
          const validatedTrade: Trade = {
            ...opp,
            type: opp.type as TradeType
          }
          if (await this.validateTrade(validatedTrade)) {
            await this.executeTrade(validatedTrade)
          }
        }
      } catch (err) {
        const error = err as Error
        console.error('Auto-trading error:', error)
      }
    }, 30 * 1000) // Every 30 seconds
  }

  async handleCommand(command: string, userId: string) {
    // Only process commands from authorized users
    if (!this.ownerIds.includes(userId)) {
      await this.provider.post('⚠️ Unauthorized command attempt')
      return
    }

    const [cmd, ...args] = command.split(' ')

    switch (cmd.toLowerCase()) {
      case '/status':
        await this.sendStatusUpdate()
        break
      case '/trade':
        await this.handleTradeCommand(args)
        break
      case '/analyze':
        await this.handleAnalyzeCommand(args)
        break
      default:
        await this.provider.post('❓ Unknown command')
    }
  }

  private async sendStatusUpdate() {
    try {
      const status = await this.getSystemStatus()
      await this.provider.post(this.formatStatusUpdate(status))
    } catch (err) {
      const error = err as Error
      await this.provider.post(`❌ Error getting status: ${error.message}`)
    }
  }

  private async getSystemStatus() {
    return {
      uptime: process.uptime(),
      tradingEnabled: this.config.tradingParams.maxAmount > 0,
      lastTrade: await this.tradingService.getLastTrade(),
      marketMetrics: await this.marketService.getKeyMetrics()
    }
  }

  private formatStatusUpdate(status: any) {
    return `📱 System Status
Uptime: ${Math.floor(status.uptime / 3600)}h ${Math.floor((status.uptime % 3600) / 60)}m
Trading: ${status.tradingEnabled ? '✅' : '❌'}
Last Trade: ${status.lastTrade ? `${status.lastTrade.type} ${status.lastTrade.amount} @ $${status.lastTrade.price}` : 'None'}`
  }

  private async handleTradeCommand(args: string[]) {
    try {
      const [type, token, amount] = args
      if (!type || !token || !amount) {
        await this.provider.post('⚠️ Invalid trade command. Format: /trade <BUY|SELL> <token> <amount>')
        return
      }

      const tradeType = type.toUpperCase() as TradeType
      if (tradeType !== 'BUY' && tradeType !== 'SELL') {
        await this.provider.post('⚠️ Invalid trade type. Must be BUY or SELL')
        return
      }

      const trade = await this.tradingService.createTrade({
        type: tradeType,
        token,
        amount: parseFloat(amount)
      })

      const validatedTrade: Trade = {
        ...trade,
        type: tradeType
      }

      if (await this.validateTrade(validatedTrade)) {
        await this.executeTrade(validatedTrade)
      } else {
        await this.provider.post('⚠️ Trade validation failed - check parameters')
      }
    } catch (err) {
      const error = err as Error
      await this.provider.post(`❌ Trade command failed: ${error.message}`)
    }
  }

  private async handleAnalyzeCommand(args: string[]) {
    try {
      const [token] = args
      if (!token) {
        await this.provider.post('⚠️ Invalid analyze command. Format: /analyze <token>')
        return
      }

      const analysis = await this.analyzeMarket(token)
      await this.provider.post(this.formatMarketAnalysis(analysis))
    } catch (err) {
      const error = err as Error
      await this.provider.post(`❌ Analysis failed: ${error.message}`)
    }
  }

  private formatMarketAnalysis(analysis: MarketAnalysis): string {
    return `📊 Market Analysis: ${analysis.recommendation}
Price: $${analysis.price}
24h Volume: $${analysis.volume24h}
Liquidity: $${analysis.liquidity}
Price Change: ${analysis.priceChange}%
Sentiment: ${this.getSentimentEmoji(analysis.sentiment)}

Technical Signals:
${analysis.signals.technical.map(s => `• ${s}`).join('\n')}

Fundamental Signals:
${analysis.signals.fundamental.map(s => `• ${s}`).join('\n')}

Social Signals:
${analysis.signals.social.map(s => `• ${s}`).join('\n')}`
  }

  private getSentimentEmoji(sentiment: number): string {
    if (sentiment >= 0.6) return '🟢'
    if (sentiment >= 0.4) return '🟡'
    return '🔴'
  }

  private formatMarketUpdate(metrics: any) {
    return `📊 Market Update
SONIC Price: $${metrics.sonicPrice}
24h Volume: $${metrics.volume24h}
TVL: $${metrics.tvl}
Top Pairs:
${metrics.topPairs.map((p: any) => `• ${p.name}: $${p.volume24h}`).join('\n')}`
  }
}
