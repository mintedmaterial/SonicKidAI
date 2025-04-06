import { ServiceConfig } from '../types'

export interface TokenData {
  id: string
  symbol: string
  name: string
  decimals: number
  totalSupply: string
  volume: string
  txCount: string
  liquidity: string
  derivedETH: string
}

export interface PairData {
  id: string
  token0: TokenData
  token1: TokenData
  reserve0: string
  reserve1: string
  totalSupply: string
  reserveUSD: string
  volumeUSD: string
  txCount: string
}

export interface SwapData {
  id: string
  timestamp: string
  pair: PairData
  sender: string
  amount0In: string
  amount1In: string
  amount0Out: string
  amount1Out: string
  amountUSD: string
}

export class SubgraphService {
  private readonly endpoint: string
  private readonly cache = new Map<string, {
    data: any
    timestamp: number
  }>()
  private readonly CACHE_DURATION = 5 * 60 * 1000 // 5 minutes

  constructor(config: ServiceConfig) {
    this.endpoint = config.subgraphEndpoint
  }

  async getToken(address: string): Promise<TokenData> {
    const query = `
      query getToken($id: ID!) {
        token(id: $id) {
          id
          symbol
          name
          decimals
          totalSupply
          volume
          txCount
          liquidity
          derivedETH
        }
      }
    `

    const response = await this.querySubgraph(query, { id: address.toLowerCase() })
    return response.token
  }

  async getPair(address: string): Promise<PairData> {
    const query = `
      query getPair($id: ID!) {
        pair(id: $id) {
          id
          token0 {
            id
            symbol
            name
            decimals
            totalSupply
            volume
            txCount
            liquidity
            derivedETH
          }
          token1 {
            id
            symbol
            name
            decimals
            totalSupply
            volume
            txCount
            liquidity
            derivedETH
          }
          reserve0
          reserve1
          totalSupply
          reserveUSD
          volumeUSD
          txCount
        }
      }
    `

    const response = await this.querySubgraph(query, { id: address.toLowerCase() })
    return response.pair
  }

  async getRecentSwaps(
    pair?: string,
    limit: number = 100
  ): Promise<SwapData[]> {
    const query = `
      query getSwaps($first: Int!, $pair: String) {
        swaps(
          first: $first,
          orderBy: timestamp,
          orderDirection: desc,
          where: { pair: $pair }
        ) {
          id
          timestamp
          pair {
            id
            token0 {
              id
              symbol
            }
            token1 {
              id
              symbol
            }
          }
          sender
          amount0In
          amount1In
          amount0Out
          amount1Out
          amountUSD
        }
      }
    `

    const response = await this.querySubgraph(query, {
      first: limit,
      pair: pair?.toLowerCase()
    })
    return response.swaps
  }

  async getTopPairs(
    count: number = 10,
    orderBy: 'volumeUSD' | 'reserveUSD' | 'txCount' = 'volumeUSD'
  ): Promise<PairData[]> {
    const query = `
      query getTopPairs($first: Int!, $orderBy: String!) {
        pairs(
          first: $first,
          orderBy: $orderBy,
          orderDirection: desc
        ) {
          id
          token0 {
            id
            symbol
            name
            decimals
            totalSupply
            volume
            txCount
            liquidity
            derivedETH
          }
          token1 {
            id
            symbol
            name
            decimals
            totalSupply
            volume
            txCount
            liquidity
            derivedETH
          }
          reserve0
          reserve1
          totalSupply
          reserveUSD
          volumeUSD
          txCount
        }
      }
    `

    const response = await this.querySubgraph(query, {
      first: count,
      orderBy
    })
    return response.pairs
  }

  async getTokenDayData(
    tokenAddress: string,
    days: number = 7
  ): Promise<{
    timestamp: number
    volume: string
    liquidity: string
    priceUSD: string
  }[]> {
    const query = `
      query getTokenDayData($token: String!, $first: Int!) {
        tokenDayDatas(
          first: $first,
          orderBy: date,
          orderDirection: desc,
          where: { token: $token }
        ) {
          date
          dailyVolumeUSD
          totalLiquidityUSD
          priceUSD
        }
      }
    `

    const response = await this.querySubgraph(query, {
      token: tokenAddress.toLowerCase(),
      first: days
    })

    return response.tokenDayDatas.map((day: any) => ({
      timestamp: day.date * 1000,
      volume: day.dailyVolumeUSD,
      liquidity: day.totalLiquidityUSD,
      priceUSD: day.priceUSD
    }))
  }

  async getPairDayData(
    pairAddress: string,
    days: number = 7
  ): Promise<{
    timestamp: number
    volume: string
    liquidity: string
    txCount: string
  }[]> {
    const query = `
      query getPairDayData($pair: String!, $first: Int!) {
        pairDayDatas(
          first: $first,
          orderBy: date,
          orderDirection: desc,
          where: { pair: $pair }
        ) {
          date
          dailyVolumeUSD
          reserveUSD
          dailyTxns
        }
      }
    `

    const response = await this.querySubgraph(query, {
      pair: pairAddress.toLowerCase(),
      first: days
    })

    return response.pairDayDatas.map((day: any) => ({
      timestamp: day.date * 1000,
      volume: day.dailyVolumeUSD,
      liquidity: day.reserveUSD,
      txCount: day.dailyTxns
    }))
  }

  async analyzeTokenMetrics(
    tokenAddress: string
  ): Promise<{
    volumeChange24h: number
    liquidityChange24h: number
    priceChange24h: number
    trend: 'up' | 'down' | 'stable'
    confidence: number
  }> {
    const dayData = await this.getTokenDayData(tokenAddress, 2)
    if (dayData.length < 2) {
      throw new Error('Insufficient historical data')
    }

    const [today, yesterday] = dayData
    
    const volumeChange24h = ((parseFloat(today.volume) - parseFloat(yesterday.volume)) / parseFloat(yesterday.volume)) * 100
    const liquidityChange24h = ((parseFloat(today.liquidity) - parseFloat(yesterday.liquidity)) / parseFloat(yesterday.liquidity)) * 100
    const priceChange24h = ((parseFloat(today.priceUSD) - parseFloat(yesterday.priceUSD)) / parseFloat(yesterday.priceUSD)) * 100

    // Determine trend
    const weightedChange = (priceChange24h * 0.5) + (volumeChange24h * 0.3) + (liquidityChange24h * 0.2)
    let trend: 'up' | 'down' | 'stable'
    if (weightedChange > 5) {
      trend = 'up'
    } else if (weightedChange < -5) {
      trend = 'down'
    } else {
      trend = 'stable'
    }

    // Calculate confidence based on volume and liquidity
    const volume = parseFloat(today.volume)
    const liquidity = parseFloat(today.liquidity)
    const confidence = Math.min(
      (volume / 100000) * 0.7 + (liquidity / 1000000) * 0.3,
      1
    )

    return {
      volumeChange24h,
      liquidityChange24h,
      priceChange24h,
      trend,
      confidence
    }
  }

  private async querySubgraph(
    query: string,
    variables: Record<string, any> = {}
  ): Promise<any> {
    const cacheKey = JSON.stringify({ query, variables })
    const cached = this.cache.get(cacheKey)
    if (cached && Date.now() - cached.timestamp < this.CACHE_DURATION) {
      return cached.data
    }

    try {
      const response = await fetch(this.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query,
          variables
        })
      })

      if (!response.ok) {
        throw new Error('Subgraph query failed')
      }

      const json = await response.json()
      if (json.errors) {
        throw new Error(json.errors[0].message)
      }

      this.cache.set(cacheKey, {
        data: json.data,
        timestamp: Date.now()
      })

      return json.data
    } catch (err) {
      const error = err as Error
      throw new Error(`Subgraph query failed: ${error.message}`)
    }
  }
}
