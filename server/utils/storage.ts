/**
 * In-memory storage for SonicKid AI
 */

// Define message type with source field
interface ChatMessage {
  role: string;
  content: string;
  timestamp: number;
  source?: string; // Optional source field to track where the message came from
}

// In-memory storage for chat messages
export const chatHistory: Record<string, Array<ChatMessage>> = {};