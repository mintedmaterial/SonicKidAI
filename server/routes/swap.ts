import { Router } from 'express';
import { z } from 'zod';
import axios from 'axios';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

// Create router
const router = Router();

// Get OpenOcean API key from environment
const OPENOCEAN_API_KEY = process.env.OPENOCEAN_API_KEY || '';

// Define OpenOcean API base URLs for both Pro and Community APIs
const OPENOCEAN_PRO_URL = 'https://open-api-pro.openocean.finance/v4';
const OPENOCEAN_COMMUNITY_URL = 'https://open-api.openocean.finance/v3'; // Fallback community API V3

// Determine which base URL to use based on API key availability
const OPENOCEAN_BASE_URL = OPENOCEAN_API_KEY ? OPENOCEAN_PRO_URL : OPENOCEAN_COMMUNITY_URL;

// Log API key and API endpoint status
if (OPENOCEAN_API_KEY) {
  console.log('OpenOcean API key status: Found (using Pro API endpoints)');
} else {
  console.log('OpenOcean API key status: Not found (falling back to Community API endpoints)');
}
console.log(`Using OpenOcean API base URL: ${OPENOCEAN_BASE_URL}`);

// Validation schemas
const quoteRequestSchema = z.object({
  fromChain: z.string().min(1, 'Source chain is required'),
  toChain: z.string().min(1, 'Destination chain is required'),
  fromToken: z.string().min(1, 'Source token is required'),
  toToken: z.string().min(1, 'Destination token is required'),
  amount: z.string().min(1, 'Amount is required'),
  account: z.string().regex(/^0x[a-fA-F0-9]{40}$/, 'Invalid wallet address format')
});

const swapRequestSchema = z.object({
  account: z.string().regex(/^0x[a-fA-F0-9]{40}$/, 'Invalid wallet address format'),
  route: z.any().refine(val => typeof val === 'object', {
    message: 'Route object is required'
  })
});

const statusRequestSchema = z.object({
  txHash: z.string().min(1, 'Transaction hash is required'),
  fromChain: z.string().min(1, 'Source chain is required')
});

// Chain ID mappings for easier reference
const CHAIN_IDS: Record<string, string> = {
  ethereum: '1',
  bsc: '56',
  polygon: '137',
  fantom: '250',
  avalanche: '43114',
  arbitrum: '42161',
  optimism: '10',
  base: '8453',
  sonic: '146'
};

// Get quote for cross-chain swap
router.get('/quote', async (req, res) => {
  try {
    // Validate request parameters
    const {
      fromChain,
      toChain,
      fromToken,
      toToken,
      amount,
      account
    } = quoteRequestSchema.parse({
      fromChain: req.query.fromChain?.toString(),
      toChain: req.query.toChain?.toString(),
      fromToken: req.query.fromToken?.toString(),
      toToken: req.query.toToken?.toString(),
      amount: req.query.amount?.toString(),
      account: req.query.account?.toString()
    });

    // Map chain names to chain IDs if needed
    const sourceChainId = CHAIN_IDS[fromChain.toLowerCase()] || fromChain;
    const destChainId = CHAIN_IDS[toChain.toLowerCase()] || toChain;

    console.log(`Cross-chain quote requested: ${fromChain}(${sourceChainId}) -> ${toChain}(${destChainId})`);
    console.log(`Tokens: ${fromToken} -> ${toToken}, Amount: ${amount}`);

    // Set up request to OpenOcean API
    const url = `${OPENOCEAN_BASE_URL}/cross-chain/v1/cross-quote`;
    const params = {
      fromChain: sourceChainId,
      toChain: destChainId,
      fromToken: fromToken,
      toToken: toToken,
      amount: amount,
      account: account,
      slippage: 1 // Default slippage is 1%
    };

    // Add API key header if available
    const headers: Record<string, string> = { 
      'Content-Type': 'application/json'
    };
    
    if (OPENOCEAN_API_KEY) {
      headers['apikey'] = OPENOCEAN_API_KEY;
    }

    // Make request to OpenOcean API
    const response = await axios.get(url, { 
      params,
      headers
    });

    // Return the quote data
    return res.json({
      success: true,
      data: response.data
    });
  } catch (error) {
    console.error('Error getting cross-chain quote:', error);
    
    return res.status(error instanceof z.ZodError ? 400 : 500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      timestamp: new Date().toISOString()
    });
  }
});

// Get transaction data for cross-chain swap
router.post('/transaction', async (req, res) => {
  try {
    // Validate request body
    const {
      account,
      route
    } = swapRequestSchema.parse(req.body);

    console.log(`Cross-chain swap transaction requested for account: ${account}`);

    // Set up request to OpenOcean API
    const url = `${OPENOCEAN_BASE_URL}/cross-chain/v1/cross-swap`;
    
    // Add API key header if available
    const headers: Record<string, string> = { 
      'Content-Type': 'application/json'
    };
    
    if (OPENOCEAN_API_KEY) {
      headers['apikey'] = OPENOCEAN_API_KEY;
    }

    // Make request to OpenOcean API
    const response = await axios.post(url, { 
      account, 
      route 
    }, { headers });

    // Return the transaction data
    return res.json({
      success: true,
      data: response.data
    });
  } catch (error) {
    console.error('Error getting cross-chain swap transaction:', error);
    
    return res.status(error instanceof z.ZodError ? 400 : 500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      timestamp: new Date().toISOString()
    });
  }
});

// Get cross-chain swap status
router.get('/status', async (req, res) => {
  try {
    // Validate request parameters
    const {
      txHash,
      fromChain
    } = statusRequestSchema.parse({
      txHash: req.query.txHash?.toString(),
      fromChain: req.query.fromChain?.toString()
    });

    // Map chain name to chain ID if needed
    const sourceChainId = CHAIN_IDS[fromChain.toLowerCase()] || fromChain;

    console.log(`Cross-chain swap status requested for tx: ${txHash} on chain ${fromChain}`);

    // Set up request to OpenOcean API
    const url = `${OPENOCEAN_BASE_URL}/cross-chain/v1/cross-swap-status`;
    const params = {
      hash: txHash,
      fromChain: sourceChainId
    };

    // Add API key header if available
    const headers: Record<string, string> = { 
      'Content-Type': 'application/json'
    };
    
    if (OPENOCEAN_API_KEY) {
      headers['apikey'] = OPENOCEAN_API_KEY;
    }

    // Make request to OpenOcean API
    const response = await axios.get(url, { 
      params,
      headers
    });

    // Return the status data
    return res.json({
      success: true,
      data: response.data
    });
  } catch (error) {
    console.error('Error getting cross-chain swap status:', error);
    
    return res.status(error instanceof z.ZodError ? 400 : 500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      timestamp: new Date().toISOString()
    });
  }
});

// Get supported chains
router.get('/chains', async (req, res) => {
  try {
    // Return the list of supported chains
    return res.json({
      success: true,
      data: Object.entries(CHAIN_IDS).map(([name, id]) => ({
        name,
        id
      }))
    });
  } catch (error) {
    console.error('Error getting supported chains:', error);
    
    return res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      timestamp: new Date().toISOString()
    });
  }
});

// Get supported tokens for a chain
router.get('/tokens/:chainId', async (req, res) => {
  try {
    const chainId = req.params.chainId;
    
    // Map chain name to chain ID if needed
    const mappedChainId = CHAIN_IDS[chainId.toLowerCase()] || chainId;

    console.log(`Tokens requested for chain: ${chainId} (${mappedChainId})`);

    // Set up request to OpenOcean API
    const url = `${OPENOCEAN_BASE_URL}/${mappedChainId}/tokens`;

    // Add API key header if available
    const headers: Record<string, string> = { 
      'Content-Type': 'application/json'
    };
    
    if (OPENOCEAN_API_KEY) {
      headers['apikey'] = OPENOCEAN_API_KEY;
    }

    // Make request to OpenOcean API
    const response = await axios.get(url, { headers });

    // Return the tokens data
    return res.json({
      success: true,
      data: response.data
    });
  } catch (error) {
    console.error(`Error getting tokens for chain ${req.params.chainId}:`, error);
    
    return res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      timestamp: new Date().toISOString()
    });
  }
});

export default router;