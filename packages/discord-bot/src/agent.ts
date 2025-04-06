import { 
  BaseAgent, 
  AgentConfig, 
  Trade, 
  TradeType, 
  MarketAnalysis
} from '@sonickid/core'
import { DiscordProvider } from '@sonickid/social-providers'

export interface DiscordAgentConfig extends AgentConfig {
  discord: {
    botToken: string
    channelId: string
    webhookUrl?: string
    ownerIds: string[]
    tradingChannelId: string
    analysisChannelId: string
    alertsChannelId: string
  }
}

export class DiscordAgent extends BaseAgent {
  private provider: DiscordProvider
  private readonly ownerIds: string[]
  private readonly channelConfig: {
    trading: string
    analysis: string
    alerts: string
  }

  constructor(config: DiscordAgentConfig) {
    super(config)
    this.ownerIds = config.discord.ownerIds
    this.channelConfig = {
      trading: config.discord.tradingChannelId,
      analysis: config.discord.analysisChannelId,
      alerts: config.discord.alertsChannelId
    }
    this.provider = new DiscordProvider({
      botToken: config.discord.botToken,
      channelId: config.discord.channelId,
      webhookUrl: config.discord.webhookUrl
    })
  }

  async start(): Promise<void> {
    try {
      // Send startup message
      await this.provider.post('🟢 Discord Agent is now online and monitoring markets')
      
      // Create thread for this session
      const sessionThread = await this.provider.createThread(
        await this.provider.post('New Trading Session Started'),
        `Trading Session ${new Date().toISOString()}`
      )

      // Start market monitoring
      await this.startMarketMonitoring()

      // Start trading if enabled
      if (this.config.tradingParams.maxAmount > 0) {
        await this.startTradingService()
      }

      // Pin the status message
      await this.pinStatusMessage()
    } catch (err) {
      const error = err as Error
      await this.provider.post(`❌ Error starting agent: ${error.message}`)
      throw error
    }
  }

  async stop(): Promise<void> {
    try {
      await this.provider.post('🔴 Discord Agent is shutting down')
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

  async handleCommand(command: string, userId: string, channelId: string) {
    // Only process commands from authorized users
    if (!this.ownerIds.includes(userId)) {
      await this.provider.post('⚠️ Unauthorized command attempt')
      return
    }

    const [cmd, ...args] = command.split(' ')

    switch (cmd.toLowerCase()) {
      case '!status':
        await this.sendStatusUpdate(channelId)
        break
      case '!trade':
        if (channelId === this.channelConfig.trading) {
          await this.handleTradeCommand(args, channelId)
        } else {
          await this.provider.post('⚠️ Trading commands only allowed in trading channel')
        }
        break
      case '!analyze':
        if (channelId === this.channelConfig.analysis) {
          await this.handleAnalyzeCommand(args, channelId)
        } else {
          await this.provider.post('⚠️ Analysis commands only allowed in analysis channel')
        }
        break
      case '!alert':
        if (channelId === this.channelConfig.alerts) {
          await this.handleAlertCommand(args, channelId)
        } else {
          await this.provider.post('⚠️ Alert commands only allowed in alerts channel')
        }
        break
      case '!help':
        await this.sendHelpMessage(channelId)
        break
      default:
        await this.provider.post('❓ Unknown command. Use !help for available commands')
    }
  }

  private async sendStatusUpdate(channelId: string) {
    try {
      const status = await this.getSystemStatus()
      const messageId = await this.provider.post(this.formatStatusUpdate(status))
      if (channelId === this.channelConfig.alerts) {
        await this.provider.pinMessage(messageId)
      }
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

  private async pinStatusMessage() {
    const status = await this.getSystemStatus()
    const messageId = await this.provider.post(this.formatStatusUpdate(status))
    await this.provider.pinMessage(messageId)
  }

  private formatStatusUpdate(status: any) {
    return `📱 System Status
Uptime: ${Math.floor(status.uptime / 3600)}h ${Math.floor((status.uptime % 3600) / 60)}m
Trading: ${status.tradingEnabled ? '✅' : '❌'}
Last Trade: ${status.lastTrade ? `${status.lastTrade.type} ${status.lastTrade.amount} @ $${status.lastTrade.price}` : 'None'}`
  }

  private async handleTradeCommand(args: string[], channelId: string) {
    try {
      const [type, token, amount] = args
      if (!type || !token || !amount) {
        await this.provider.post('⚠️ Invalid trade command. Format: !trade <BUY|SELL> <token> <amount>')
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
        const success = await this.executeTrade(validatedTrade)
        if (success) {
          const messageId = await this.provider.post('✅ Trade executed successfully')
          await this.provider.addReaction(messageId, '✅')
        }
      } else {
        await this.provider.post('⚠️ Trade validation failed - check parameters')
      }
    } catch (err) {
      const error = err as Error
      await this.provider.post(`❌ Trade command failed: ${error.message}`)
    }
  }

  private async handleAnalyzeCommand(args: string[], channelId: string) {
    try {
      const [token] = args
      if (!token) {
        await this.provider.post('⚠️ Invalid analyze command. Format: !analyze <token>')
        return
      }

      const analysis = await this.analyzeMarket(token)
      const messageId = await this.provider.post(this.formatMarketAnalysis(analysis))
      
      // Add reactions based on sentiment
      if (analysis.sentiment >= 0.6) {
        await this.provider.addReaction(messageId, '🟢')
      } else if (analysis.sentiment >= 0.4) {
        await this.provider.addReaction(messageId, '🟡')
      } else {
        await this.provider.addReaction(messageId, '🔴')
      }
    } catch (err) {
      const error = err as Error
      await this.provider.post(`❌ Analysis failed: ${error.message}`)
    }
  }

  private async handleAlertCommand(args: string[], channelId: string) {
    const [type, ...message] = args
    if (!type || message.length === 0) {
      await this.provider.post('⚠️ Invalid alert command. Format: !alert <INFO|WARN|ERROR> <message>')
      return
    }

    const alertMessage = message.join(' ')
    let emoji = '📢'
    switch (type.toUpperCase()) {
      case 'INFO':
        emoji = 'ℹ️'
        break
      case 'WARN':
        emoji = '⚠️'
        break
      case 'ERROR':
        emoji = '❌'
        break
    }

    const messageId = await this.provider.post(`${emoji} ALERT: ${alertMessage}`)
    await this.provider.addReaction(messageId, emoji)
  }

  private async sendHelpMessage(channelId: string) {
    const help = `🤖 Available Commands:

!status - Show current system status
!trade <BUY|SELL> <token> <amount> - Execute a trade (trading channel only)
!analyze <token> - Analyze a token (analysis channel only)
!alert <INFO|WARN|ERROR> <message> - Post an alert (alerts channel only)
!help - Show this help message

Channel Configuration:
Trading: <#${this.channelConfig.trading}>
Analysis: <#${this.channelConfig.analysis}>
Alerts: <#${this.channelConfig.alerts}>`

    await this.provider.post(help)
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
