import { Router } from 'express';
import { z } from 'zod';
import { executeCrossChainSwap } from '@shared/squidsdk';

const router = Router();

// Validation schema for cross-chain swap requests
const swapSchema = z.object({
  fromChain: z.string(),
  toChain: z.string(),
  fromToken: z.string(),
  toToken: z.string(),
  amount: z.string(),
  toAddress: z.string().optional()
});

router.post('/swap', async (req, res) => {
  try {
    const validatedData = swapSchema.parse(req.body);
    
    // Use default address if not provided
    const toAddress = validatedData.toAddress || process.env.SQUID_EVM_ADDRESS;
    
    const result = await executeCrossChainSwap({
      ...validatedData,
      fromAddress: process.env.SQUID_EVM_ADDRESS!,
      toAddress
    });

    if (result.success) {
      res.json({
        success: true,
        transaction: result
      });
    } else {
      res.status(400).json({
        success: false,
        error: result.error
      });
    }
  } catch (error) {
    console.error('Error processing cross-chain swap:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

export default router;
