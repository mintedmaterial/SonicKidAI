/**
 * Chat routes for SonicKid AI
 * Handles chat conversations and AI responses
 */

import { Router } from 'express';
import { AnthropicService } from '../services/anthropic_service';
import axios from 'axios';

const router = Router();
const anthropicService = new AnthropicService();

// Import shared storage
import { chatHistory } from '../utils/storage';

// Route to get all messages for a session
router.get('/messages', (req, res) => {
  const sessionId = req.query.sessionId || 'default';
  const source = req.query.source || 'all'; // Filter by source (chat, chart-analysis, etc.)
  
  let messages = chatHistory[sessionId as string] || [];
  
  // Filter messages by source if specified
  if (source !== 'all') {
    // For 'chat' source, also include messages that don't have a source specified (legacy data)
    if (source === 'chat') {
      messages = messages.filter(msg => !msg.source || msg.source === 'chat');
    } else {
      messages = messages.filter(msg => msg.source === source);
    }
  }
  
  res.json({
    success: true,
    data: messages
  });
});

// Get market data for context
async function fetchMarketData() {
  try {
    // Fetch Sonic price data from internal API
    const sonicResponse = await axios.get('http://localhost:3000/api/market/sonic');
    const sonicData = sonicResponse.data.data;
    
    // Fetch top pairs data from internal API
    const pairsResponse = await axios.get('http://localhost:3000/api/market/pairs');
    const pairsData = pairsResponse.data.data;
    
    // Fetch NFT sales data from internal API
    const nftResponse = await axios.get('http://localhost:3000/api/nft/sales');
    const nftData = nftResponse.data.data;
    
    // Fetch news data from internal API
    const newsResponse = await axios.get('http://localhost:3000/api/news/recent');
    const newsData = newsResponse.data.data;
    
    return {
      sonic: sonicData,
      pairs: pairsData.slice(0, 5), // Top 5 pairs
      nfts: nftData.slice(0, 3),    // Latest 3 NFT sales
      news: newsData.slice(0, 3)    // Latest 3 news items
    };
  } catch (error) {
    console.error('Error fetching market data for chat context:', error);
    return null;
  }
}

// Generate a local response when AI is unavailable
function generateLocalResponse(userMessage: string, marketData: any): string {
  const lowercaseMessage = userMessage.toLowerCase();
  
  // Check for price query
  if (lowercaseMessage.includes('price') && lowercaseMessage.includes('sonic')) {
    const price = marketData?.sonic?.price || '0.00';
    const change = marketData?.sonic?.priceChange24h || '0.00';
    const direction = parseFloat(change) >= 0 ? 'up' : 'down';
    
    return `The current price of Sonic is $${price}, which is ${direction} ${Math.abs(parseFloat(change))}% in the last 24 hours. This data is from our internal market tracker.`;
  }
  
  // Check for market/TVL query
  if (lowercaseMessage.includes('tvl') || 
      (lowercaseMessage.includes('market') && lowercaseMessage.includes('data'))) {
    const tvl = marketData?.sonic?.tvl || 'Unknown';
    const volume = marketData?.sonic?.volume24h || 'Unknown';
    
    return `Sonic currently has a Total Value Locked (TVL) of $${tvl} with a 24-hour trading volume of $${volume}. This data is from our internal market tracker.`;
  }
  
  // Check for NFT query
  if (lowercaseMessage.includes('nft') || lowercaseMessage.includes('collectible')) {
    if (marketData?.nfts?.length > 0) {
      const nft = marketData.nfts[0];
      return `Recent NFT activity: "${nft.name}" ${nft.status} for ${nft.price} Sonic. Check the NFT section for more details.`;
    } else {
      return `I don't have any recent NFT data available at the moment.`;
    }
  }
  
  // Default response
  return `I'm sorry, but I couldn't generate a response at this time. Please try again later or check the market data directly from the dashboard.`;
}

// Get AI response using TopHat
async function getAIResponse(userMessage: string, marketData: any, isInstructor: boolean = false): Promise<string> {
  try {
    // Format market data as context for the AI
    let contextMessage = 'Here is the current market data from our authenticated sources:\n\n';
    
    if (marketData?.sonic) {
      contextMessage += `MARKET DATA (From SonicScan.org and DefiLlama):\n`;
      contextMessage += `Sonic Price: $${marketData.sonic.price} (Source: SonicScan.org)\n`;
      contextMessage += `24h Change: ${marketData.sonic.priceChange24h}% (Source: SonicScan.org)\n`;
      contextMessage += `Market Cap: $${marketData.sonic.marketCap} (Source: SonicScan.org)\n`;
      contextMessage += `TVL: $${marketData.sonic.tvl} (Source: DefiLlama)\n`;
      contextMessage += `24h Volume: $${marketData.sonic.volume24h} (Source: DexScreener)\n\n`;
    }
    
    if (marketData?.pairs && marketData.pairs.length > 0) {
      contextMessage += 'TOP TRADING PAIRS (From DexScreener):\n';
      marketData.pairs.forEach((pair: any, index: number) => {
        contextMessage += `${index + 1}. ${pair.token0Symbol}/${pair.token1Symbol}: $${pair.volumeUSD24h} (24h volume)\n`;
      });
      contextMessage += '\n';
    }
    
    if (marketData?.nfts && marketData.nfts.length > 0) {
      contextMessage += 'RECENT NFT SALES (From PaintSwap):\n';
      marketData.nfts.forEach((nft: any, index: number) => {
        contextMessage += `${index + 1}. "${nft.name}" ${nft.status} for ${nft.price} Sonic\n`;
      });
      contextMessage += '\n';
    }
    
    if (marketData?.news && marketData.news.length > 0) {
      contextMessage += 'RECENT NEWS (From CryptoPanic):\n';
      marketData.news.forEach((item: any, index: number) => {
        contextMessage += `${index + 1}. ${item.title} - Source: ${item.source} (${item.url})\n`;
      });
      contextMessage += '\n';
    }
    
    contextMessage += 'DOCUMENTATION RESOURCES:\n';
    contextMessage += '- Sonic Labs Documentation: Complete technical documentation for the Sonic ecosystem\n';
    contextMessage += '- KyberSwap Documentation: API reference and integration guide for KyberSwap\n';
    contextMessage += '- OpenOcean API: Cross-chain swap routing documentation\n';
    contextMessage += '- Bridge Services: Cross-chain bridging capabilities for assets\n\n';
    
    contextMessage += 'IMPORTANT: When answering, always reference the legitimate data sources where we get our information from (SonicScan.org, DefiLlama, DexScreener, PaintSwap, CryptoPanic) and use the direct URLs provided in the news items. You have access to documentation for technical questions about Sonic Labs, KyberSwap, and cross-chain bridges.\n\n';
    
    // Generate AI response with context
    const response = await anthropicService.generateChatCompletion(
      `${contextMessage}\nUser Question: ${userMessage}`,
      isInstructor
    );
    
    return response;
  } catch (error) {
    console.error('Error getting AI response:', error);
    return generateLocalResponse(userMessage, marketData);
  }
}

// Route to send a message and get a response
router.post('/message', async (req, res) => {
  try {
    const { 
      message, 
      sessionId = 'default', 
      mode = 'standard',
      source = 'chat',  // New parameter to track message source (chat, chart-analysis, etc.)
      context = {}      // Optional context data (for chart analysis, etc.)
    } = req.body;
    
    if (!message) {
      return res.status(400).json({
        success: false,
        error: 'Message is required'
      });
    }
    
    // Initialize session history if it doesn't exist
    if (!chatHistory[sessionId]) {
      chatHistory[sessionId] = [];
    }
    
    // Add user message to history with source info
    chatHistory[sessionId].push({
      role: 'user',
      content: message,
      timestamp: Date.now(),
      source: source // Track where message came from
    });
    
    // Get market data for context
    const marketData = await fetchMarketData();
    
    // Get AI response based on mode
    const isInstructor = mode === 'instructor';
    const aiResponse = await getAIResponse(message, marketData, isInstructor);
    
    // Add AI response to history with source info
    chatHistory[sessionId].push({
      role: 'assistant',
      content: aiResponse,
      timestamp: Date.now(),
      source: source // Keep same source as query
    });
    
    // Limit history to last 50 messages per session
    if (chatHistory[sessionId].length > 50) {
      chatHistory[sessionId] = chatHistory[sessionId].slice(-50);
    }
    
    // Return the AI response
    res.json({
      success: true,
      data: {
        message: aiResponse,
        timestamp: Date.now(),
        source: source
      }
    });
  } catch (error) {
    console.error('Error processing message:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to process message'
    });
  }
});

// Route to clear chat history
router.delete('/messages', (req, res) => {
  const { sessionId = 'default' } = req.body;
  
  // Clear session history
  chatHistory[sessionId] = [];
  
  res.json({
    success: true,
    message: 'Chat history cleared'
  });
});

export default router;