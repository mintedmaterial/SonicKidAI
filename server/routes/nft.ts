/**
 * NFT routes for SonicKid AI
 * Handles NFT data integration
 */

import { Router } from 'express';
import axios from 'axios';
import { truncateAddress } from '../utils/helpers';

const router = Router();

// PaintSwap API URL
const PAINTSWAP_API_URL = 'https://api.paintswap.finance/v2';

// Route to get recent NFT sales
router.get('/sales', async (req, res) => {
  try {
    const limit = parseInt(req.query.limit as string) || 10;
    
    console.log(`Fetching ${limit} recent NFT sales from PaintSwap API - using all sales data`);
    const response = await axios.get(`${PAINTSWAP_API_URL}/traded-nfts`);
    const data = response.data;
    
    if (!data || !Array.isArray(data)) {
      throw new Error('Invalid response from PaintSwap API');
    }
    
    // Transform the data to our format
    const salesData = data.slice(0, limit).map((sale: any) => {
      return {
        id: sale.id || sale.txHash || `nft-${Math.random().toString(36).substring(2, 10)}`,
        name: sale.name || 'Unnamed NFT',
        collection: sale.collection?.name || 'Unknown collection',
        image: sale.image || '/assets/no-image.png',
        price: sale.price ? parseFloat(sale.price).toFixed(4) : '0.0000',
        currency: 'Sonic', // Show as "Sonic" per user request (though actual data is in FTM)
        seller: truncateAddress(sale.seller || 'Unknown'),
        buyer: truncateAddress(sale.buyer || 'Unknown'),
        timestamp: sale.timestamp || Date.now(),
        status: sale.status || 'Listed for Sale',
        url: sale.url || `https://paintswap.finance/marketplace/assets/${sale.id}`,
        chainId: sale.chainId || 'sonic',
      };
    });
    
    // Log a sample for debugging
    if (salesData.length > 0) {
      console.log(`Sample sale: ${salesData[0].name} from ${salesData[0].collection} - ${salesData[0].price} ${salesData[0].currency}`);
    }
    
    console.log(`✅ Retrieved ${salesData.length} NFT sales from PaintSwap API`);
    
    res.json({
      success: true,
      data: salesData
    });
  } catch (error) {
    console.error('Error fetching NFT sales:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch NFT sales data'
    });
  }
});

export default router;