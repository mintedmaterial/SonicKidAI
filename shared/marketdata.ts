import { ethers } from 'ethers';

interface TokenPrice {
  price: number | string;
  timestamp: number;
  source: string;
}

interface TokenData {
  address: string;
  symbol: string;
  name: string;
  decimals: number;
  nativeAddress?: string; // Native token address
  sonicAddress?: string; // Legacy Native Sonic token address
  wrappedAddress?: string; // Wrapped Sonic token address (wS)
  prices?: TokenPrice[];
  priceUsd?: number;  // Direct price in USD for easier access
  volume24h?: number | string;
  volumeChange24h?: number | string; // 24h volume change percentage
  liquidity?: number | string | { usd: number | string; base: number | string; quote: number | string };
  priceChange24h?: number | string;
  tvl?: number;
  tvlChange24h?: number;
  chain?: string;
  source?: string; // Source of the data (e.g., 'sonic_labs', 'dexscreener', 'fallback')
}

export interface DexPairToken {
  address: string;
  name: string;
  symbol: string;
}

export interface DexScreenerPair {
  pairAddress: string;
  baseToken: DexPairToken;
  quoteToken: DexPairToken;
  priceUsd: string | number;
  txCount?: number;
  volume?: number | string;
  priceChange?: number | string;
  liquidity?: number | string;
  fdv?: number | string;
  marketCap?: number | string;
}

interface ChainMapping {
  id: string;
  prefix: string;
  name: string;
}

const CHAIN_MAPPINGS: { [key: string]: ChainMapping } = {
  'sonic': { id: '146', prefix: '$S', name: 'Sonic' },
  'eth': { id: '1', prefix: '$eth', name: 'Ethereum' },
  'arb': { id: '42161', prefix: '$arb', name: 'Arbitrum' },
  'op': { id: '10', prefix: '$op', name: 'Optimism' }
};

export class MarketDataService {
  private dexscreenerApi: string;
  private memeApi: string;
  private defillamaApi: string;
  private alchemyApi: string;
  private alchemyUrl: string;
  private websocketUrl: string;
  private sonicRpcUrl: string;

  constructor() {
    this.dexscreenerApi = process.env.DEXSCREENER_API || "https://api.dexscreener.com/latest/dex";
    this.memeApi = process.env.MEME_API || "https://meme-api.openocean.finance";
    this.defillamaApi = process.env.DEFILLAMA_API || "https://api.llama.fi";
    this.alchemyApi = process.env.ALCHEMY_PRICES_API || "https://api.g.alchemy.com/prices/v1";
    this.alchemyUrl = `https://sonic-mainnet.g.alchemy.com/v2/${process.env.ALCHEMY_API_KEY}`;
    this.websocketUrl = process.env.WEBSOCKET_URL || "wss://meme-api.openocean.finance/ws/public";
    this.sonicRpcUrl = `https://sonic-mainnet.g.alchemy.com/v2/${process.env.SONIC_LABS_API_KEY}`;

    if (!process.env.ALCHEMY_API_KEY) {
      console.warn('ALCHEMY_API_KEY not set - Alchemy features will be disabled');
    }
    if (!process.env.SONIC_LABS_API_KEY) {
      console.warn('SONIC_LABS_API_KEY not set - Sonic features may be limited');
    }
  }

  /**
   * Get SONIC price prioritizing SonicScan.org API and only using database as fallback
   * @returns Price data object with timestamp
   */
  private async getSonicPrice(): Promise<TokenPrice | null> {
    try {
      // First try to get price from SonicScan.org API (more accurate)
      const apiResponse = await fetch(`https://api.sonicscan.org/api?module=stats&action=ethprice&apikey=${process.env.SONIC_LABS_API_KEY}`);
      
      if (apiResponse.ok) {
        const data = await apiResponse.json();
        if (data && data.result && data.result.ethusd) {
          const price = parseFloat(data.result.ethusd);
          console.log(`✅ Retrieved SONIC price from SonicScan.org API: $${price}`);
          return {
            price: price,
            timestamp: Date.now(),
            source: 'sonic_labs'
          };
        }
      }
      
      // Fallback to database price if API fails
      console.log('⚠️ SonicScan.org API call failed, falling back to database price');
      const dbPrice = await this.getSonicPriceFromDatabase();
      if (dbPrice) {
        // Check if the database price is recent (less than 1 hour old)
        const priceAge = Date.now() - dbPrice.timestamp;
        const isRecent = priceAge < 3600000; // 1 hour in milliseconds
        
        if (isRecent && parseFloat(String(dbPrice.price)) > 0.3) { // Validate price is within expected range (>$0.30)
          console.log(`✅ Retrieved SONIC price from database: $${dbPrice.price}`);
          return dbPrice;
        } else {
          console.log(`⚠️ Database price rejected: ${isRecent ? 'price too low' : 'too old'}`);
        }
      }
      
      // If we get here, try SonicScan.org API one more time (in case the first attempt failed)
      console.log('Retrying SonicScan.org API...');
      const retryResponse = await fetch(`https://api.sonicscan.org/api?module=stats&action=ethprice&apikey=${process.env.SONIC_LABS_API_KEY}`);

      if (retryResponse.ok) {
        const data = await retryResponse.json();
        if (data.result && data.result.ethusd) {
          return {
            price: parseFloat(data.result.ethusd),
            timestamp: Date.now(),
            source: 'sonic_labs'
          };
        }
      }

      return null;
    } catch (error) {
      console.error('Error fetching Sonic price from Sonic Labs:', error);
      return null;
    }
  }
  
  /**
   * Get latest SONIC price from the database
   * @returns Price data object with timestamp
   */
  private async getSonicPriceFromDatabase(): Promise<TokenPrice | null> {
    try {
      console.log('Attempting to fetch SONIC price from database...');
      
      // Use the database utility for consistent database access
      const { getLatestSonicPrice } = await import('./database');
      
      try {
        // Get the latest SONIC price from the database
        const priceData = await getLatestSonicPrice();
        
        if (priceData) {
          console.log(`✅ Found SONIC price in database: $${priceData.price} (source: ${priceData.source})`);
          return {
            price: priceData.price,
            timestamp: priceData.timestamp,
            source: priceData.source
          };
        }
        
        console.log('⚠️ No SONIC price found in database, falling back to SonicScan.org API');
        return null;
      } catch (innerError) {
        console.error('Error in database query execution:', innerError);
        return null;
      }
    } catch (error) {
      console.error('Error fetching SONIC price from database:', error);
      return null;
    }
  }
  
  /**
   * Get Sonic TVL data from DefiLlama
   * @returns TVL data object with current value and change percentage
   */
  private async getSonicTVL(): Promise<{tvl: number, tvlChange24h: number} | null> {
    try {
      console.log('Fetching Sonic TVL data from DefiLlama...');
      
      // Get current TVL from DefiLlama API - use the /protocol endpoint instead
      // Sonic chain ID in DefiLlama is 'fantom' since it was rebranded
      const response = await fetch('https://api.llama.fi/v2/chains');
      
      if (!response.ok) {
        throw new Error(`DefiLlama API error: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (!data || !Array.isArray(data)) {
        throw new Error('Invalid response format from DefiLlama');
      }
      
      // Find Sonic (formerly Fantom) in the chains list
      const sonicData = data.find((chain: any) => 
        chain.name === 'Fantom' || 
        chain.name === 'Sonic' || 
        chain.chainId === 'fantom'
      );
      
      if (!sonicData) {
        console.warn('Sonic chain not found in DefiLlama data, using fallback values');
        return {
          tvl: 65000000, // $65M TVL based on latest data
          tvlChange24h: 0.5  // 0.5% 24h change
        };
      }
      
      // Current TVL
      const currentTVL = sonicData.tvl || 65000000;
      
      // Get TVL change percentage
      let tvlChange24h = 0;
      
      // If there's change data, calculate percentage
      if (sonicData.change_1d !== undefined) {
        tvlChange24h = sonicData.change_1d;
      }
      
      console.log(`✅ DefiLlama Sonic TVL: $${currentTVL.toLocaleString()} (${tvlChange24h.toFixed(2)}% 24h change)`);
      
      return {
        tvl: currentTVL,
        tvlChange24h: tvlChange24h
      };
    } catch (error) {
      console.error('Error fetching Sonic TVL from DefiLlama:', error);
      // Return fallback values if fetch fails
      return {
        tvl: 65000000, // $65M TVL based on latest data
        tvlChange24h: 0.5  // 0.5% 24h change
      };
    }
  }
  
  /**
   * Get Sonic DEX 24h volume data from DefiLlama
   * @returns Total 24h volume for Sonic DEXes
   */
  async getSonicDexVolume(): Promise<{volume24h: number, volumeChange24h: number}> {
    try {
      console.log('Fetching Sonic DEX volume data from DefiLlama...');
      
      // Use the overview/dexs endpoint with Sonic filter to get DEX volume data
      const response = await fetch('https://api.llama.fi/overview/dexs/Sonic?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true&dataType=dailyVolume');
      
      if (!response.ok) {
        throw new Error(`DefiLlama DEX API error: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (!data) {
        throw new Error('Invalid response format from DefiLlama DEX API');
      }
      
      // Extract the total volume and volume change
      const totalVolume = data.total24h || 0;
      const volumeChange = data.change_1d || 0;
      
      console.log(`✅ DefiLlama Sonic DEX 24h Volume: $${totalVolume.toLocaleString()} (${volumeChange.toFixed(2)}% 24h change)`);
      
      return {
        volume24h: totalVolume,
        volumeChange24h: volumeChange
      };
    } catch (error) {
      console.error('Error fetching Sonic DEX volume from DefiLlama:', error);
      
      // Return zeros in case of errors
      return {
        volume24h: 0,
        volumeChange24h: 0
      };
    }
  }
  
  /**
   * Get Fear and Greed Index data from Alternative.me API
   * @param limit Number of days of data to retrieve
   * @returns Fear and Greed Index data
   */
  async getFearGreedIndex(limit: number = 30): Promise<any> {
    try {
      console.log('Fetching Fear and Greed Index data...');
      
      // Call the Fear and Greed Index API
      const response = await fetch(`https://api.alternative.me/fng/?limit=${limit}&format=json`);
      
      if (!response.ok) {
        throw new Error(`Fear and Greed API error: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (!data || !data.data) {
        throw new Error('Invalid response format from Fear and Greed API');
      }
      
      console.log(`✅ Successfully fetched Fear and Greed data with ${data.data.length} entries`);
      
      return data;
    } catch (error) {
      console.error('Error fetching Fear and Greed data:', error);
      throw error;
    }
  }

  private getChainByPrefix(prefix: string): ChainMapping | null {
    const chain = Object.values(CHAIN_MAPPINGS).find(c => c.prefix.toLowerCase() === prefix.toLowerCase());
    return chain || null;
  }

  private getChainById(chainId: string): ChainMapping | null {
    const chain = Object.values(CHAIN_MAPPINGS).find(c => c.id === chainId);
    return chain || null;
  }

  async getDexScreenerPairs(chainId: string, pairId?: string): Promise<TokenPrice | null> {
    try {
      const chain = this.getChainById(chainId);
      if (!chain) {
        console.warn(`Unsupported chain ID: ${chainId}`);
        return null;
      }

      const endpoint = pairId 
        ? `${this.dexscreenerApi}/pairs/${chainId}/${pairId}`
        : `${this.dexscreenerApi}/pairs/${chainId}`;

      const response = await fetch(endpoint);
      if (response.ok) {
        const data = await response.json();
        if (data.pairs && data.pairs.length > 0) {
          return {
            price: parseFloat(data.pairs[0].priceUsd),
            timestamp: Date.now(),
            source: 'dexscreener'
          };
        }
      }
      return null;
    } catch (error) {
      console.error('DexScreener pairs fetch error:', error);
      return null;
    }
  }

  /**
   * Get Trading Pairs on Sonic Chain from DexScreener
   * Returns array of trading pairs sorted by liquidity
   */
  async getSonicPairs(limit: number = 20): Promise<any[]> {
    try {
      // Try the more specific Sonic/USDC search first as suggested
      console.log('Searching for Sonic/USDC pairs specifically');
      
      const endpoint = `${this.dexscreenerApi}/search?q=Sonic%2FUSDC`;
      console.log(`Fetching Sonic pairs from: ${endpoint}`);
      
      const response = await fetch(endpoint);
      if (!response.ok) {
        throw new Error(`DexScreener API returned ${response.status}`);
      }
      
      const data = await response.json();
      
      if (!data.pairs || !Array.isArray(data.pairs)) {
        console.warn('No pairs found or invalid response format');
        return [];
      }
      
      console.log(`Found ${data.pairs.length} total pairs for Sonic/USDC search`);
      
      // Filter for Sonic network pairs if chainId is specified in the pair data
      // IMPORTANT: We must strictly filter for Sonic chain first (146 or 'sonic')
      // to avoid confusing with Solana chain tokens that have "SONIC" in their name
      const sonicPairs = data.pairs.filter((pair: any) => {
        // STRICT CHECK: Only include pairs on Sonic chain
        const isSonicChain = pair.chainId === '146' || pair.chainId?.toLowerCase() === 'sonic';
        
        // If not on Sonic chain, exclude the pair
        if (!isSonicChain) {
          return false;
        }
        
        // Now for pairs that are definitely on Sonic chain, we can further filter:
        
        // Check if it's a DEX on Sonic 
        const isSonicDex = pair.dexId?.toLowerCase().includes('sonic');
        
        // Check for SONIC token as base or quote
        const hasSonicToken = 
          pair.baseToken?.symbol?.toUpperCase().includes('SONIC') || 
          pair.quoteToken?.symbol?.toUpperCase().includes('SONIC');
        
        // Check for USDC token as base or quote
        const hasUsdcToken = 
          pair.baseToken?.symbol?.toUpperCase().includes('USDC') || 
          pair.quoteToken?.symbol?.toUpperCase().includes('USDC');
        
        // At least one of these conditions must be true (all pairs are guaranteed to be on Sonic chain)
        return isSonicDex || hasSonicToken || hasUsdcToken;
      });
      
      console.log(`Found ${sonicPairs.length} Sonic network pairs after filtering`);
      
      // If we didn't find any pairs with the specific search, fallback to broader search
      if (sonicPairs.length === 0) {
        console.log('No specific Sonic/USDC pairs found, trying broader SONIC search');
        
        // Fallback to general SONIC search
        const fallbackEndpoint = `${this.dexscreenerApi}/search?q=SONIC`;
        console.log(`Fetching fallback Sonic pairs from: ${fallbackEndpoint}`);
        
        const fallbackResponse = await fetch(fallbackEndpoint);
        if (!fallbackResponse.ok) {
          throw new Error(`DexScreener API returned ${fallbackResponse.status}`);
        }
        
        const fallbackData = await fallbackResponse.json();
        
        if (!fallbackData.pairs || !Array.isArray(fallbackData.pairs)) {
          console.warn('No pairs found in fallback search');
          return [];
        }
        
        console.log(`Found ${fallbackData.pairs.length} total pairs in fallback SONIC search`);
        
        // Apply the improved chain-first filter logic to the fallback data
        const fallbackSonicPairs = fallbackData.pairs.filter((pair: any) => {
          // STRICT CHECK: Only include pairs on Sonic chain
          const isSonicChain = pair.chainId === '146' || pair.chainId?.toLowerCase() === 'sonic';
          
          // If not on Sonic chain, exclude the pair 
          if (!isSonicChain) {
            return false;
          }
          
          // For pairs on Sonic chain, we can further refine the search:
          const isSonicDex = pair.dexId?.toLowerCase().includes('sonic');
          const hasSonicToken = 
            pair.baseToken?.symbol?.toUpperCase().includes('SONIC') || 
            pair.quoteToken?.symbol?.toUpperCase().includes('SONIC');
          
          // At least one of these should match (all pairs are on Sonic chain)
          return isSonicDex || hasSonicToken;
        });
        
        console.log(`Found ${fallbackSonicPairs.length} pairs in fallback search after filtering`);
        
        // Process fallback pairs the same way
        return this.processPairs(fallbackSonicPairs, limit);
      }
      
      // Process and return the pairs from the specific search
      return this.processPairs(sonicPairs, limit);
    } catch (error) {
      console.error('Error fetching Sonic pairs:', error);
      return [];
    }
  }
  
  /**
   * Process and format DexScreener pairs data
   */
  private processPairs(pairs: any[], limit: number): any[] {
    return pairs
      .filter((pair: any) => 
        pair.liquidity && 
        (pair.liquidity.usd || pair.liquidity > 0) && 
        parseFloat(pair.liquidity.usd || pair.liquidity) > 0
      )
      .sort((a: any, b: any) => {
        const liquidityA = parseFloat(a.liquidity?.usd || a.liquidity || '0');
        const liquidityB = parseFloat(b.liquidity?.usd || b.liquidity || '0');
        return liquidityB - liquidityA;
      })
      .slice(0, limit)
      .map((pair: any) => ({
        pairAddress: pair.pairAddress,
        baseToken: {
          address: pair.baseToken?.address,
          name: pair.baseToken?.name,
          symbol: pair.baseToken?.symbol
        },
        quoteToken: {
          address: pair.quoteToken?.address,
          name: pair.quoteToken?.name,
          symbol: pair.quoteToken?.symbol
        },
        liquidity: parseFloat(pair.liquidity?.usd || pair.liquidity || '0'),
        volume24h: parseFloat(pair.volume?.h24 || '0'),
        priceUsd: parseFloat(pair.priceUsd || '0'),
        priceChange24h: parseFloat(pair.priceChange?.h24 || '0'),
        txns24h: {
          buys: parseInt(pair.txns?.h24?.buys || '0'),
          sells: parseInt(pair.txns?.h24?.sells || '0')
        },
        dexId: pair.dexId,
        chainId: pair.chainId
      }));
  }

  private async getMemeApiPrice(tokenAddress: string): Promise<TokenPrice | null> {
    try {
      const response = await fetch(`${this.memeApi}/token?address=${tokenAddress}`);
      if (response.ok) {
        const data = await response.json();
        if (data.price) {
          return {
            price: parseFloat(data.price),
            timestamp: Date.now(),
            source: 'meme_api'
          };
        }
      }
      return null;
    } catch (error) {
      console.error('Meme API fetch error:', error);
      return null;
    }
  }

  private async getAlchemyPrice(tokenAddress: string): Promise<TokenPrice | null> {
    if (!process.env.ALCHEMY_API_KEY) return null;

    try {
      const response = await fetch(`${this.alchemyApi}/${process.env.ALCHEMY_API_KEY}/tokens/by-address?addresses=${tokenAddress}`);
      if (response.ok) {
        const data = await response.json();
        if (data.data?.[0]?.prices?.[0]) {
          return {
            price: parseFloat(data.data[0].prices[0].value),
            timestamp: Date.now(),
            source: 'alchemy'
          };
        }
      }
      return null;
    } catch (error) {
      console.error('Alchemy fetch error:', error);
      return null;
    }
  }

  async getTokenPrice(tokenAddress: string, chainId: string = "sonic"): Promise<TokenPrice | null> {
    try {
      // For Sonic token, try Sonic Labs API first
      if (chainId === "sonic") {
        const sonicPrice = await this.getSonicPrice();
        if (sonicPrice) {
          return sonicPrice;
        }
      }

      // For other tokens, try APIs in order of reliability
      const prices = await Promise.all([
        this.getDexScreenerPairs(chainId), 
        this.getMemeApiPrice(tokenAddress),
        this.getAlchemyPrice(tokenAddress)
      ]);

      return prices.find(price => price !== null) || null;

    } catch (error) {
      console.error('Error fetching token price:', error);
      return null;
    }
  }

  async getTokenData(tokenAddress: string, chainId: string = "sonic"): Promise<TokenData | null> {
    try {
      console.log(`getTokenData called with tokenAddress: ${tokenAddress}, chainId: ${chainId}`);

      // For SONIC token, prioritize getting price from database, then fallback to SonicScan.org API
      if (tokenAddress.toUpperCase() === "SONIC") {
        console.log("Fetching SONIC price from database and market data from DexScreener");
        try {
          // First, try to get the SONIC price from database, which internally falls back to SonicScan.org API if needed
          const sonicPrice = await this.getSonicPrice();
          
          if (!sonicPrice) {
            console.warn("Failed to get SONIC price from database and SonicScan.org API");
          } else {
            console.log(`✅ SONIC price retrieved: $${sonicPrice.price} (source: ${sonicPrice.source})`);
          }
          
          // Then get market data (volume, liquidity, etc.) from DexScreener
          const sonicPairs = await this.getSonicPairs(20);
          const sonicPair = sonicPairs.find(pair => 
            pair.baseToken?.symbol?.toUpperCase() === "SONIC" ||
            pair.quoteToken?.symbol?.toUpperCase() === "SONIC"
          );
          
          // Get TVL data from DefiLlama
          const tvlData = await this.getSonicTVL();
          
          // Default wrapped Sonic token address (always use the same)
          const wrappedSonicAddress = "0x039e2fB66102314Ce7b64Ce5Ce3E5183bc94aD38"; // wS token address
          
          // Always return Sonic token data with priority from SonicScan.org API, then fallback to DexScreener data
          if (sonicPair) {
            console.log("Found SONIC pair in DexScreener data");
            // Determine if SONIC is base or quote token
            const isSonicBase = sonicPair.baseToken?.symbol?.toUpperCase() === "SONIC";
            const tokenInfo = isSonicBase ? sonicPair.baseToken : sonicPair.quoteToken;
            
            return {
              address: wrappedSonicAddress,
              nativeAddress: wrappedSonicAddress,
              wrappedAddress: wrappedSonicAddress,
              symbol: "wS",
              name: "Wrapped Sonic",
              decimals: 18,
              // Use the SonicScan.org price if available (best source), otherwise fallback to DexScreener
              priceUsd: sonicPrice ? parseFloat(String(sonicPrice.price)) : parseFloat(String(sonicPair.priceUsd)),
              volume24h: sonicPair.volume24h || 0,
              liquidity: sonicPair.liquidity || 0,
              priceChange24h: sonicPair.priceChange24h || 0,
              // Add TVL data from DefiLlama
              tvl: tvlData?.tvl || 0,
              tvlChange24h: tvlData?.tvlChange24h || 0,
              // Add Sonic chain identifier
              chain: "Sonic",
              // Mark source
              source: sonicPrice ? sonicPrice.source : 'dexscreener'
            };
          } else {
            console.log("No SONIC pair found in DexScreener data, using basic token data");
            // Even without a valid pair, return token data using just price and TVL
            return {
              address: wrappedSonicAddress,
              nativeAddress: wrappedSonicAddress,
              wrappedAddress: wrappedSonicAddress,
              symbol: "wS",
              name: "Wrapped Sonic",
              decimals: 18,
              // Use the SonicScan.org price if available
              priceUsd: sonicPrice ? parseFloat(String(sonicPrice.price)) : 0.55,
              volume24h: 870000, // Default volume
              liquidity: 1470000, // Default liquidity
              priceChange24h: 1.5, // Default 24h price change
              // Add TVL data from DefiLlama if available
              tvl: tvlData?.tvl || 866116157,
              tvlChange24h: tvlData?.tvlChange24h || 0,
              // Add Sonic chain identifier
              chain: "Sonic",
              // Mark source
              source: sonicPrice ? sonicPrice.source : 'fallback'
            };
          }
        } catch (error) {
          console.error("Error fetching SONIC data:", error);
        }
      }

      console.log("Fetching data from external APIs...");
      const [dexScreenerData, memeApiData, defillamaData] = await Promise.all([
        this.fetchDexScreenerData(tokenAddress, chainId),
        this.fetchMemeApiData(tokenAddress),
        this.fetchDefiLlamaData(tokenAddress, chainId)
      ]);

      console.log("API responses:", {
        dexScreenerData: !!dexScreenerData,
        memeApiData: !!memeApiData,
        defillamaData: !!defillamaData
      });

      if (!dexScreenerData && !memeApiData && !defillamaData) {
        console.warn(`No data found for token ${tokenAddress}`);
        return null;
      }

      const tokenData: TokenData = {
        address: tokenAddress,
        symbol: dexScreenerData?.baseToken?.symbol || memeApiData?.symbol || '',
        name: dexScreenerData?.baseToken?.name || memeApiData?.name || '',
        decimals: 18, 
        prices: [],
        volume24h: dexScreenerData?.volume24h || 0,
        liquidity: dexScreenerData?.liquidity?.usd || 0,
        priceChange24h: dexScreenerData?.priceChange?.h24 || 0
      };

      const price = await this.getTokenPrice(tokenAddress, chainId);
      if (price) {
        tokenData.prices = [price];
      }

      console.log("Final tokenData:", tokenData);
      return tokenData;
    } catch (error) {
      console.error('Error fetching token data:', error);
      return null;
    }
  }

  private async fetchDexScreenerData(tokenAddress: string, chainId: string) {
    try {
      const response = await fetch(`${this.dexscreenerApi}/tokens/${chainId}/${tokenAddress}`);
      if (!response.ok) return null;
      const data = await response.json();
      return data.pairs?.[0] || null;
    } catch (error) {
      console.error('DexScreener fetch error:', error);
      return null;
    }
  }

  private async fetchMemeApiData(tokenAddress: string) {
    try {
      const response = await fetch(`${this.memeApi}/token?address=${tokenAddress}`);
      if (!response.ok) return null;
      return await response.json();
    } catch (error) {
      console.error('Meme API fetch error:', error);
      return null;
    }
  }

  private async fetchDefiLlamaData(tokenAddress: string, chainId: string) {
    try {
      const response = await fetch(`${this.defillamaApi}/token/${chainId}:${tokenAddress}`);
      if (!response.ok) return null;
      return await response.json();
    } catch (error) {
      console.error('DefiLlama fetch error:', error);
      return null;
    }
  }
}

export const marketData = new MarketDataService();