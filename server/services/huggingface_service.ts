/**
 * HuggingFace service for chart analysis using BERT models
 * Provides an interface to use HuggingFace sentiment and vision models for analyzing charts
 */

import axios from 'axios';

interface HuggingFaceVisionResponse {
  generated_text: string;
}

interface HuggingFaceSentimentResponse {
  label: string;
  score: number;
}

export class HuggingFaceService {
  private apiKey: string;
  private baseUrl: string = 'https://api-inference.huggingface.co/models';

  constructor(apiKey?: string) {
    this.apiKey = apiKey || process.env.HUGGINGFACE_API_KEY || '';
    if (!this.apiKey) {
      console.warn('HuggingFace API key not provided. Some features may not work.');
    }
  }

  /**
   * Set API key for HuggingFace service
   * @param apiKey HuggingFace API key
   */
  setApiKey(apiKey: string): void {
    this.apiKey = apiKey;
  }

  /**
   * Analyze a chart image using a vision-language model
   * @param imageBuffer Buffer containing the chart image
   * @param modelId HuggingFace model ID to use (default: microsoft/git-base-coco)
   * @returns Analysis text about the chart
   */
  async analyzeChartImage(
    imageBuffer: Buffer,
    modelId: string = 'microsoft/git-base-coco'
  ): Promise<string> {
    try {
      if (!this.apiKey) {
        return 'API key not configured for HuggingFace service.';
      }

      const response = await axios.post(
        `${this.baseUrl}/${modelId}`,
        imageBuffer,
        {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/octet-stream'
          },
          timeout: 30000 // 30 second timeout
        }
      );

      if (response.status !== 200) {
        throw new Error(`HuggingFace API responded with status ${response.status}`);
      }

      const data = response.data as HuggingFaceVisionResponse;
      return data.generated_text || 'No analysis generated.';
    } catch (error) {
      console.error('Error analyzing chart image with HuggingFace:', error);
      return 'Failed to analyze the chart image. Please try again later.';
    }
  }

  /**
   * Analyze sentiment of text using a BERT model
   * @param text Text to analyze
   * @param modelId HuggingFace model ID to use (default: finiteautomata/bertweet-base-sentiment-analysis)
   * @returns Sentiment analysis result
   */
  async analyzeSentiment(
    text: string,
    modelId: string = 'finiteautomata/bertweet-base-sentiment-analysis'
  ): Promise<{ sentiment: string; score: number }> {
    try {
      if (!this.apiKey) {
        return { sentiment: 'neutral', score: 0.5 };
      }

      const response = await axios.post(
        `${this.baseUrl}/${modelId}`,
        { inputs: text },
        {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json'
          },
          timeout: 10000 // 10 second timeout
        }
      );

      if (response.status !== 200) {
        throw new Error(`HuggingFace API responded with status ${response.status}`);
      }

      const data = response.data as HuggingFaceSentimentResponse[];
      if (!data || data.length === 0) {
        return { sentiment: 'neutral', score: 0.5 };
      }

      return {
        sentiment: data[0].label.toLowerCase(),
        score: data[0].score
      };
    } catch (error) {
      console.error('Error analyzing sentiment with HuggingFace:', error);
      return { sentiment: 'neutral', score: 0.5 };
    }
  }

  /**
   * Get technical analysis for a crypto chart
   * @param imageBuffer Buffer containing the chart image
   * @returns Technical analysis of the chart
   */
  async getTechnicalAnalysis(imageBuffer: Buffer): Promise<string> {
    try {
      // Use a more specialized model for technical chart analysis if available
      const modelId = 'salesforce/blip-image-captioning-large';
      const baseAnalysis = await this.analyzeChartImage(imageBuffer, modelId);
      
      // Enhance the analysis with crypto-specific terminology
      return this.enhanceWithCryptoTerminology(baseAnalysis);
    } catch (error) {
      console.error('Error getting technical analysis:', error);
      return 'Failed to perform technical analysis on the chart.';
    }
  }

  /**
   * Enhance generic image analysis with crypto-specific terminology
   * @param analysis Original analysis
   * @returns Enhanced analysis with crypto terminology
   */
  private enhanceWithCryptoTerminology(analysis: string): string {
    // Replace generic terms with more crypto-specific ones
    const enhancedAnalysis = analysis
      .replace(/line graph/gi, 'price chart')
      .replace(/upward trend/gi, 'bullish trend')
      .replace(/downward trend/gi, 'bearish trend')
      .replace(/going up/gi, 'in an uptrend')
      .replace(/going down/gi, 'in a downtrend')
      .replace(/peak/gi, 'resistance level')
      .replace(/valley/gi, 'support level')
      .replace(/fluctuation/gi, 'volatility')
      .replace(/steady/gi, 'consolidating')
      .replace(/increase/gi, 'rally')
      .replace(/decrease/gi, 'correction');

    return enhancedAnalysis;
  }
}