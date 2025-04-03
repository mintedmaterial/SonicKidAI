import { Router } from 'express';
import { z } from 'zod';
import { Anthropic } from '@anthropic-ai/sdk';
import { HuggingFace } from '@huggingface/api-client' 

// the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
const ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022";

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

const router = Router();

// Test endpoint to verify routing
router.get('/health', (_req, res) => {
  return res.json({
    success: true,
    message: 'AI routes working',
    service: 'anthropic'
  });
});

// Validation schema for market analysis requests
const marketAnalysisSchema = z.object({
  data: z.object({
    text: z.string().min(1, "Market data text is required"),
    metrics: z.object({
      price: z.number().optional(),
      volume: z.number().optional(), 
      liquidity: z.number().optional(),
      priceChange: z.number().optional()
    }).optional()
  })
});

// Market analysis endpoint
router.post('/analyze', async (req, res) => {
  try {
    const { data } = marketAnalysisSchema.parse(req.body);

    const response = await anthropic.messages.create({
      model: ANTHROPIC_MODEL,
      max_tokens: 500,
      messages: [
        {
          role: "user",
          content: "You are a crypto market analyst. Analyze the market data and provide trading recommendations. Focus on key metrics like price movement, volume, and liquidity."
        },
        {
          role: "user", 
          content: `Analyze this market data :\n${data.text}`
        }
      ]
    });

    const analysis = response.content[0].text;

    return res.json({
      success: true,
      analysis
    });
  } catch (error) {
    console.error('Market analysis failed:', error);
    return res.status(error instanceof z.ZodError ? 400 : 500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Market trend analysis endpoint
router.get('/market-trend/:timeframe?', async (req, res) => {
  try {
    const timeframe = req.params.timeframe || '24h';

    const response = await anthropic.messages.create({
      model: ANTHROPIC_MODEL,
      max_tokens: 500,
      messages: [
        {
          role: "system",
          content: "You are a crypto market analyst. Analyze market trends and provide insights on market direction and momentum."
        },
        {
          role: "user",
          content: `Analyze current market trends for the ${timeframe} timeframe. Consider price action, volume, and overall market sentiment.`
        }
      ]
    });

    const analysis = response.content[0].text;

    return res.json({
      success: true,
      analysis
    });
  } catch (error) {
    console.error('Market trend analysis failed:', error);
    return res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

export default router;