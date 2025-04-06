import { ServiceConfig } from '../types'

export interface SmartWalletConfig {
  chain: number
  sponsorGas?: boolean
}

export interface InAppWalletConfig {
  auth?: {
    mode?: 'popup' | 'redirect'
    options?: string[]
  }
  smartAccount?: SmartWalletConfig
}

interface ContractMetadata {
  name: string
  symbol: string
  address: string
  abi: any[]
}

interface WalletConfig {
  address: string
  privateKey: string
}

export interface TransactionConfig {
  gasLimit?: number
  maxFeePerGas?: number
  maxPriorityFeePerGas?: number
  nonce?: number
}

export interface ContractWriteConfig extends TransactionConfig {
  value?: string | number
}

export class ThirdWebService {
  private readonly apiKey: string
  private readonly secretKey: string
  private readonly baseUrl: string
  private readonly contracts: Map<string, ContractMetadata>
  private readonly wallets: Map<string, WalletConfig>
  private readonly nftContract: string = '0x45bC8A938E487FdE4F31A7E051c2b63627F6f966'

  constructor(config: ServiceConfig) {
    this.apiKey = config.thirdwebApiKey
    this.secretKey = config.thirdwebSecretKey
    this.baseUrl = 'http://localhost:3005' // Local ThirdWeb Engine
    this.contracts = new Map()
    this.wallets = new Map()
  }

  async initialize(): Promise<void> {
    try {
      // Test connection to ThirdWeb Engine
      const response = await fetch(this.baseUrl, {
        headers: this.getHeaders()
      })

      if (!response.ok) {
        throw new Error('ThirdWeb Engine not running')
      }
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to initialize ThirdWeb service: ${error.message}`)
    }
  }

  async addContract(
    name: string,
    address: string,
    chainId: number
  ): Promise<ContractMetadata> {
    try {
      const response = await fetch(`${this.baseUrl}/contract`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({
          chain: chainId,
          address,
          name
        })
      })

      if (!response.ok) {
        throw new Error('Failed to add contract')
      }

      const contract = await response.json()
      this.contracts.set(name, contract)
      return contract
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to add contract: ${error.message}`)
    }
  }

  async addWallet(name: string, privateKey: string): Promise<string> {
    try {
      const response = await fetch(`${this.baseUrl}/wallet`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({
          privateKey
        })
      })

      if (!response.ok) {
        throw new Error('Failed to add wallet')
      }

      const { address } = await response.json()
      this.wallets.set(name, { address, privateKey })
      return address
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to add wallet: ${error.message}`)
    }
  }

  async readContract(
    contractName: string,
    functionName: string,
    args: any[] = []
  ): Promise<any> {
    const contract = this.contracts.get(contractName)
    if (!contract) {
      throw new Error(`Contract ${contractName} not found`)
    }

    try {
      const response = await fetch(`${this.baseUrl}/contract/read`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({
          contract: contract.address,
          functionName,
          args
        })
      })

      if (!response.ok) {
        throw new Error('Contract read failed')
      }

      return response.json()
    } catch (err) {
      const error = err as Error
      throw new Error(`Contract read failed: ${error.message}`)
    }
  }

  async writeContract(
    contractName: string,
    functionName: string,
    args: any[] = [],
    wallet: string,
    config: ContractWriteConfig = {}
  ): Promise<string> {
    const contract = this.contracts.get(contractName)
    if (!contract) {
      throw new Error(`Contract ${contractName} not found`)
    }

    const walletConfig = this.wallets.get(wallet)
    if (!walletConfig) {
      throw new Error(`Wallet ${wallet} not found`)
    }

    try {
      const response = await fetch(`${this.baseUrl}/contract/write`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({
          contract: contract.address,
          functionName,
          args,
          wallet: walletConfig.address,
          ...config
        })
      })

      if (!response.ok) {
        throw new Error('Contract write failed')
      }

      const { hash } = await response.json()
      return hash
    } catch (err) {
      const error = err as Error
      throw new Error(`Contract write failed: ${error.message}`)
    }
  }

  async deployContract(
    name: string,
    abi: any[],
    bytecode: string,
    wallet: string,
    args: any[] = []
  ): Promise<string> {
    const walletConfig = this.wallets.get(wallet)
    if (!walletConfig) {
      throw new Error(`Wallet ${wallet} not found`)
    }

    try {
      const response = await fetch(`${this.baseUrl}/contract/deploy`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({
          abi,
          bytecode,
          wallet: walletConfig.address,
          args
        })
      })

      if (!response.ok) {
        throw new Error('Contract deployment failed')
      }

      const { address } = await response.json()
      
      // Add deployed contract to our registry
      await this.addContract(name, address, 1) // TODO: Make chainId configurable
      
      return address
    } catch (err) {
      const error = err as Error
      throw new Error(`Contract deployment failed: ${error.message}`)
    }
  }

  async getTransaction(hash: string): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/transaction/${hash}`, {
        headers: this.getHeaders()
      })

      if (!response.ok) {
        throw new Error('Failed to get transaction')
      }

      return response.json()
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to get transaction: ${error.message}`)
    }
  }

  async waitForTransaction(hash: string, confirmations: number = 1): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/transaction/${hash}/wait`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ confirmations })
      })

      if (!response.ok) {
        throw new Error('Transaction wait failed')
      }
    } catch (err) {
      const error = err as Error
      throw new Error(`Transaction wait failed: ${error.message}`)
    }
  }

  private getHeaders(): HeadersInit {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.secretKey}`
    }
  }

  // Smart Account Methods
  async createSmartAccount(config: SmartWalletConfig): Promise<string> {
    try {
      const response = await fetch(`${this.baseUrl}/wallet/smart`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({
          chain: config.chain,
          sponsorGas: config.sponsorGas
        })
      })

      if (!response.ok) {
        throw new Error('Failed to create smart account')
      }

      const { address } = await response.json()
      return address
    } catch (error) {
      console.error('Smart account creation failed:', error)
      throw error
    }
  }

  // In-App Wallet Methods
  async createInAppWallet(config: InAppWalletConfig): Promise<string> {
    try {
      const response = await fetch(`${this.baseUrl}/wallet/in-app`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(config)
      })

      if (!response.ok) {
        throw new Error('Failed to create in-app wallet')
      }

      const { address } = await response.json()
      return address
    } catch (error) {
      console.error('In-app wallet creation failed:', error)
      throw error
    }
  }

  // NFT Contract Methods
  async getNFTBalance(address: string): Promise<number> {
    try {
      const response = await fetch(`${this.baseUrl}/contract/${this.nftContract}/balanceOf`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({
          args: [address]
        })
      })

      if (!response.ok) {
        throw new Error('Failed to get NFT balance')
      }

      const { result } = await response.json()
      return Number(result)
    } catch (error) {
      console.error('Get NFT balance failed:', error)
      throw error
    }
  }

  async mintNFT(to: string, metadata: {
    name: string
    description: string
    image: string
    attributes?: { trait_type: string; value: string }[]
  }): Promise<string> {
    try {
      const response = await fetch(`${this.baseUrl}/contract/${this.nftContract}/mint`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({
          args: [to, metadata]
        })
      })

      if (!response.ok) {
        throw new Error('Failed to mint NFT')
      }

      const { transactionHash } = await response.json()
      return transactionHash
    } catch (error) {
      console.error('NFT minting failed:', error)
      throw error
    }
  }
}
