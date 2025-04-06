import { ErrorResponse } from '../types'

export interface NewsItem {
  id: string
  title: string
  url: string
  published_at: string
  source: {
    title: string
    region: string
    domain: string
  }
  currencies: Array<{
    code: string
    title: string
    slug: string
  }>
  votes: {
    positive: number
    negative: number
    important: number
  }
  sentiment: 'positive' | 'negative' | 'neutral'
}

export interface NewsAnalysis {
  sentiment: number // 0 to 1
  confidence: number // 0 to 1
  summary: string
  topStories: NewsItem[]
  relatedTokens: Array<{
    symbol: string
    mentions: number
    sentiment: number
  }>
}

type SentimentScore = number

export class NewsService {
  private readonly apiKey: string
  private readonly baseUrl = 'https://cryptopanic.com/api/v1'
  private readonly cache = new Map<string, {
    data: NewsAnalysis
    timestamp: number
  }>()
  private readonly CACHE_DURATION = 5 * 60 * 1000 // 5 minutes

  constructor(apiKey: string) {
    this.apiKey = apiKey
  }

  async getNews(token: string): Promise<NewsItem[]> {
    try {
      const response = await fetch(
        `${this.baseUrl}/posts/?auth_token=${this.apiKey}&currencies=${token}&kind=news&public=true`,
        {
          headers: {
            'Accept': 'application/json'
          }
        }
      )

      if (!response.ok) {
        throw new Error(`CryptoPanic API error: ${response.statusText}`)
      }

      const data = await response.json()
      return data.results
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to fetch news: ${error.message}`)
    }
  }

  async analyzeNews(token: string): Promise<NewsAnalysis> {
    // Check cache
    const cached = this.cache.get(token)
    if (cached && Date.now() - cached.timestamp < this.CACHE_DURATION) {
      return cached.data
    }

    try {
      const news = await this.getNews(token)
      const analysis = this.performAnalysis(news)
      
      // Cache the result
      this.cache.set(token, {
        data: analysis,
        timestamp: Date.now()
      })

      return analysis
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to analyze news: ${error.message}`)
    }
  }

  private performAnalysis(news: NewsItem[]): NewsAnalysis {
    // Calculate overall sentiment
    const sentimentScores: SentimentScore[] = news.map(item => {
      switch (item.sentiment) {
        case 'positive':
          return item.votes.important ? 1 : 0.75
        case 'negative':
          return item.votes.important ? 0 : 0.25
        default:
          return 0.5
      }
    })

    const totalSentiment = sentimentScores.reduce((sum: number, score: number) => sum + score, 0)
    const sentiment = sentimentScores.length > 0 ? totalSentiment / sentimentScores.length : 0.5

    // Calculate confidence based on votes and sources
    const totalVotes = news.reduce((sum, item) => 
      sum + item.votes.positive + item.votes.negative + item.votes.important, 0
    )
    const confidence = Math.min(totalVotes / (news.length * 10 || 1), 1) // Normalize to 0-1

    // Find related tokens
    const tokenMentions = new Map<string, {
      mentions: number
      positiveVotes: number
      negativeVotes: number
    }>()

    news.forEach(item => {
      item.currencies.forEach(currency => {
        const current = tokenMentions.get(currency.code) || {
          mentions: 0,
          positiveVotes: 0,
          negativeVotes: 0
        }
        current.mentions++
        current.positiveVotes += item.votes.positive
        current.negativeVotes += item.votes.negative
        tokenMentions.set(currency.code, current)
      })
    })

    const relatedTokens = Array.from(tokenMentions.entries())
      .map(([symbol, data]) => ({
        symbol,
        mentions: data.mentions,
        sentiment: data.positiveVotes / (data.positiveVotes + data.negativeVotes || 1)
      }))
      .sort((a, b) => b.mentions - a.mentions)

    // Generate summary
    const summary = this.generateSummary(news, sentiment, confidence)

    // Sort news by importance and recency
    const topStories = [...news].sort((a, b) => {
      const scoreA = a.votes.important * 3 + a.votes.positive - a.votes.negative
      const scoreB = b.votes.important * 3 + b.votes.positive - b.votes.negative
      return scoreB - scoreA
    }).slice(0, 5)

    return {
      sentiment,
      confidence,
      summary,
      topStories,
      relatedTokens
    }
  }

  private generateSummary(news: NewsItem[], sentiment: number, confidence: number): string {
    const totalNews = news.length
    const positiveNews = news.filter(item => item.sentiment === 'positive').length
    const negativeNews = news.filter(item => item.sentiment === 'negative').length
    const importantNews = news.filter(item => item.votes.important > 0).length

    let summary = `Analysis based on ${totalNews} news articles. `

    if (sentiment > 0.7) {
      summary += 'Overall market sentiment is very positive. '
    } else if (sentiment > 0.5) {
      summary += 'Market sentiment is slightly positive. '
    } else if (sentiment < 0.3) {
      summary += 'Overall market sentiment is very negative. '
    } else if (sentiment < 0.5) {
      summary += 'Market sentiment is slightly negative. '
    } else {
      summary += 'Market sentiment is neutral. '
    }

    if (confidence > 0.7) {
      summary += 'Confidence in this analysis is high. '
    } else if (confidence > 0.4) {
      summary += 'Confidence in this analysis is moderate. '
    } else {
      summary += 'Confidence in this analysis is low. '
    }

    if (importantNews > 0) {
      summary += `Found ${importantNews} significant developments. `
    }

    return summary
  }

  async getMarketSentiment(): Promise<{
    overall: number
    trending: Array<{
      symbol: string
      sentiment: number
      newsCount: number
    }>
  }> {
    try {
      const response = await fetch(
        `${this.baseUrl}/stats/?auth_token=${this.apiKey}`,
        {
          headers: {
            'Accept': 'application/json'
          }
        }
      )

      if (!response.ok) {
        throw new Error(`CryptoPanic API error: ${response.statusText}`)
      }

      const data = await response.json()
      return {
        overall: data.market_sentiment || 0.5,
        trending: data.trending_currencies?.map((c: any) => ({
          symbol: c.currency,
          sentiment: c.sentiment,
          newsCount: c.news_count
        })) || []
      }
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to get market sentiment: ${error.message}`)
    }
  }
}
