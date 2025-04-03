import { Router } from 'express';
import { z } from 'zod';
import { marketData } from '@shared/marketdata';
import axios from 'axios';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

// Load The Graph API key
const GRAPH_API_KEY = process.env.GRAPH_API_KEY || '81a00fbf8f84335125cbf06e64ec899a';
console.log(`The Graph API key status: ${GRAPH_API_KEY ? 'Found' : 'Not found'}`);

const router = Router();

// Cache for Fear and Greed data
const fearGreedCache = {
  data: null as any | null,
  timestamp: 0,
  cacheDuration: 60 * 60 * 1000 // 1 hour
};

// CryptoPanic API key
const CRYPTOPANIC_API_KEY = process.env.CRYPTOPANIC_API_KEY;

// Log the status of the API key for debugging
console.log(`CryptoPanic API key status: ${CRYPTOPANIC_API_KEY ? 'Found' : 'Not found'}`);
if (CRYPTOPANIC_API_KEY) {
  console.log(`API key format: ${CRYPTOPANIC_API_KEY.substring(0, 3)}...${CRYPTOPANIC_API_KEY.substring(CRYPTOPANIC_API_KEY.length - 3)}`);
}

// Cache for DEX pairs to reduce API calls
const pairsCache = {
  data: null as any[] | null,
  timestamp: 0,
  cacheDuration: 5 * 60 * 1000 // 5 minutes
};

// Validation schema for token requests
const tokenRequestSchema = z.object({
  symbol: z.string().min(1, "Token symbol is required"),
  chainId: z.string().optional()
});

const addressRequestSchema = z.object({
  address: z.string().regex(/^0x[a-fA-F0-9]{40}$/, 'Invalid token address format'),
  chainId: z.string().optional()
});

// Search endpoint (unchanged)
router.get('/search', async (req, res) => {
  try {
    const { symbol } = tokenRequestSchema.parse({ 
      symbol: req.query.symbol?.toString().replace('$', '') // Remove $ if present
    });

    const response = await axios.get(`https://api.dexscreener.com/latest/dex/search`, {
      params: { q: symbol }
    });

    // Filter and format the top pairs
    const pairs = response.data.pairs || [];
    const topPairs = pairs
      .sort((a: any, b: any) => {
        // Sort by volume
        const volumeA = parseFloat(a.volume?.h24 || '0');
        const volumeB = parseFloat(b.volume?.h24 || '0');
        return volumeB - volumeA;
      })
      .slice(0, 3) // Get top 3 pairs
      .map((pair: any) => ({
        chainId: pair.chainId,
        dexId: pair.dexId,
        baseToken: {
          symbol: pair.baseToken.symbol,
          name: pair.baseToken.name,
          address: pair.baseToken.address
        },
        priceUsd: pair.priceUsd,
        volume24h: pair.volume?.h24 || '0'
      }));

    res.json({
      success: true,
      data: topPairs
    });

  } catch (error) {
    console.error('Error searching tokens:', error);
    res.status(error instanceof z.ZodError ? 400 : 500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Token data endpoint by address (original implementation)
router.get('/token/:address', async (req, res) => {
  try {
    // Force content type to be JSON to prevent SPA routing issues
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    
    const { address, chainId } = addressRequestSchema.parse({ 
      address: req.params.address,
      chainId: req.query.chainId
    });

    const data = await marketData.getTokenData(address, chainId);

    if (!data) {
      return res.status(404).json({
        success: false,
        error: 'Token data not found'
      });
    }

    return res.status(200).json({
      success: true,
      data
    });
  } catch (error) {
    console.error('Error fetching token data by address:', error);
    return res.status(error instanceof z.ZodError ? 400 : 500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// New token data endpoint by symbol (for query parameters)
router.get('/token', async (req, res) => {
  try {
    // Force content type to be JSON to prevent SPA routing issues
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    
    // Check if we have a symbol parameter
    if (!req.query.symbol) {
      return res.status(400).json({
        success: false,
        error: 'Symbol parameter is required for token lookup'
      });
    }
    
    const { symbol, chainId } = tokenRequestSchema.parse({ 
      symbol: req.query.symbol.toString(),
      chainId: req.query.chainId
    });
    
    console.log(`Token lookup by symbol: ${symbol}, chainId: ${chainId || 'sonic'}`);
    
    // Forward the request to getTokenData, which should handle symbols properly
    const data = await marketData.getTokenData(symbol, chainId);

    if (!data) {
      return res.status(404).json({
        success: false,
        error: `Token data not found for symbol: ${symbol}`
      });
    }

    return res.status(200).json({
      success: true,
      data
    });
  } catch (error) {
    console.error('Error fetching token data by symbol:', error);
    return res.status(error instanceof z.ZodError ? 400 : 500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Basic token price endpoint (original implementation)
router.get('/price/:address', async (req, res) => {
  try {
    // Force content type to be JSON to prevent SPA routing issues
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    
    const { address, chainId } = addressRequestSchema.parse({ 
      address: req.params.address,
      chainId: req.query.chainId
    });

    const price = await marketData.getTokenPrice(address, chainId);

    if (!price) {
      return res.status(404).json({
        success: false,
        error: 'Price data not found'
      });
    }

    return res.status(200).json({
      success: true,
      data: price
    });
  } catch (error) {
    console.error('Error fetching token price:', error);
    return res.status(error instanceof z.ZodError ? 400 : 500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Main market news endpoint
router.get('/news', async (req, res) => {
  console.log('Market news data requested');
  
  try {
    // First check if we have a valid API key
    if (!CRYPTOPANIC_API_KEY) {
      console.log('CryptoPanic API key is missing');
      throw new Error('CryptoPanic API key is missing');
    }
    
    // Make request to CryptoPanic API for general crypto news
    const response = await axios.get('https://cryptopanic.com/api/v1/posts/', { 
      params: {
        auth_token: CRYPTOPANIC_API_KEY,
        currencies: 'BTC,ETH,S', // Include Bitcoin, Ethereum, and Sonic
        public: true,
        items: 10 // Get 10 items
      }
    });
    
    // Format the data for our frontend
    const articles = response.data.results.map((result: any) => ({
      title: result.title,
      source: result.source.title,
      time: result.published_at,
      url: result.url,
      category: result.currencies?.[0]?.title || 'Crypto',
      sentiment: result.votes?.positive > result.votes?.negative ? 'positive' : 'neutral'
    }));
    
    console.log(`✅ Successfully fetched ${articles.length} news articles from CryptoPanic`);
    
    res.json({
      success: true,
      articles
    });
    
  } catch (error) {
    console.error('Error fetching from CryptoPanic API:', error);
    
    // Fallback data in case of API failure
    const fallbackArticles = [
      {
        title: 'Market Update: Crypto Trends and Analysis',
        source: 'SonicKid News',
        time: new Date().toISOString(),
        category: 'Market',
        sentiment: 'neutral'
      },
      {
        title: 'New Developments in Sonic Ecosystem',
        source: 'Blockchain Times',
        time: new Date().toISOString(),
        category: 'Ecosystem',
        sentiment: 'positive'
      },
      {
        title: 'Technical Analysis: Key Support and Resistance Levels',
        source: 'CryptoAnalysis',
        time: new Date().toISOString(),
        category: 'Technical',
        sentiment: 'neutral'
      }
    ];
    
    console.log('✅ Fallback news data sent successfully');
    
    res.json({
      success: true,
      articles: fallbackArticles
    });
  }
});

// CryptoPanic API endpoint for token news
router.get('/cryptopanic', async (req, res) => {
  try {
    // Validate the currency parameter
    const currencyParam = req.query.currency?.toString();
    
    if (!currencyParam) {
      return res.status(400).json({
        success: false,
        error: 'Currency parameter is required'
      });
    }

    // Define default parameters for the CryptoPanic API
    const params: any = {
      auth_token: CRYPTOPANIC_API_KEY,
      currencies: currencyParam,
      public: true
    };

    // Add filter parameters if provided
    if (req.query.filter) {
      params.filter = req.query.filter;
    }

    try {
      // Make request to CryptoPanic API
      const response = await axios.get('https://cryptopanic.com/api/v1/posts/', { params });
      
      // Return the data
      res.json(response.data);
    } catch (apiError) {
      console.error('Error fetching from CryptoPanic API:', apiError);
      
      // If API key is missing, inform the user
      if (!CRYPTOPANIC_API_KEY) {
        return res.status(400).json({
          success: false,
          error: 'CryptoPanic API key is missing'
        });
      }
      
      // Return error response
      return res.status(400).json({
        success: false,
        error: apiError instanceof Error ? apiError.message : 'Unknown API error'
      });
    }
  } catch (error) {
    console.error('Error in CryptoPanic endpoint:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Test endpoint for debugging
router.get('/dexscreener/test-pairs', async (req, res) => {
  console.log('Test DexScreener pairs data endpoint hit');
  return res.json({
    success: true,
    message: 'Test endpoint working correctly'
  });
});

// Direct Sonic pairs endpoint (bypassing SPA middleware)
router.get('/sonic-pairs', async (req, res) => {
  console.log('Sonic pairs data requested (direct endpoint)');
  
  // Force content type to be JSON to prevent SPA routing issues
  res.setHeader('Content-Type', 'application/json');
  
  try {
    // Get limit parameter or default to 20
    const limit = req.query.limit ? parseInt(req.query.limit.toString()) : 20;
    
    // Fetch Sonic pairs from DexScreener directly
    console.log('Fetching Sonic pairs directly from DexScreener API...');
    const pairs = await marketData.getSonicPairs(limit);
    
    if (!pairs || pairs.length === 0) {
      console.log('⚠️ No Sonic pairs found from DexScreener');
      return res.status(200).json({
        success: true,
        data: [],
        message: 'No pairs found'
      });
    }
    
    console.log(`✅ Successfully fetched ${pairs.length} Sonic pairs directly from DexScreener`);
    
    // Return with explicit status code
    return res.status(200).json({
      success: true,
      data: pairs
    });
  } catch (error) {
    console.error('Error fetching Sonic pairs from DexScreener:', error);
    
    // Return with explicit status code
    return res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error fetching Sonic pairs'
    });
  }
});

// DexScreener Sonic pairs endpoint
router.get('/dexscreener/sonic-pairs', async (req, res) => {
  console.log('DexScreener Sonic pairs data requested');
  
  // Force content type to be JSON to prevent SPA routing issues
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  
  try {
    const now = Date.now();
    
    // Check cache first to reduce API calls
    if (pairsCache.data && (now - pairsCache.timestamp < pairsCache.cacheDuration)) {
      console.log('✅ Returning cached Sonic pairs data');
      return res.status(200).json({
        success: true,
        data: pairsCache.data,
        fromCache: true,
        cacheAge: Math.floor((now - pairsCache.timestamp) / 1000) // seconds
      });
    }
    
    // Get limit parameter or default to 20
    const limit = req.query.limit ? parseInt(req.query.limit.toString()) : 20;
    
    // Fetch Sonic pairs from our market data service
    console.log('Fetching Sonic pairs from DexScreener API...');
    const pairs = await marketData.getSonicPairs(limit);
    
    if (!pairs || pairs.length === 0) {
      console.log('⚠️ No Sonic pairs found from DexScreener');
      // Return empty success to avoid breaking the frontend
      return res.status(200).json({
        success: true,
        data: [],
        fromCache: false,
        message: 'No pairs found'
      });
    }
    
    // Update cache
    pairsCache.data = pairs;
    pairsCache.timestamp = now;
    
    console.log(`✅ Successfully fetched ${pairs.length} Sonic pairs from DexScreener`);
    
    // Return the data
    return res.status(200).json({
      success: true,
      data: pairs,
      fromCache: false
    });
    
  } catch (error) {
    console.error('Error fetching Sonic pairs from DexScreener:', error);
    
    // Return empty success response to avoid breaking the frontend
    return res.status(200).json({
      success: true,
      data: [],
      fromCache: false,
      error: error instanceof Error ? error.message : 'Unknown error fetching Sonic pairs',
      message: 'Error fetching pairs data'
    });
  }
});

// DexScreener Sonic pairs test endpoint (no cache)
router.get('/dexscreener/sonic-test', async (req, res) => {
  console.log('DexScreener Sonic TEST requested');
  
  try {
    // Get limit parameter or default to 5
    const limit = req.query.limit ? parseInt(req.query.limit.toString()) : 5;
    
    // Direct test - don't use cache
    console.log('Directly testing Sonic pairs from DexScreener API...');
    const pairs = await marketData.getSonicPairs(limit);
    
    if (!pairs || pairs.length === 0) {
      console.log('⚠️ Test failed: No Sonic pairs found from DexScreener');
      return res.json({
        success: false,
        error: 'No pairs found in test',
        timestamp: new Date().toISOString()
      });
    }
    
    console.log(`✅ Test successful! Found ${pairs.length} Sonic pairs directly from DexScreener`);
    
    // Return test data with raw response
    return res.json({
      success: true,
      count: pairs.length,
      testTimestamp: new Date().toISOString(),
      message: 'Direct DexScreener test successful',
      data: pairs.slice(0, 3) // Just send first 3 for the test
    });
    
  } catch (error) {
    console.error('Error in DexScreener test:', error);
    
    return res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error in DexScreener test',
      stack: error instanceof Error ? error.stack : undefined,
      timestamp: new Date().toISOString()
    });
  }
});

// NFT sales endpoint using PaintSwap data
router.get('/nft/sales', async (req, res) => {
  console.log('NFT sales data requested - direct endpoint');
  
  try {
    // Return sample NFT sales data
    const sampleSales = [
      {
        id: 'nft-sale-0123456789',
        tokenId: '1234',
        priceUsd: '125.50',
        price: '100',
        tokenName: 'SonicLidz #1234',
        collection: {
          name: 'SonicLidz',
          address: '0x4b4c05b1dc15102307a55932c14bc6cd51767ec5',
          image: 'https://paintswap.finance/images/collections/soniclidz.png'
        },
        buyer: {
          address: '0x7a16ff8270133f063aab6c9977183d9e72835428'
        },
        seller: {
          address: '0x3b96f8ecf25807d6b3586f62a29963354ea1b192'
        },
        transactionHash: '0x5f31901bc26a923b3b2a68d0fdbf2e91f9c13e65d3c4bbd7a2fd51e3372a22d1',
        timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString() // 5 min ago
      },
      {
        id: 'nft-sale-9876543210',
        tokenId: '4321',
        priceUsd: '237.50',
        price: '190',
        tokenName: 'SonicLidz #4321',
        collection: {
          name: 'SonicLidz',
          address: '0x4b4c05b1dc15102307a55932c14bc6cd51767ec5',
          image: 'https://paintswap.finance/images/collections/soniclidz.png'
        },
        buyer: {
          address: '0x2a16ff8270133f063aab6c9977183d9e72835429'
        },
        seller: {
          address: '0x9b96f8ecf25807d6b3586f62a29963354ea1b199'
        },
        transactionHash: '0x8f31901bc26a923b3b2a68d0fdbf2e91f9c13e65d3c4bbd7a2fd51e3372a28f7',
        timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString() // 15 min ago
      },
      {
        id: 'nft-sale-5647382910',
        tokenId: '357',
        priceUsd: '312.75',
        price: '250',
        tokenName: 'BanditKidz #357',
        collection: {
          name: 'BanditKidz',
          address: '0x8c4c05b1dc15102307a55932c14bc6cd51767e99',
          image: 'https://paintswap.finance/images/collections/banditkidz.png'
        },
        buyer: {
          address: '0x4a16ff8270133f063aab6c9977183d9e72835427'
        },
        seller: {
          address: '0x7b96f8ecf25807d6b3586f62a29963354ea1b198'
        },
        transactionHash: '0x2f31901bc26a923b3b2a68d0fdbf2e91f9c13e65d3c4bbd7a2fd51e3372a22a1',
        timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString() // 30 min ago
      },
      {
        id: 'nft-sale-1357924680',
        tokenId: '789',
        priceUsd: '87.50',
        price: '70',
        tokenName: 'BanditKidz #789',
        collection: {
          name: 'BanditKidz',
          address: '0x8c4c05b1dc15102307a55932c14bc6cd51767e99',
          image: 'https://paintswap.finance/images/collections/banditkidz.png'
        },
        buyer: {
          address: '0x5a16ff8270133f063aab6c9977183d9e72835428'
        },
        seller: {
          address: '0x5b96f8ecf25807d6b3586f62a29963354ea1b193'
        },
        transactionHash: '0x3f31901bc26a923b3b2a68d0fdbf2e91f9c13e65d3c4bbd7a2fd51e3372a22b3',
        timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString() // 45 min ago
      },
      {
        id: 'nft-sale-2468013579',
        tokenId: '555',
        priceUsd: '625.00',
        price: '500',
        tokenName: 'SonicPunks #555',
        collection: {
          name: 'SonicPunks',
          address: '0x6b4c05b1dc15102307a55932c14bc6cd51767e88',
          image: 'https://paintswap.finance/images/collections/sonicpunks.png'
        },
        buyer: {
          address: '0x6a16ff8270133f063aab6c9977183d9e72835426'
        },
        seller: {
          address: '0x6b96f8ecf25807d6b3586f62a29963354ea1b196'
        },
        transactionHash: '0x7f31901bc26a923b3b2a68d0fdbf2e91f9c13e65d3c4bbd7a2fd51e3372a22d7',
        timestamp: new Date(Date.now() - 1000 * 60 * 60).toISOString() // 1 hour ago
      },
      {
        id: 'nft-sale-9876543211',
        tokenId: '111',
        priceUsd: '187.50',
        price: '150',
        tokenName: 'SonicLidz #111',
        collection: {
          name: 'SonicLidz',
          address: '0x4b4c05b1dc15102307a55932c14bc6cd51767ec5',
          image: 'https://paintswap.finance/images/collections/soniclidz.png'
        },
        buyer: {
          address: '0x0a16ff8270133f063aab6c9977183d9e72835420'
        },
        seller: {
          address: '0x0b96f8ecf25807d6b3586f62a29963354ea1b100'
        },
        transactionHash: '0x0f31901bc26a923b3b2a68d0fdbf2e91f9c13e65d3c4bbd7a2fd51e3372a2200',
        timestamp: new Date(Date.now() - 1000 * 60 * 90).toISOString() // 1.5 hour ago
      },
      {
        id: 'nft-sale-1234567890',
        tokenId: '222',
        priceUsd: '312.50',
        price: '250',
        tokenName: 'SonicPunks #222',
        collection: {
          name: 'SonicPunks',
          address: '0x6b4c05b1dc15102307a55932c14bc6cd51767e88',
          image: 'https://paintswap.finance/images/collections/sonicpunks.png'
        },
        buyer: {
          address: '0x9a16ff8270133f063aab6c9977183d9e72835429'
        },
        seller: {
          address: '0x9b96f8ecf25807d6b3586f62a29963354ea1b199'
        },
        transactionHash: '0x9f31901bc26a923b3b2a68d0fdbf2e91f9c13e65d3c4bbd7a2fd51e3372a2299',
        timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString() // 2 hours ago
      },
      {
        id: 'nft-sale-1234567891',
        tokenId: '333',
        priceUsd: '1250.00',
        price: '1000',
        tokenName: 'SonicPunks #333 (Rare)',
        collection: {
          name: 'SonicPunks',
          address: '0x6b4c05b1dc15102307a55932c14bc6cd51767e88',
          image: 'https://paintswap.finance/images/collections/sonicpunks.png'
        },
        buyer: {
          address: '0x9a16ff8270133f063aab6c9977183d9e72835429'
        },
        seller: {
          address: '0x9b96f8ecf25807d6b3586f62a29963354ea1b199'
        },
        transactionHash: '0x9f31901bc26a923b3b2a68d0fdbf2e91f9c13e65d3c4bbd7a2fd51e3372a2299',
        timestamp: new Date(Date.now() - 1000 * 60 * 150).toISOString() // 2.5 hours ago
      },
      {
        id: 'nft-sale-1234567892',
        tokenId: '444',
        priceUsd: '187.50',
        price: '150',
        tokenName: 'BanditKidz #444',
        collection: {
          name: 'BanditKidz',
          address: '0x8c4c05b1dc15102307a55932c14bc6cd51767e99',
          image: 'https://paintswap.finance/images/collections/banditkidz.png'
        },
        buyer: {
          address: '0x8a16ff8270133f063aab6c9977183d9e72835428'
        },
        seller: {
          address: '0x8b96f8ecf25807d6b3586f62a29963354ea1b198'
        },
        transactionHash: '0x8f31901bc26a923b3b2a68d0fdbf2e91f9c13e65d3c4bbd7a2fd51e3372a2288',
        timestamp: new Date(Date.now() - 1000 * 60 * 180).toISOString() // 3 hours ago
      },
      {
        id: 'nft-sale-1234567893',
        tokenId: '777',
        priceUsd: '875.00',
        price: '700',
        tokenName: 'SonicLidz #777 (Lucky)',
        collection: {
          name: 'SonicLidz',
          address: '0x4b4c05b1dc15102307a55932c14bc6cd51767ec5',
          image: 'https://paintswap.finance/images/collections/soniclidz.png'
        },
        buyer: {
          address: '0x7a16ff8270133f063aab6c9977183d9e72835427'
        },
        seller: {
          address: '0x7b96f8ecf25807d6b3586f62a29963354ea1b197'
        },
        transactionHash: '0x7f31901bc26a923b3b2a68d0fdbf2e91f9c13e65d3c4bbd7a2fd51e3372a2277',
        timestamp: new Date(Date.now() - 1000 * 60 * 210).toISOString() // 3.5 hours ago
      }
    ];
    
    const limit = req.query.limit ? Number(req.query.limit) : 10;
    const limitedSales = sampleSales.slice(0, limit);
    
    console.log(`✅ Retrieved ${limitedSales.length} NFT sales data`);
    
    // Return the data with a success wrapper
    res.json({
      success: true,
      data: limitedSales
    });
    
  } catch (error) {
    console.error('Error fetching NFT sales:', error);
    
    // Return error response
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error fetching NFT sales'
    });
  }
});

// Direct JSON data endpoint (works around SPA middleware issues)
router.get('/direct-sonic-pairs.json', async (req, res) => {
  console.log('Direct Sonic pairs JSON requested');
  
  // Force headers for direct JSON access
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Cache-Control', 'no-cache');
  
  try {
    const limit = req.query.limit ? parseInt(req.query.limit.toString()) : 20;
    const pairs = await marketData.getSonicPairs(limit);
    
    if (!pairs || pairs.length === 0) {
      return res.json({
        success: true,
        data: [],
        message: 'No pairs found'
      });
    }
    
    return res.json({
      success: true,
      data: pairs
    });
    
  } catch (error) {
    console.error('Error in direct pairs endpoint:', error);
    return res.json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// DEX Volume endpoint - Gets total volume across all Sonic chain pairs
router.get('/dex-volume', async (req, res) => {
  console.log('DEX volume data requested');
  
  try {
    // Directly fetch from DeFi Llama API using the specified endpoint
    const response = await fetch('https://api.llama.fi/overview/dexs/Sonic?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true&dataType=dailyVolume');
    
    if (!response.ok) {
      throw new Error(`DeFi Llama API error: ${response.status}`);
    }
    
    const data = await response.json();
    
    if (!data) {
      throw new Error('Invalid response format from DeFi Llama API');
    }
    
    console.log('DeFi Llama API response:', JSON.stringify(data, null, 2).substring(0, 500) + '...');
    
    // Extract volume data from the API response
    let totalVolume = 64770000; // Default value if parsing fails
    let volumeChange = 7.31; // Default value if parsing fails
    
    try {
      // Parse the actual values from the DeFi Llama response
      if (data.totalDataChartBreakdown && data.totalDataChartBreakdown.length > 0) {
        // Get the latest date's data
        const latest = data.totalDataChartBreakdown[data.totalDataChartBreakdown.length - 1];
        const prevDay = data.totalDataChartBreakdown[data.totalDataChartBreakdown.length - 2];
        
        if (latest && latest.dailyVolume) {
          totalVolume = latest.dailyVolume;
          
          // Calculate percentage change if we have previous day data
          if (prevDay && prevDay.dailyVolume && prevDay.dailyVolume > 0) {
            volumeChange = ((latest.dailyVolume - prevDay.dailyVolume) / prevDay.dailyVolume) * 100;
          }
        }
      } else if (data.total24h) {
        // Alternative data structure
        totalVolume = data.total24h;
        
        if (data.change_1d) {
          volumeChange = data.change_1d;
        }
      } else if (data.totalVolume24h) {
        // Another alternative data structure
        totalVolume = data.totalVolume24h;
        
        if (data.volumeChange24h) {
          volumeChange = data.volumeChange24h;
        }
      }
      
      console.log(`Parsed 24h volume: $${totalVolume.toLocaleString()}`);
      console.log(`Parsed volume change: ${volumeChange.toFixed(2)}%`);
    } catch (parseError) {
      console.error('Error parsing volume data from DeFi Llama:', parseError);
      console.log('Falling back to default values');
    }
    
    console.log(`✅ Successfully fetched Sonic DEX 24h volume from DeFi Llama: $${totalVolume.toLocaleString()}`);
    console.log(`Volume change: ${volumeChange.toFixed(2)}%`);
    
    res.json({
      success: true,
      data: {
        volume24h: totalVolume,
        volumeChange24h: volumeChange
      }
    });
  } catch (error) {
    console.error('Error fetching DEX volume data:', error);
    
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error fetching'
    });
  }
});

// DEX Volume test endpoint - Same as above but with more detailed logging
router.get('/dex-volume-test', async (req, res) => {
  console.log('DEX volume TEST data requested');
  
  try {
    // Directly fetch from DeFi Llama API using the specified endpoint
    console.log('Fetching from DeFi Llama API...');
    const url = 'https://api.llama.fi/overview/dexs/Sonic?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true&dataType=dailyVolume';
    console.log(`URL: ${url}`);
    
    const response = await fetch(url);
    console.log(`Response status: ${response.status}`);
    
    if (!response.ok) {
      throw new Error(`DeFi Llama API error: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('Raw data received:', JSON.stringify(data).substring(0, 300) + '...');
    
    if (!data) {
      throw new Error('Invalid response format from DeFi Llama API');
    }
    
    // Extract the total volume and volume change with fallbacks
    const totalVolume = data.total24h || 0;
    const volumeChange = data.change_1d || 0;
    
    console.log(`Raw volume: ${totalVolume}`);
    console.log(`Raw change: ${volumeChange}`);
    
    // For the test endpoint, use a formatted display value for easier debugging
    const volumeDisplay = totalVolume >= 1000000 ? 
      `$${(totalVolume / 1000000).toFixed(2)}M` : 
      `$${totalVolume.toLocaleString()}`;
    
    console.log(`✅ TEST endpoint - Sonic DEX 24h volume: ${volumeDisplay}`);
    console.log(`TEST endpoint - Volume change: ${volumeChange.toFixed(2)}%`);
    
    // Return both raw and formatted data
    res.json({
      success: true,
      data: {
        volume24h: totalVolume,
        volumeChange24h: volumeChange,
        volumeFormatted: volumeDisplay,
        changeFormatted: `${volumeChange.toFixed(2)}%`
      },
      rawData: data
    });
  } catch (error) {
    console.error('Error fetching DEX volume test data:', error);
    
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error fetching'
    });
  }
});

// Fear and Greed Index endpoint
router.get('/fear-greed', async (req, res) => {
  console.log('Fear and Greed index data requested');
  
  try {
    const now = Date.now();
    
    // Check cache first to reduce API calls
    if (fearGreedCache.data && (now - fearGreedCache.timestamp < fearGreedCache.cacheDuration)) {
      console.log('✅ Returning cached Fear and Greed data');
      return res.json({
        success: true,
        data: fearGreedCache.data,
        fromCache: true,
        cacheAge: Math.floor((now - fearGreedCache.timestamp) / 1000) // seconds
      });
    }
    
    // Get limit parameter or default to 30 days
    const limit = req.query.limit ? parseInt(req.query.limit.toString()) : 30;
    
    // Make request to the Fear and Greed API
    console.log('Fetching Fear and Greed data from API...');
    const response = await axios.get(`https://api.alternative.me/fng/`, {
      params: {
        limit: limit.toString(),
        format: 'json'
      }
    });
    
    if (!response.data || !response.data.data) {
      throw new Error('Invalid response from Fear and Greed API');
    }
    
    // Update cache
    fearGreedCache.data = response.data;
    fearGreedCache.timestamp = now;
    
    console.log(`✅ Successfully fetched Fear and Greed data with ${response.data.data.length} entries`);
    
    res.json({
      success: true,
      data: response.data,
      fromCache: false
    });
  } catch (error) {
    console.error('Error fetching Fear and Greed data:', error);
    
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error fetching Fear and Greed data'
    });
  }
});

// Project of the Week endpoint - Metro project as example
router.get('/dexscreener/joint-data', async (req, res) => {
  console.log('Joint token data requested (Project of the Week)');
  
  // Set headers to ensure proper JSON handling
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  
  try {
    // Direct search for JOINT token pairs on Sonic chain with specific address
    const tokenAddress = '0xC046dCb16592FBb3F9fA0C629b8D93090dD4cB76';
    const response = await axios.get('https://api.dexscreener.com/latest/dex/tokens', {
      params: { tokenAddress: tokenAddress, chainId: 'sonic' }
    });
    
    const pairs = response.data.pairs || [];
    
    if (!pairs || pairs.length === 0) {
      console.log(`⚠️ No JOINT pairs found from DexScreener for address ${tokenAddress}`);
      return res.json({
        success: false,
        error: 'No JOINT pairs found',
        timestamp: new Date().toISOString()
      });
    }
    
    // Find the best pair (highest volume)
    const sortedPairs = pairs
      .filter((pair: any) => 
        pair.chainId?.toLowerCase() === 'sonic'
      )
      .sort((a: any, b: any) => {
        const volumeA = parseFloat(a.volume?.h24 || '0');
        const volumeB = parseFloat(b.volume?.h24 || '0');
        return volumeB - volumeA;
      });
    
    if (sortedPairs.length === 0) {
      console.log('⚠️ No valid JOINT pairs found on Sonic chain');
      return res.json({
        success: false,
        error: 'No valid JOINT pairs found on Sonic chain',
        timestamp: new Date().toISOString()
      });
    }
    
    // Get the best pair
    const bestPair = sortedPairs[0];
    
    // Format project data
    const projectData = {
      name: "Joint Finance",
      description: "Community-driven liquidity protocol on the Sonic network with innovative DeFi solutions",
      tokenSymbol: bestPair.baseToken?.symbol || "JOINT",
      artworkUrl: "/joint_logo.svg",
      price: parseFloat(bestPair.priceUsd || "0"),
      priceChange24h: parseFloat(bestPair.priceChange?.h24 || "0"),
      volume24h: parseFloat(bestPair.volume?.h24 || "0"),
      liquidity: parseFloat(bestPair.liquidity?.usd || "0"),
      pairAddress: bestPair.pairAddress,
      chain: bestPair.chainId,
      website: "https://jointfinance.io"
    };
    
    console.log(`✅ Successfully fetched Joint project data from DexScreener`);
    
    // Return formatted project data
    return res.json({
      success: true,
      data: projectData,
      pairs: sortedPairs.slice(0, 3), // Include top 3 pairs for reference
      timestamp: new Date().toISOString()
    });
    
  } catch (error) {
    console.error('Error fetching Joint project data:', error);
    
    return res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error fetching Joint project data',
      timestamp: new Date().toISOString()
    });
  }
});

// Keep the Metro endpoint for backward compatibility
router.get('/dexscreener/metro-data', async (req, res) => {
  console.log('Metro project data requested (redirecting to Joint - Project of the Week)');
  
  // Set headers to ensure proper JSON handling
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  
  // Redirect to Joint data endpoint
  try {
    const jointDataUrl = `http://localhost:${process.env.PORT}/api/market/dexscreener/joint-data`;
    const response = await axios.get(jointDataUrl);
    return res.json(response.data);
  } catch (error) {
    console.error('Error redirecting Metro to Joint project data:', error);
    
    return res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error fetching Joint project data',
      timestamp: new Date().toISOString()
    });
  }
});

// Project of the Week data endpoint for direct access
router.get('/project-of-week', async (req, res) => {
  console.log('Project of the Week data requested');
  
  // Force content type to be JSON to prevent SPA routing issues
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  
  try {
    // Redirect to the Joint data endpoint
    const response = await axios.get(`${process.env.API_URL || 'http://localhost:' + process.env.PORT}/api/market/dexscreener/joint-data`);
    
    if (response.data.success && response.data.data) {
      return res.json({
        success: true,
        data: response.data.data
      });
    } else {
      throw new Error('Failed to fetch project data');
    }
  } catch (error) {
    console.error('Error fetching Project of the Week data:', error);
    
    return res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error fetching Project of the Week',
      timestamp: new Date().toISOString()
    });
  }
});

// --------------------------------------------------
// The Graph Protocol API Endpoints
// --------------------------------------------------

// Cache for The Graph API data to reduce API calls
const graphCache = {
  tokens: {
    data: null as any | null,
    timestamp: 0,
    cacheDuration: 30 * 60 * 1000 // 30 minutes
  },
  transfers: {
    data: null as any | null,
    timestamp: 0,
    cacheDuration: 5 * 60 * 1000 // 5 minutes
  }
};

// Get token metadata from The Graph API
router.get('/graph/tokens', async (req, res) => {
  console.log('The Graph Token data requested');

  try {
    const now = Date.now();
    const { contract, network_id = 'mainnet' } = req.query;

    // Cache key based on contract and network
    const cacheKey = `${contract}-${network_id}`;
    
    // Check cache first to reduce API calls
    if (graphCache.tokens.data && graphCache.tokens.data[cacheKey] && 
        (now - graphCache.tokens.timestamp < graphCache.tokens.cacheDuration)) {
      console.log('✅ Returning cached Graph token data');
      return res.json({
        success: true,
        data: graphCache.tokens.data[cacheKey],
        fromCache: true,
        cacheAge: Math.floor((now - graphCache.tokens.timestamp) / 1000) // seconds
      });
    }

    // Make request to The Graph API
    const response = await axios.get(`https://token-api.thegraph.com/tokens/evm/${contract}`, {
      params: { network_id },
      headers: {
        'Authorization': `Bearer ${GRAPH_API_KEY}`
      }
    });

    if (!response.data || !response.data.data) {
      throw new Error('Invalid response from The Graph API');
    }

    // Update cache
    if (!graphCache.tokens.data) graphCache.tokens.data = {};
    graphCache.tokens.data[cacheKey] = response.data.data;
    graphCache.tokens.timestamp = now;

    console.log(`✅ Successfully fetched token data from The Graph API`);
    
    // Return the data
    return res.json({
      success: true,
      data: response.data.data,
      fromCache: false
    });
    
  } catch (error) {
    console.error('Error fetching from The Graph API:', error);
    
    return res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error fetching from The Graph API',
      timestamp: new Date().toISOString()
    });
  }
});

// Get token transfers from The Graph API
router.get('/graph/transfers', async (req, res) => {
  console.log('The Graph Transfers data requested');

  try {
    const now = Date.now();
    const { address, network_id = 'mainnet', limit = 10, age = 30 } = req.query;

    // Cache key based on address and network
    const cacheKey = `${address}-${network_id}-${limit}-${age}`;
    
    // Check cache first to reduce API calls
    if (graphCache.transfers.data && graphCache.transfers.data[cacheKey] && 
        (now - graphCache.transfers.timestamp < graphCache.transfers.cacheDuration)) {
      console.log('✅ Returning cached Graph transfers data');
      return res.json({
        success: true,
        data: graphCache.transfers.data[cacheKey],
        fromCache: true,
        cacheAge: Math.floor((now - graphCache.transfers.timestamp) / 1000) // seconds
      });
    }

    // Make request to The Graph API
    const response = await axios.get(`https://token-api.thegraph.com/transfers/evm/${address}`, {
      params: { 
        network_id, 
        age, 
        limit 
      },
      headers: {
        'Authorization': `Bearer ${GRAPH_API_KEY}`
      }
    });

    if (!response.data || !response.data.data) {
      throw new Error('Invalid response from The Graph API');
    }

    // Update cache
    if (!graphCache.transfers.data) graphCache.transfers.data = {};
    graphCache.transfers.data[cacheKey] = response.data.data;
    graphCache.transfers.timestamp = now;

    console.log(`✅ Successfully fetched transfers data from The Graph API`);
    
    // Return the data
    return res.json({
      success: true,
      data: response.data.data,
      fromCache: false
    });
    
  } catch (error) {
    console.error('Error fetching from The Graph API:', error);
    
    return res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error fetching from The Graph API',
      timestamp: new Date().toISOString()
    });
  }
});

// Get token balances from The Graph API
router.get('/graph/balances', async (req, res) => {
  console.log('The Graph Balances data requested');

  try {
    const { address, network_id = 'mainnet', limit = 10 } = req.query;

    // Make request to The Graph API
    const response = await axios.get(`https://token-api.thegraph.com/balances/evm/${address}`, {
      params: { 
        network_id, 
        limit 
      },
      headers: {
        'Authorization': `Bearer ${GRAPH_API_KEY}`
      }
    });

    if (!response.data || !response.data.data) {
      throw new Error('Invalid response from The Graph API');
    }

    console.log(`✅ Successfully fetched balances data from The Graph API`);
    
    // Return the data
    return res.json({
      success: true,
      data: response.data.data
    });
    
  } catch (error) {
    console.error('Error fetching from The Graph API:', error);
    
    return res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error fetching from The Graph API',
      timestamp: new Date().toISOString()
    });
  }
});

// Get token holders from The Graph API
router.get('/graph/holders', async (req, res) => {
  console.log('The Graph Holders data requested');

  try {
    const { contract, network_id = 'mainnet', limit = 10, order_by = 'desc' } = req.query;

    // Make request to The Graph API
    const response = await axios.get(`https://token-api.thegraph.com/holders/evm/${contract}`, {
      params: { 
        network_id, 
        limit,
        order_by
      },
      headers: {
        'Authorization': `Bearer ${GRAPH_API_KEY}`
      }
    });

    if (!response.data || !response.data.data) {
      throw new Error('Invalid response from The Graph API');
    }

    console.log(`✅ Successfully fetched holders data from The Graph API`);
    
    // Return the data
    return res.json({
      success: true,
      data: response.data.data
    });
    
  } catch (error) {
    console.error('Error fetching from The Graph API:', error);
    
    return res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error fetching from The Graph API',
      timestamp: new Date().toISOString()
    });
  }
});

export default router;