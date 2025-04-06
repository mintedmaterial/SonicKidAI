import { 
  Protocol, 
  LiquidityPool, 
  StrategyAnalysis,
  DefiProvider 
} from '../types'

export class DefiService {
  private providers: DefiProvider[] = []

  constructor(providers: DefiProvider[] = []) {
    this.providers = providers
  }

  addProvider(provider: DefiProvider) {
    this.providers.push(provider)
  }

  async getLiquidity(token: string): Promise<number> {
    const liquidities = await Promise.all(
      this.providers.map(async (provider) => {
        try {
          return await provider.getLiquidity(token)
        } catch (error) {
          console.error('Failed to get liquidity from provider:', error)
          return 0
        }
      })
    )

    return liquidities.reduce((total, current) => total + current, 0)
  }

  async getYield(token: string): Promise<number> {
    const yields = await Promise.all(
      this.providers.map(async (provider) => {
        try {
          return await provider.getYield(token)
        } catch (error) {
          console.error('Failed to get yield from provider:', error)
          return 0
        }
      })
    )

    // Return the highest yield available
    return Math.max(...yields, 0)
  }

  async getPoolInfo(token: string): Promise<LiquidityPool[]> {
    const poolInfos = await Promise.all(
      this.providers.map(async (provider) => {
        try {
          const info = await provider.getPoolInfo(token)
          return Array.isArray(info) ? info : [info]
        } catch (error) {
          console.error('Failed to get pool info from provider:', error)
          return []
        }
      })
    )

    return poolInfos.flat()
  }

  async analyzeStrategy(token: string): Promise<StrategyAnalysis> {
    const [liquidity, yield_, pools] = await Promise.all([
      this.getLiquidity(token),
      this.getYield(token),
      this.getPoolInfo(token)
    ])

    // Find the best pool based on liquidity and yield
    const bestPool = pools.reduce((best, current) => {
      const score = current.apr * 0.7 + (current.totalSupply / 1e6) * 0.3
      const bestScore = best ? best.apr * 0.7 + (best.totalSupply / 1e6) * 0.3 : 0
      return score > bestScore ? current : best
    }, pools[0])

    if (!bestPool) {
      throw new Error('No valid pools found')
    }

    const protocol: Protocol = {
      name: 'SonicDex', // TODO: Make this dynamic
      address: bestPool.address,
      type: 'DEX',
      tvl: liquidity,
      apr: yield_
    }

    const risk = this.calculateRisk(liquidity, yield_, bestPool)

    return {
      protocol,
      pool: bestPool,
      expectedReturn: yield_,
      risk,
      recommendation: this.generateRecommendation(risk, yield_)
    }
  }

  private calculateRisk(liquidity: number, yield_: number, pool: LiquidityPool): 'LOW' | 'MEDIUM' | 'HIGH' {
    // Basic risk calculation based on liquidity and yield
    if (liquidity < 100000 || yield_ > 100) {
      return 'HIGH'
    }
    if (liquidity < 1000000 || yield_ > 50) {
      return 'MEDIUM'
    }
    return 'LOW'
  }

  private generateRecommendation(risk: 'LOW' | 'MEDIUM' | 'HIGH', yield_: number): string {
    switch (risk) {
      case 'LOW':
        return `Safe investment opportunity with ${yield_}% APR`
      case 'MEDIUM':
        return `Moderate risk investment with ${yield_}% APR - Diversify position`
      case 'HIGH':
        return `High risk investment with ${yield_}% APR - Proceed with caution`
    }
  }
}
