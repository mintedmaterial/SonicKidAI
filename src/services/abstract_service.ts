import { ethers } from 'ethers';
import { insertTransactionSchema, type InsertTransaction } from '@shared/schema';
import { storage } from '../storage';

export class AbstractService {
  private apiKey: string;
  private baseUrl: string;
  private agentId: string | null;

  constructor() {
    this.apiKey = "5a693905b3aa8160ff2941f0a42058c100ea2af2ba54e53864ee1166fa6810b7";
    this.baseUrl = "https://agent.api.eternalai.org/api/agent";
    this.agentId = null; // Will be set after creating or retrieving agent
  }

  private async createHeaders() {
    return {
      'Authorization': `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json'
    };
  }

  async parseTransactionCommand(command: string): Promise<InsertTransaction | null> {
    try {
      const response = await fetch('https://api.eternalai.org/v1/chat/completions', {
        method: 'POST',
        headers: await this.createHeaders(),
        body: JSON.stringify({
          chain_id: "8453", // Base network
          model: "DeepSeek-R1-Distill-Llama-70B",
          messages: [
            {
              role: "system",
              content: `Parse transaction command into JSON format with fields:
                {
                  "amount": string,
                  "tokenSymbol": string,
                  "toAddress": string
                }
              Example commands:
              - "Send 100 USDC to 0xabc..."
              - "Transfer 0.1 ETH to 0xdef..."
              - "Pay 50 USDC on Abstract to 0xghi..."
              `
            },
            {
              role: "user",
              content: command
            }
          ],
          response_format: { type: "json_object" }
        })
      });

      if (!response.ok) {
        throw new Error(`Error code: ${response.status} - ${await response.text()}`);
      }

      const data = await response.json();
      const parsedCommand = JSON.parse(data.choices[0].message.content);

      const transaction: InsertTransaction = {
        amount: parsedCommand.amount.toString(),
        tokenSymbol: parsedCommand.tokenSymbol,
        toAddress: parsedCommand.toAddress,
        userId: null // Will be set when user authentication is added
      };

      // Validate the transaction data
      return insertTransactionSchema.parse(transaction);

    } catch (error) {
      console.error('Failed to parse transaction command:', error);
      return null;
    }
  }

  async executeTransaction(transaction: InsertTransaction): Promise<{
    success: boolean;
    transactionHash?: string;
    error?: string;
  }> {
    try {
      // Store transaction in database first
      const storedTx = await storage.createTransaction(transaction);

      // Execute the transaction on Abstract
      // This is where we would integrate with the Abstract protocol
      // For now, we'll simulate a successful transaction
      const txHash = ethers.hexlify(ethers.randomBytes(32));

      // Update transaction status
      await storage.updateTransactionStatus(storedTx.id, "completed", txHash);

      return {
        success: true,
        transactionHash: txHash
      };

    } catch (error) {
      console.error('Transaction failed:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  // Add more methods for Abstract protocol integration later
}

export const abstractService = new AbstractService();
