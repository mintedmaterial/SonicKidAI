import { ErrorResponse } from '../types'

export interface NFTCollection {
  address: string
  name: string
  symbol: string
  totalSupply: number
  floorPrice: number
  volume24h: number
  holders: number
  verified: boolean
  attributes?: {
    [key: string]: string[]
  }
}

export interface NFTItem {
  tokenId: string
  collection: string
  name: string
  description?: string
  image: string
  attributes: {
    trait_type: string
    value: string
  }[]
  lastPrice?: number
  listed?: boolean
  listPrice?: number
}

export interface NFTSale {
  tokenId: string
  collection: string
  price: number
  seller: string
  buyer: string
  timestamp: number
  txHash: string
}

export interface NFTMarketStats {
  totalVolume: number
  volume24h: number
  totalSales: number
  sales24h: number
  averagePrice: number
  floorPrice: number
  highestSale: number
}

export class NFTService {
  private readonly apiKey: string
  private readonly baseUrl = 'https://api.paintswap.finance/v2'
  private readonly cache = new Map<string, {
    data: any
    timestamp: number
  }>()
  private readonly CACHE_DURATION = 5 * 60 * 1000 // 5 minutes

  constructor(apiKey: string) {
    this.apiKey = apiKey
  }

  async getCollection(address: string): Promise<NFTCollection> {
    try {
      const response = await fetch(
        `${this.baseUrl}/collections/${address}`,
        {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Accept': 'application/json'
          }
        }
      )

      if (!response.ok) {
        throw new Error(`PaintSwap API error: ${response.statusText}`)
      }

      const data = await response.json()
      return this.formatCollection(data)
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to fetch collection: ${error.message}`)
    }
  }

  async getCollectionStats(address: string): Promise<NFTMarketStats> {
    try {
      const response = await fetch(
        `${this.baseUrl}/collections/${address}/stats`,
        {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Accept': 'application/json'
          }
        }
      )

      if (!response.ok) {
        throw new Error(`PaintSwap API error: ${response.statusText}`)
      }

      const data = await response.json()
      return {
        totalVolume: data.total_volume,
        volume24h: data.volume_24h,
        totalSales: data.total_sales,
        sales24h: data.sales_24h,
        averagePrice: data.average_price,
        floorPrice: data.floor_price,
        highestSale: data.highest_sale
      }
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to fetch collection stats: ${error.message}`)
    }
  }

  async getRecentSales(collection?: string, limit: number = 20): Promise<NFTSale[]> {
    try {
      const url = collection 
        ? `${this.baseUrl}/collections/${collection}/sales`
        : `${this.baseUrl}/sales`

      const response = await fetch(
        `${url}?limit=${limit}`,
        {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Accept': 'application/json'
          }
        }
      )

      if (!response.ok) {
        throw new Error(`PaintSwap API error: ${response.statusText}`)
      }

      const data = await response.json()
      return data.sales.map(this.formatSale)
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to fetch recent sales: ${error.message}`)
    }
  }

  async getListings(collection: string, limit: number = 20): Promise<NFTItem[]> {
    try {
      const response = await fetch(
        `${this.baseUrl}/collections/${collection}/listings?limit=${limit}`,
        {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Accept': 'application/json'
          }
        }
      )

      if (!response.ok) {
        throw new Error(`PaintSwap API error: ${response.statusText}`)
      }

      const data = await response.json()
      return data.listings.map(this.formatNFTItem)
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to fetch listings: ${error.message}`)
    }
  }

  async analyzeMarket(collection?: string): Promise<{
    trend: 'up' | 'down' | 'stable'
    confidence: number
    summary: string
    recentSales: NFTSale[]
    stats: NFTMarketStats
  }> {
    try {
      const [sales, stats] = await Promise.all([
        this.getRecentSales(collection, 100),
        collection ? this.getCollectionStats(collection) : this.getOverallMarketStats()
      ])

      // Analyze price trend
      const priceTrend = this.analyzePriceTrend(sales)
      
      // Calculate confidence based on sales volume
      const confidence = Math.min(stats.sales24h / 10, 1)

      // Generate summary
      const summary = this.generateMarketSummary(stats, priceTrend, confidence)

      return {
        trend: priceTrend.direction,
        confidence,
        summary,
        recentSales: sales.slice(0, 5), // Return only 5 most recent sales
        stats
      }
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to analyze market: ${error.message}`)
    }
  }

  private async getOverallMarketStats(): Promise<NFTMarketStats> {
    try {
      const response = await fetch(
        `${this.baseUrl}/stats`,
        {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Accept': 'application/json'
          }
        }
      )

      if (!response.ok) {
        throw new Error(`PaintSwap API error: ${response.statusText}`)
      }

      const data = await response.json()
      return {
        totalVolume: data.total_volume,
        volume24h: data.volume_24h,
        totalSales: data.total_sales,
        sales24h: data.sales_24h,
        averagePrice: data.average_price,
        floorPrice: 0, // Not applicable for overall market
        highestSale: data.highest_sale
      }
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to fetch overall market stats: ${error.message}`)
    }
  }

  private analyzePriceTrend(sales: NFTSale[]): {
    direction: 'up' | 'down' | 'stable'
    percentage: number
  } {
    if (sales.length < 2) {
      return { direction: 'stable', percentage: 0 }
    }

    // Sort sales by timestamp
    const sortedSales = [...sales].sort((a, b) => b.timestamp - a.timestamp)

    // Calculate average price for first and second half of the period
    const midPoint = Math.floor(sortedSales.length / 2)
    const recentAvg = sortedSales.slice(0, midPoint).reduce((sum, sale) => sum + sale.price, 0) / midPoint
    const oldAvg = sortedSales.slice(midPoint).reduce((sum, sale) => sum + sale.price, 0) / (sortedSales.length - midPoint)

    const percentageChange = ((recentAvg - oldAvg) / oldAvg) * 100

    if (percentageChange > 5) {
      return { direction: 'up', percentage: percentageChange }
    } else if (percentageChange < -5) {
      return { direction: 'down', percentage: Math.abs(percentageChange) }
    } else {
      return { direction: 'stable', percentage: Math.abs(percentageChange) }
    }
  }

  private generateMarketSummary(
    stats: NFTMarketStats,
    trend: { direction: 'up' | 'down' | 'stable', percentage: number },
    confidence: number
  ): string {
    let summary = `Market Analysis: `

    // Add trend information
    if (trend.direction === 'up') {
      summary += `Prices are trending up ${trend.percentage.toFixed(1)}% `
    } else if (trend.direction === 'down') {
      summary += `Prices are trending down ${trend.percentage.toFixed(1)}% `
    } else {
      summary += `Prices are stable `
    }

    // Add volume information
    summary += `with ${stats.sales24h} sales in the last 24h `
    summary += `totaling ${stats.volume24h.toFixed(2)} SONIC. `

    // Add confidence level
    if (confidence > 0.7) {
      summary += `High confidence in analysis based on strong trading activity.`
    } else if (confidence > 0.4) {
      summary += `Moderate confidence in analysis based on average trading activity.`
    } else {
      summary += `Low confidence in analysis due to limited trading activity.`
    }

    return summary
  }

  private formatCollection(data: any): NFTCollection {
    return {
      address: data.address,
      name: data.name,
      symbol: data.symbol,
      totalSupply: data.total_supply,
      floorPrice: data.floor_price,
      volume24h: data.volume_24h,
      holders: data.holders,
      verified: data.verified,
      attributes: data.attributes
    }
  }

  private formatSale(data: any): NFTSale {
    return {
      tokenId: data.token_id,
      collection: data.collection,
      price: data.price,
      seller: data.seller,
      buyer: data.buyer,
      timestamp: data.timestamp,
      txHash: data.tx_hash
    }
  }

  private formatNFTItem(data: any): NFTItem {
    return {
      tokenId: data.token_id,
      collection: data.collection,
      name: data.name,
      description: data.description,
      image: data.image,
      attributes: data.attributes,
      lastPrice: data.last_price,
      listed: data.listed,
      listPrice: data.list_price
    }
  }
}
