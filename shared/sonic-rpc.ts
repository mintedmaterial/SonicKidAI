import dotenv from 'dotenv';
import axios from 'axios';

// Initialize environment variables
dotenv.config();

// Sonic network configuration
const SONIC_RPC_URL = process.env.SONIC_RPC_URL || "https://lb.drpc.org/ogrpc?network=sonic&dkey=AmMJko_SuE44v86ofB11nuXvLABC70AR774a0mSYF3e0";
const SONIC_LABS_API_KEY = process.env.SONIC_LABS_API_KEY || "Q3UEUBJ5H26SM85B8VCAS28KPWBMS3AS6X";
const SONIC_SCAN_URL = "https://api.sonicscan.org";

// Common token addresses on Sonic network
const TOKEN_ADDRESSES: Record<string, string> = {
  SONIC: '0x5c49752d3101A9bBb4918BAE2e65e75c90f69FE8',
  USDC: '0x7F5373AE26c3E8FfC4c77b7255DF7eC1A9aF52a6',
  WETH: '0x4f95fe57bea74c8c627cce4b651f7c315dd2813c'
};

// Price cache with expiration
const priceCache = {
  data: null as number | null,
  timestamp: 0,
  expirationMs: 60000, // 1 minute cache
};

/**
 * Get S (SONIC) price directly from sonicscan.org API
 * @returns Price of 1 S (SONIC) in USD
 */
export const getSonicPriceFromSonicScan = async (): Promise<number> => {
  try {
    const now = Date.now();
    
    // Check cache validity
    if (priceCache.data !== null && 
        (now - priceCache.timestamp) < priceCache.expirationMs) {
      console.log(`Using cached SONIC price: $${priceCache.data} (${Math.round((now - priceCache.timestamp) / 1000)}s old)`);
      return priceCache.data;
    }
    
    console.log('Fetching SONIC price from SonicScan.org API...');
    
    // Use the official endpoint as provided in the documentation
    const apiUrl = `${SONIC_SCAN_URL}/api?module=stats&action=ethprice&apikey=${SONIC_LABS_API_KEY}`;
    
    const response = await axios.get(apiUrl);
    const data = response.data;
    
    if (data.status !== '1') {
      throw new Error(`SonicScan API error: ${data.message || 'Unknown error'}`);
    }
    
    // Extract price from response
    const price = parseFloat(data.result.ethusd);
    console.log(`✅ SONIC price from SonicScan.org: $${price}`);
    
    // Update cache
    priceCache.data = price;
    priceCache.timestamp = now;
    
    return price;
  } catch (error) {
    console.error('Error fetching SONIC price from SonicScan:', error);
    throw error;
  }
};

/**
 * Get token information with price from Sonic network
 * @param tokenSymbol Token symbol
 * @returns Token information object
 */
export const getSonicTokenInfo = async (tokenSymbol: string = 'SONIC'): Promise<any> => {
  try {
    if (tokenSymbol.toUpperCase() === 'SONIC') {
      console.log('Fetching SONIC token info with price from SonicScan.org API...');
      
      // Get price from the official endpoint
      const price = await getSonicPriceFromSonicScan();
      
      // Return token info with the price from SonicScan
      return {
        address: TOKEN_ADDRESSES.SONIC,
        symbol: 'SONIC',
        name: 'Sonic',
        decimals: 18,
        price,
        source: 'sonicscan.org'
      };
    } else {
      throw new Error(`Token ${tokenSymbol} not supported for direct price fetching`);
    }
  } catch (error) {
    console.error(`Error fetching ${tokenSymbol} info:`, error);
    throw error;
  }
};

// Export token addresses for reuse
export { TOKEN_ADDRESSES };