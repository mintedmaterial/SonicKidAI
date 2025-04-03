import { Router } from 'express';
import { z } from 'zod';
import { abstractService } from '../services/abstract_service';
import { storage } from '../storage';

const router = Router();

const commandSchema = z.object({
  command: z.string().min(1, "Command is required")
});

router.post('/api/transactions/execute', async (req, res) => {
  try {
    const { command } = commandSchema.parse(req.body);

    // Parse the natural language command
    const transaction = await abstractService.parseTransactionCommand(command);
    if (!transaction) {
      return res.status(400).json({
        success: false,
        error: "Failed to parse transaction command"
      });
    }

    // Execute the transaction
    const result = await abstractService.executeTransaction(transaction);
    if (!result.success) {
      return res.status(400).json({
        success: false,
        error: result.error
      });
    }

    return res.json({
      success: true,
      transactionHash: result.transactionHash
    });

  } catch (error) {
    console.error('Transaction execution failed:', error);
    return res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

router.get('/api/transactions', async (req, res) => {
  try {
    // For now, get transactions without user filtering since we don't have auth yet
    const transactions = await storage.getUserTransactions(null);
    return res.json({
      success: true,
      transactions
    });
  } catch (error) {
    console.error('Failed to fetch transactions:', error);
    return res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

export default router;