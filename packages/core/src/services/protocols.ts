import { ThirdWebService } from './thirdweb'
import { ServiceConfig, Protocol, LiquidityPool, Trade } from '../types'

interface ProtocolConfig {
  name: string
  type: 'DEX' | 'LENDING' | 'YIELD'
  address: string
  abi: any[]
}

const PROTOCOLS: Record<string, ProtocolConfig> = {
  SHADOW: {
    name: 'Shadow',
    type: 'DEX',
    address: '0x...',  // TODO: Add actual contract addresses
    abi: []  // TODO: Add ABI
  },
  METRO: {
    name: 'Metro',
    type: 'DEX',
    address: '0x...',
    abi: []
  },
  BEETS: {
    name: 'Beets',
    type: 'DEX',
    address: '0x...',
    abi: []
  },
  SWPX: {
    name: 'SwpX',
    type: 'DEX',
    address: '0x...',
    abi: []
  },
  EQUALIZER: {
    name: 'Equalizer',
    type: 'DEX',
    address: '0x...',
    abi: []
  }
}

export class ProtocolService {
  private readonly thirdweb: ThirdWebService
  private readonly activeProtocols: Map<string, Protocol>
  private readonly tradingWallet: string

  constructor(config: ServiceConfig) {
    this.thirdweb = new ThirdWebService(config)
    this.activeProtocols = new Map()
    this.tradingWallet = 'trading' // Default wallet name
  }

  async initialize(): Promise<void> {
    try {
      // Initialize ThirdWeb Engine
      await this.thirdweb.initialize()

      // Add trading wallet
      // TODO: Get private key from secure config
      await this.thirdweb.addWallet(this.tradingWallet, 'private_key')

      // Initialize all protocols
      await Promise.all(
        Object.entries(PROTOCOLS).map(([key, config]) =>
          this.initializeProtocol(key, config)
        )
      )
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to initialize protocol service: ${error.message}`)
    }
  }

  async getLiquidityPools(protocol: string): Promise<LiquidityPool[]> {
    const protocolConfig = PROTOCOLS[protocol]
    if (!protocolConfig) {
      throw new Error(`Unknown protocol: ${protocol}`)
    }

    try {
      const pools = await this.thirdweb.readContract(
        protocol,
        'getAllPools',
        []
      )

      return Promise.all(
        pools.map(async (poolAddress: string) => {
          const [token0, token1, reserves, totalSupply, apr] = await Promise.all([
            this.thirdweb.readContract(protocol, 'getToken0', [poolAddress]),
            this.thirdweb.readContract(protocol, 'getToken1', [poolAddress]),
            this.thirdweb.readContract(protocol, 'getReserves', [poolAddress]),
            this.thirdweb.readContract(protocol, 'totalSupply', [poolAddress]),
            this.thirdweb.readContract(protocol, 'getAPR', [poolAddress])
          ])

          return {
            address: poolAddress,
            token0,
            token1,
            reserve0: reserves[0],
            reserve1: reserves[1],
            totalSupply,
            apr
          }
        })
      )
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to get liquidity pools: ${error.message}`)
    }
  }

  async executeTrade(protocol: string, trade: Trade): Promise<string> {
    const protocolConfig = PROTOCOLS[protocol]
    if (!protocolConfig) {
      throw new Error(`Unknown protocol: ${protocol}`)
    }

    try {
      // Get optimal route for trade
      const route = await this.findOptimalRoute(protocol, trade)

      // Execute trade through protocol router
      const txHash = await this.thirdweb.writeContract(
        protocol,
        trade.type === 'BUY' ? 'swapExactTokensForTokens' : 'swapTokensForExactTokens',
        [
          trade.amount,
          0, // TODO: Calculate minimum amount out
          route,
          this.tradingWallet,
          Math.floor(Date.now() / 1000) + 60 * 20 // 20 minute deadline
        ],
        this.tradingWallet
      )

      // Wait for transaction confirmation
      await this.thirdweb.waitForTransaction(txHash)

      return txHash
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to execute trade: ${error.message}`)
    }
  }

  async getProtocolInfo(protocol: string): Promise<Protocol> {
    const protocolConfig = PROTOCOLS[protocol]
    if (!protocolConfig) {
      throw new Error(`Unknown protocol: ${protocol}`)
    }

    try {
      const [tvl, apr] = await Promise.all([
        this.thirdweb.readContract(protocol, 'getTotalValueLocked', []),
        protocolConfig.type === 'YIELD' 
          ? this.thirdweb.readContract(protocol, 'getAverageAPR', [])
          : Promise.resolve(0)
      ])

      return {
        name: protocolConfig.name,
        address: protocolConfig.address,
        type: protocolConfig.type,
        tvl,
        apr
      }
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to get protocol info: ${error.message}`)
    }
  }

  async calculatePriceImpact(protocol: string, trade: Trade): Promise<number> {
    try {
      const route = await this.findOptimalRoute(protocol, trade)
      const impact = await this.thirdweb.readContract(
        protocol,
        'calculatePriceImpact',
        [trade.amount, route]
      )
      return impact / 10000 // Convert from basis points to percentage
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to calculate price impact: ${error.message}`)
    }
  }

  private async initializeProtocol(key: string, config: ProtocolConfig): Promise<void> {
    try {
      // Add contract to ThirdWeb Engine
      await this.thirdweb.addContract(
        key,
        config.address,
        1 // TODO: Make chainId configurable
      )

      // Get protocol info
      const protocol = await this.getProtocolInfo(key)
      this.activeProtocols.set(key, protocol)
    } catch (err) {
      const error = err as Error
      console.error(`Failed to initialize ${key}: ${error.message}`)
      // Continue with other protocols
    }
  }

  private async findOptimalRoute(
    protocol: string,
    trade: Trade
  ): Promise<string[]> {
    try {
      return await this.thirdweb.readContract(
        protocol,
        'findBestPath',
        [
          trade.amount,
          trade.token,
          'USDC', // TODO: Make quote token configurable
          3 // Max hops
        ]
      )
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to find optimal route: ${error.message}`)
    }
  }
}
