import { 
  Trade, 
  SocialPost, 
  MarketUpdate, 
  ErrorResponse,
  SocialProvider 
} from '../types'

export class SocialService {
  private providers: SocialProvider[] = []
  private sentimentCache: Map<string, { value: number; timestamp: number }> = new Map()
  private readonly CACHE_DURATION = 5 * 60 * 1000 // 5 minutes

  constructor(providers: SocialProvider[] = []) {
    this.providers = providers
  }

  addProvider(provider: SocialProvider) {
    this.providers.push(provider)
  }

  async post(content: string): Promise<string[]> {
    const postIds = await Promise.all(
      this.providers.map(async (provider) => {
        try {
          return await provider.post(content)
        } catch (error) {
          console.error('Failed to post to provider:', error)
          return null
        }
      })
    )

    return postIds.filter((id): id is string => id !== null)
  }

  async getSentiment(token: string): Promise<number> {
    const cached = this.sentimentCache.get(token)
    if (cached && Date.now() - cached.timestamp < this.CACHE_DURATION) {
      return cached.value
    }

    const sentiments = await Promise.all(
      this.providers.map(async (provider) => {
        try {
          return await provider.getSentiment(token)
        } catch (error) {
          console.error('Failed to get sentiment from provider:', error)
          return null
        }
      })
    )

    const validSentiments = sentiments.filter((s): s is number => s !== null)
    if (validSentiments.length === 0) {
      return 0
    }

    const averageSentiment = validSentiments.reduce((a, b) => a + b, 0) / validSentiments.length
    this.sentimentCache.set(token, {
      value: averageSentiment,
      timestamp: Date.now()
    })

    return averageSentiment
  }

  async getSocialSignals(token: string): Promise<string[]> {
    const allSignals = await Promise.all(
      this.providers.map(async (provider) => {
        try {
          return await provider.getSocialSignals(token)
        } catch (error) {
          console.error('Failed to get social signals from provider:', error)
          return []
        }
      })
    )

    return Array.from(new Set(allSignals.flat()))
  }

  async postTradeUpdate(trade: Trade): Promise<void> {
    const update = this.formatTradeUpdate(trade)
    await Promise.all(
      this.providers.map(async (provider) => {
        try {
          await provider.postTradeUpdate(trade)
        } catch (error) {
          console.error('Failed to post trade update to provider:', error)
        }
      })
    )
  }

  private formatTradeUpdate(trade: Trade): string {
    return `🤖 Trade Alert
Type: ${trade.type}
Token: ${trade.token}
Amount: ${trade.amount}
Price: $${trade.price || 'Market'}
Status: ${trade.status}
Pair: ${trade.pair}`
  }

  private getSentimentEmoji(sentiment: number): string {
    if (sentiment >= 0.6) return '🟢'
    if (sentiment >= 0.4) return '🟡'
    return '🔴'
  }

  private formatMarketUpdate(update: MarketUpdate): string {
    switch (update.type) {
      case 'PRICE':
        return `💰 Price Update\n${update.content}`
      case 'VOLUME':
        return `📊 Volume Update\n${update.content}`
      case 'TRADE':
        return `🔄 Trade Update\n${update.content}`
      case 'ANALYSIS':
        return `📈 Market Analysis\n${update.content}`
      default:
        return update.content
    }
  }
}
