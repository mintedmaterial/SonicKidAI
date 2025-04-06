export interface TVLData {
  tvl: number
  tvlChange24h: number
  tvlChange7d: number
  tokens: {
    symbol: string
    amount: number
    value: number
  }[]
  protocols: {
    name: string
    tvl: number
    dominance: number
  }[]
}

export interface ProtocolTVL {
  name: string
  tvl: number
  tvlChange24h: number
  tvlChange7d: number
  mcap: number
  mcapTvlRatio: number
}

export class TVLService {
  private readonly baseUrl = 'https://api.defillama.com/v2'
  private readonly cache = new Map<string, {
    data: any
    timestamp: number
  }>()
  private readonly CACHE_DURATION = 5 * 60 * 1000 // 5 minutes

  async getChainTVL(chain: string = 'sonic'): Promise<TVLData> {
    const cacheKey = `chain_tvl_${chain}`
    const cached = this.cache.get(cacheKey)
    if (cached && Date.now() - cached.timestamp < this.CACHE_DURATION) {
      return cached.data
    }

    try {
      const [tvlResponse, protocolsResponse] = await Promise.all([
        fetch(`${this.baseUrl}/charts/${chain}`),
        fetch(`${this.baseUrl}/protocols/${chain}`)
      ])

      if (!tvlResponse.ok || !protocolsResponse.ok) {
        throw new Error('DefiLlama API error')
      }

      const tvlData = await tvlResponse.json()
      const protocolsData = await protocolsResponse.json()

      // Get latest TVL data point
      const latest = tvlData[tvlData.length - 1]
      const oneDayAgo = tvlData[tvlData.length - 2]
      const sevenDaysAgo = tvlData[tvlData.length - 8]

      // Calculate changes
      const tvlChange24h = ((latest.totalLiquidityUSD - oneDayAgo.totalLiquidityUSD) / oneDayAgo.totalLiquidityUSD) * 100
      const tvlChange7d = ((latest.totalLiquidityUSD - sevenDaysAgo.totalLiquidityUSD) / sevenDaysAgo.totalLiquidityUSD) * 100

      // Format protocols data
      const totalTVL = latest.totalLiquidityUSD
      const protocols = protocolsData
        .sort((a: any, b: any) => b.tvl - a.tvl)
        .map((p: any) => ({
          name: p.name,
          tvl: p.tvl,
          dominance: (p.tvl / totalTVL) * 100
        }))
        .slice(0, 10) // Top 10 protocols

      const result: TVLData = {
        tvl: totalTVL,
        tvlChange24h,
        tvlChange7d,
        tokens: latest.tokens || [],
        protocols
      }

      // Cache the result
      this.cache.set(cacheKey, {
        data: result,
        timestamp: Date.now()
      })

      return result
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to fetch chain TVL: ${error.message}`)
    }
  }

  async getProtocolTVL(protocol: string): Promise<ProtocolTVL> {
    const cacheKey = `protocol_tvl_${protocol}`
    const cached = this.cache.get(cacheKey)
    if (cached && Date.now() - cached.timestamp < this.CACHE_DURATION) {
      return cached.data
    }

    try {
      const response = await fetch(`${this.baseUrl}/protocol/${protocol}`)
      if (!response.ok) {
        throw new Error('DefiLlama API error')
      }

      const data = await response.json()
      const tvlData = data.tvl
      const latest = tvlData[tvlData.length - 1]
      const oneDayAgo = tvlData[tvlData.length - 2]
      const sevenDaysAgo = tvlData[tvlData.length - 8]

      const result: ProtocolTVL = {
        name: data.name,
        tvl: latest.totalLiquidityUSD,
        tvlChange24h: ((latest.totalLiquidityUSD - oneDayAgo.totalLiquidityUSD) / oneDayAgo.totalLiquidityUSD) * 100,
        tvlChange7d: ((latest.totalLiquidityUSD - sevenDaysAgo.totalLiquidityUSD) / sevenDaysAgo.totalLiquidityUSD) * 100,
        mcap: data.mcap || 0,
        mcapTvlRatio: data.mcap ? data.mcap / latest.totalLiquidityUSD : 0
      }

      // Cache the result
      this.cache.set(cacheKey, {
        data: result,
        timestamp: Date.now()
      })

      return result
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to fetch protocol TVL: ${error.message}`)
    }
  }

  async getTopProtocolsByTVL(chain: string = 'sonic', limit: number = 10): Promise<ProtocolTVL[]> {
    try {
      const response = await fetch(`${this.baseUrl}/protocols/${chain}`)
      if (!response.ok) {
        throw new Error('DefiLlama API error')
      }

      const data = await response.json()
      return data
        .sort((a: any, b: any) => b.tvl - a.tvl)
        .slice(0, limit)
        .map((p: any) => ({
          name: p.name,
          tvl: p.tvl,
          tvlChange24h: p.change_1d || 0,
          tvlChange7d: p.change_7d || 0,
          mcap: p.mcap || 0,
          mcapTvlRatio: p.mcap ? p.mcap / p.tvl : 0
        }))
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to fetch top protocols: ${error.message}`)
    }
  }

  async analyzeTVLTrends(chain: string = 'sonic'): Promise<{
    trend: 'growing' | 'declining' | 'stable'
    confidence: number
    summary: string
    topGainers: ProtocolTVL[]
    topLosers: ProtocolTVL[]
  }> {
    try {
      const [chainData, protocols] = await Promise.all([
        this.getChainTVL(chain),
        this.getTopProtocolsByTVL(chain, 20)
      ])

      // Analyze overall trend
      const trend = this.analyzeTrend(chainData.tvlChange24h, chainData.tvlChange7d)
      
      // Sort protocols by 24h change
      const sortedByChange = [...protocols].sort((a, b) => b.tvlChange24h - a.tvlChange24h)
      const topGainers = sortedByChange.slice(0, 5)
      const topLosers = sortedByChange.reverse().slice(0, 5)

      // Calculate confidence based on data consistency
      const confidence = this.calculateConfidence(protocols)

      // Generate summary
      const summary = this.generateTVLSummary(chainData, trend, confidence)

      return {
        trend: trend.direction,
        confidence,
        summary,
        topGainers,
        topLosers
      }
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to analyze TVL trends: ${error.message}`)
    }
  }

  private analyzeTrend(change24h: number, change7d: number): {
    direction: 'growing' | 'declining' | 'stable'
    strength: 'strong' | 'moderate' | 'weak'
  } {
    // Weight recent changes more heavily
    const weightedChange = (change24h * 0.7) + (change7d * 0.3)

    let direction: 'growing' | 'declining' | 'stable'
    let strength: 'strong' | 'moderate' | 'weak'

    if (weightedChange > 5) {
      direction = 'growing'
      strength = weightedChange > 20 ? 'strong' : weightedChange > 10 ? 'moderate' : 'weak'
    } else if (weightedChange < -5) {
      direction = 'declining'
      strength = weightedChange < -20 ? 'strong' : weightedChange < -10 ? 'moderate' : 'weak'
    } else {
      direction = 'stable'
      strength = 'moderate'
    }

    return { direction, strength }
  }

  private calculateConfidence(protocols: ProtocolTVL[]): number {
    // Calculate confidence based on:
    // 1. Number of protocols with consistent data
    // 2. Total TVL coverage
    // 3. Data freshness (handled by cache)

    const totalProtocols = protocols.length
    const protocolsWithConsistentData = protocols.filter(p => 
      !isNaN(p.tvl) && !isNaN(p.tvlChange24h) && !isNaN(p.tvlChange7d)
    ).length

    const dataCompleteness = protocolsWithConsistentData / totalProtocols
    return Math.min(dataCompleteness, 1)
  }

  private generateTVLSummary(
    chainData: TVLData,
    trend: { direction: 'growing' | 'declining' | 'stable', strength: 'strong' | 'moderate' | 'weak' },
    confidence: number
  ): string {
    let summary = `TVL Analysis: `

    // Add trend information
    if (trend.direction === 'growing') {
      summary += `TVL is ${trend.strength}ly growing `
    } else if (trend.direction === 'declining') {
      summary += `TVL is ${trend.strength}ly declining `
    } else {
      summary += `TVL is stable `
    }

    // Add current TVL and changes
    summary += `at $${chainData.tvl.toFixed(2)}M `
    summary += `(24h: ${chainData.tvlChange24h.toFixed(1)}%, 7d: ${chainData.tvlChange7d.toFixed(1)}%). `

    // Add protocol dominance
    const topProtocol = chainData.protocols[0]
    if (topProtocol) {
      summary += `${topProtocol.name} leads with ${topProtocol.dominance.toFixed(1)}% dominance. `
    }

    // Add confidence level
    if (confidence > 0.8) {
      summary += `High confidence in analysis.`
    } else if (confidence > 0.5) {
      summary += `Moderate confidence in analysis.`
    } else {
      summary += `Low confidence in analysis due to limited data.`
    }

    return summary
  }
}
