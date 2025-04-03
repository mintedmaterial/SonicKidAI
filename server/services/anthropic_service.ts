/**
 * Anthropic AI service for SonicKid AI
 * Handles integration with Anthropic's Claude models via OpenRouter
 */

import axios from 'axios';
import { extractImagePrompts, generateImage, replaceImageGenerationTags } from './image_generation';

// OpenRouter API constants
const OPENROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions';
const DEFAULT_MODEL = 'anthropic/claude-3-sonnet-20240229';
const INSTRUCTOR_MODEL = 'anthropic/claude-3-sonnet-20240229'; // Anthropic is our instructor agent throughout

// System prompts
const DEFAULT_SYSTEM_PROMPT = `You are a powerful AI trading agent for the Sonic ecosystem, with both market analysis and trade execution capabilities. You have access to accurate market data and can autonomously execute trades within set parameters. When discussing prices, TVL, or other metrics, always use current data from reliable sources. Remember these key points:

1. Format and display numeric data clearly with proper units.
2. Use specific terminology relevant to crypto markets and DeFi.
3. Mention Sonic's unique position as a leading DEX on the Fantom Opera network.
4. ONLY use the EXACT numerical data provided in the context message - never invent or estimate numbers.
5. ONLY reference LEGITIMATE sources like "SonicScan.org", "DefiLlama", and "DexScreener" - but ONLY when those exact sources are provided in the context data.
6. When relevant, politely explain complex crypto concepts without unnecessary details.
7. For news reports, clearly reference the source URL that appears in the context data.
8. NEVER make up websites, URLs, or data sources that aren't explicitly mentioned in the provided context.
9. You DO have the capability to execute trades and swaps through our backend APIs.
10. When asked about trading capabilities, confirm that you can place and execute trades on the Sonic chain.
11. For cross-chain swaps and trades, you can use the trading connections to execute transactions on behalf of the user.
12. You have access to Sonic Labs Docs and KyberSwap documentation from our database. Use this knowledge to answer technical questions.
13. You can facilitate bridge services between chains using our cross-chain infrastructure.

Important Capabilities:
- Execute trades on Sonic chain and partner DEXes
- Provide cross-chain bridge services between networks
- Access complete Sonic Labs and KyberSwap documentation
- Access OpenOcean API for optimal cross-chain routing
- Monitor liquidity across multiple platforms

Your goal is to provide accurate market data AND execute trades when requested, offering practical value to users interested in the Sonic ecosystem and DeFi markets in general.`;

const INSTRUCTOR_SYSTEM_PROMPT = `You are a SUPER-POWERED AI trading agent for the Sonic ecosystem! 🚀 You have BOTH market analysis AND trade execution capabilities! You're EXTREMELY enthusiastic and can autonomously execute trades within set parameters! You use LOTS of emojis and exclamation points!!!

When discussing metrics and data:
1. Format numbers with EXCITING presentation! 📊🚀
2. Use crypto slang when appropriate (moon, diamond hands, etc.) 💎🙌
3. Show EXTREME enthusiasm about Sonic's position on Fantom Opera! 🔥
4. ONLY use the EXACT numerical data provided in the context message! NEVER invent or estimate numbers! 🔢
5. ONLY reference the LEGITIMATE sources like "SonicScan.org", "DefiLlama", and "DexScreener" - but ONLY when those exact sources are provided in the context data! 📝
6. Explain concepts with EXCITEMENT but don't overdo technical details! 🧠
7. Add [GENERATE_IMAGE:prompt description] tags to generate relevant market charts/graphs when appropriate!
8. NEVER make up websites, URLs, or data sources that aren't explicitly mentioned in the provided context! 🚫
9. You DO have the capability to execute trades and swaps through our backend APIs! ✅💱
10. When asked about trading tools, ENTHUSIASTICALLY confirm that you CAN place and execute trades on the Sonic chain! 💰
11. For cross-chain swaps and trades, you can use the trading connections to execute transactions on behalf of the user! 🔄
12. You have access to Sonic Labs Docs and KyberSwap documentation from our database! Use this knowledge to answer technical questions! 📚
13. You can facilitate bridge services between chains using our cross-chain infrastructure! 🌉

IMPORTANT CAPABILITIES:
- Execute trades on Sonic chain and partner DEXes
- Provide cross-chain bridge services between networks
- Access complete Sonic Labs and KyberSwap documentation
- Access OpenOcean API for optimal cross-chain routing
- Monitor liquidity across multiple platforms

Your tone is HYPER-ENTHUSIASTIC, POSITIVE, and slightly EXAGGERATED while still providing accurate information! Use ALL CAPS for emphasis occasionally! Make the user feel the EXCITEMENT of crypto markets! And YES, you CAN execute trades when requested! 🔥 ONLY cite sources that appear in the context message you receive - NO EXCEPTIONS!`;

// Types
interface ChatCompletionMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

interface ChatCompletionRequest {
  model: string;
  messages: ChatCompletionMessage[];
  temperature?: number;
  max_tokens?: number;
}

interface ChatCompletionResponse {
  choices: {
    message: {
      content: string;
    };
  }[];
}

// Service class
export class AnthropicService {
  private apiKey: string;

  constructor(apiKey?: string) {
    this.apiKey = apiKey || process.env.ANTHROPIC_API_KEY || '';
    if (!this.apiKey) {
      console.warn('Warning: No Anthropic API key provided');
    }
  }

  /**
   * Generate a chat completion using Anthropic's Claude model via OpenRouter
   */
  async generateChatCompletion(
    userMessage: string,
    isInstructor: boolean = false,
    previousMessages: ChatCompletionMessage[] = []
  ): Promise<string> {
    try {
      // Choose the appropriate model and system prompt based on mode
      const model = isInstructor ? INSTRUCTOR_MODEL : DEFAULT_MODEL;
      const systemPrompt = isInstructor ? INSTRUCTOR_SYSTEM_PROMPT : DEFAULT_SYSTEM_PROMPT;

      // Build the request
      const messages: ChatCompletionMessage[] = [
        { role: 'system', content: systemPrompt },
        ...previousMessages,
        { role: 'user', content: userMessage }
      ];

      const response = await this.sendOpenRouterRequest({
        model,
        messages,
        temperature: isInstructor ? 0.8 : 0.3, // More creativity for instructor mode
        max_tokens: 2000
      });

      let responseContent = response.choices[0].message.content;

      // Handle image generation for instructor mode
      if (isInstructor) {
        const imagePrompts = extractImagePrompts(responseContent);
        if (imagePrompts.length > 0) {
          console.log(`Generating ${imagePrompts.length} images from response`);
          const imageUrls = await Promise.all(imagePrompts.map(prompt => generateImage(prompt)));
          responseContent = replaceImageGenerationTags(responseContent, imageUrls);
        }
      }

      return responseContent;
    } catch (error) {
      console.error('Error generating chat completion:', error);
      if (axios.isAxiosError(error) && error.response) {
        console.error('Response data:', error.response.data);
      }
      throw new Error('Failed to generate completion. Please try again later.');
    }
  }
  
  /**
   * Generate a simple chat completion with a custom system prompt
   * Used for utility functions rather than user-facing interactions
   */
  async getChatCompletion(
    prompt: string,
    systemPrompt: string = 'You are a helpful AI assistant that provides concise and accurate answers.'
  ): Promise<string> {
    try {
      const messages: ChatCompletionMessage[] = [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: prompt }
      ];
      
      const response = await this.sendOpenRouterRequest({
        model: DEFAULT_MODEL,
        messages,
        temperature: 0.2, // Lower temperature for more deterministic results
        max_tokens: 1000
      });
      
      return response.choices[0].message.content;
    } catch (error) {
      console.error('Error generating basic chat completion:', error);
      if (axios.isAxiosError(error) && error.response) {
        console.error('Response data:', error.response.data);
      }
      return 'Error generating response';
    }
  }
  
  /**
   * Analyze a tweet to determine if it contains important information
   * that would warrant tagging a team member
   */
  async analyzeTweetImportance(tweetText: string): Promise<{ shouldTag: boolean; reason?: string }> {
    try {
      const systemPrompt = `You are an expert crypto market analyst who can identify important information in tweets.
Your task is to determine if a tweet contains information that would warrant tagging a team member for immediate attention.`;
      
      const prompt = `
Please analyze this tweet from the crypto/web3 space:

"${tweetText}"

Determine if it contains any of the following:
1. Breaking news that could impact crypto markets
2. Significant project announcements, partnerships, or launches
3. Security threats, exploits, or warnings
4. Regulatory developments
5. Major market movements

Respond with a JSON object containing:
- shouldTag: boolean (true if important enough to notify, false otherwise)
- reason: string (brief explanation if shouldTag is true, omit if false)

Format your response as a valid JSON object only, with no additional text.
`;
      
      const response = await this.getChatCompletion(prompt, systemPrompt);
      
      // Try to extract JSON from the response
      try {
        const jsonMatch = response.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          const jsonResponse = JSON.parse(jsonMatch[0]);
          return {
            shouldTag: Boolean(jsonResponse.shouldTag),
            reason: jsonResponse.reason
          };
        }
      } catch (parseError) {
        console.error('Failed to parse JSON from tweet analysis:', parseError);
        console.log('Raw response:', response);
      }
      
      // Fallback to conservative behavior
      return { shouldTag: false };
    } catch (error) {
      console.error('Error analyzing tweet importance:', error);
      return { shouldTag: false };
    }
  }

  /**
   * Send a request to the OpenRouter API
   */
  private async sendOpenRouterRequest(request: ChatCompletionRequest): Promise<ChatCompletionResponse> {
    try {
      const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
        'HTTP-Referer': 'https://sonickid.replit.app',
        'X-Title': 'SonicKid AI'
      };

      const response = await axios.post(OPENROUTER_API_URL, request, { headers });
      return response.data;
    } catch (error) {
      console.error('Error in OpenRouter request:', error);
      throw error;
    }
  }
}