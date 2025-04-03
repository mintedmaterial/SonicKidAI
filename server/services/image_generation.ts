/**
 * Image generation service for SonicKid AI
 * Handles generating images from text prompts using Anthropic's Claude model
 */

import fs from 'fs';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';
import Anthropic from '@anthropic-ai/sdk';

// Basic SVG colors for different chart types
const COLOR_PALETTE = {
  green: '#4CAF50',
  red: '#F44336',
  blue: '#2196F3',
  purple: '#9C27B0',
  orange: '#FF9800',
  teal: '#009688',
  gray: '#9E9E9E',
  primary: '#7838fa',
  secondary: '#7d3cff',
  sonic: '#f16196'
};

// Extract image generation prompts from message
export function extractImagePrompts(message: string): string[] {
  const promptRegex = /\[GENERATE_IMAGE:(.*?)\]/g;
  const prompts: string[] = [];
  let match;
  
  while ((match = promptRegex.exec(message)) !== null) {
    if (match[1].trim()) {
      prompts.push(match[1].trim());
    }
  }
  
  return prompts;
}

// Replace image generation tags with image URLs
export function replaceImageGenerationTags(message: string, imageUrls: string[]): string {
  let updatedMessage = message;
  let urlIndex = 0;
  
  updatedMessage = updatedMessage.replace(/\[GENERATE_IMAGE:(.*?)\]/g, () => {
    if (urlIndex < imageUrls.length) {
      const imageUrl = imageUrls[urlIndex++];
      return `![Generated Image](${imageUrl})`;
    }
    return ''; // Remove the tag if no URL is available
  });
  
  return updatedMessage;
}

// Generate an image from a prompt
export async function generateImage(prompt: string): Promise<string> {
  try {
    // Create uploads directory if it doesn't exist
    const uploadsDir = path.join(process.cwd(), 'public', 'uploads');
    if (!fs.existsSync(uploadsDir)) {
      fs.mkdirSync(uploadsDir, { recursive: true });
    }

    // Currently using a fallback SVG generator since we don't have direct access to image generation API
    const svgContent = createSVGImage(prompt);
    const filename = `gen-img-${uuidv4().substring(0, 8)}.svg`;
    const filePath = path.join(uploadsDir, filename);
    
    // Write SVG file
    fs.writeFileSync(filePath, svgContent);
    
    // Return the URL
    return `/uploads/${filename}`;
  } catch (error) {
    console.error('Error generating image:', error);
    throw error;
  }
}

// Create a basic SVG image based on prompt
function createSVGImage(prompt: string): string {
  const promptLower = prompt.toLowerCase();
  let svgContent = '';
  
  // Identify chart type from prompt
  const isBarChart = promptLower.includes('bar chart') || promptLower.includes('bar graph');
  const isLineChart = promptLower.includes('line chart') || promptLower.includes('trend');
  const isPieChart = promptLower.includes('pie chart') || promptLower.includes('distribution');
  const isCandle = promptLower.includes('candle') || promptLower.includes('candlestick');
  const isBullish = promptLower.includes('bull') || promptLower.includes('up') || promptLower.includes('positive');
  const isBearish = promptLower.includes('bear') || promptLower.includes('down') || promptLower.includes('negative');
  
  // Default dimensions
  const width = 500;
  const height = 300;
  
  // Base SVG with a white background
  svgContent = `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="${width}" height="${height}" fill="white"/>
  <text x="10" y="20" font-family="Arial" font-size="14" fill="#333">${escapeXML(prompt)}</text>`;
  
  // Add content based on chart type
  if (isBarChart) {
    // Simple bar chart
    const numBars = 7;
    const barWidth = (width - 40) / numBars - 10;
    const maxBarHeight = height - 60;
    
    // Add bars
    for (let i = 0; i < numBars; i++) {
      // Random height between 20% and 90% of maxBarHeight
      let barHeight;
      
      if (isBullish) {
        // Trend up for bullish
        barHeight = maxBarHeight * (0.2 + (i * 0.1) + Math.random() * 0.15);
      } else if (isBearish) {
        // Trend down for bearish
        barHeight = maxBarHeight * (0.8 - (i * 0.08) + Math.random() * 0.15);
      } else {
        // Random pattern
        barHeight = maxBarHeight * (0.2 + Math.random() * 0.7);
      }
      
      // Bar color
      let barColor = isBullish ? COLOR_PALETTE.green : (isBearish ? COLOR_PALETTE.red : COLOR_PALETTE.sonic);
      
      // Add bar
      svgContent += `
      <rect x="${20 + i * (barWidth + 10)}" y="${height - 40 - barHeight}" width="${barWidth}" height="${barHeight}" 
        fill="${barColor}" stroke="#333" stroke-width="1" rx="2"/>`;
    }
    
    // Add axes
    svgContent += `
    <line x1="20" y1="${height - 40}" x2="${width - 20}" y2="${height - 40}" stroke="#333" stroke-width="2"/>
    <line x1="20" y1="40" x2="20" y2="${height - 40}" stroke="#333" stroke-width="2"/>`;
    
  } else if (isLineChart) {
    // Simple line chart
    const numPoints = 8;
    const pointWidth = (width - 40) / (numPoints - 1);
    const maxHeight = height - 60;
    const points = [];
    
    // Generate points
    for (let i = 0; i < numPoints; i++) {
      let y;
      if (isBullish) {
        // Trend up for bullish
        y = maxHeight * (0.7 - (i * 0.08) - Math.random() * 0.1);
      } else if (isBearish) {
        // Trend down for bearish
        y = maxHeight * (0.3 + (i * 0.08) + Math.random() * 0.1);
      } else {
        // Random pattern with some smoothness
        if (i === 0) {
          y = maxHeight * (0.3 + Math.random() * 0.4);
        } else {
          // Make the next point somewhat related to the previous
          const prevY = points[i-1].y;
          const change = maxHeight * (Math.random() * 0.2 - 0.1);
          y = Math.max(0.1 * maxHeight, Math.min(0.9 * maxHeight, prevY + change));
        }
      }
      points.push({ x: 20 + i * pointWidth, y: 40 + y });
    }
    
    // Create the line path
    let pathData = `M ${points[0].x} ${points[0].y}`;
    for (let i = 1; i < points.length; i++) {
      pathData += ` L ${points[i].x} ${points[i].y}`;
    }
    
    // Line color
    const lineColor = isBullish ? COLOR_PALETTE.green : (isBearish ? COLOR_PALETTE.red : COLOR_PALETTE.sonic);
    
    // Add the path
    svgContent += `
    <path d="${pathData}" fill="none" stroke="${lineColor}" stroke-width="3"/>`;
    
    // Add markers at each point
    points.forEach(point => {
      svgContent += `
      <circle cx="${point.x}" cy="${point.y}" r="4" fill="${lineColor}" stroke="#333" stroke-width="1"/>`;
    });
    
    // Add axes
    svgContent += `
    <line x1="20" y1="${height - 40}" x2="${width - 20}" y2="${height - 40}" stroke="#333" stroke-width="2"/>
    <line x1="20" y1="40" x2="20" y2="${height - 40}" stroke="#333" stroke-width="2"/>`;
    
  } else if (isPieChart) {
    // Simple pie chart
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) / 2 - 40;
    
    // Define segments (random values that add up to 100%)
    const segments = [
      { percentage: 30 + Math.random() * 20, color: COLOR_PALETTE.sonic },
      { percentage: 15 + Math.random() * 15, color: COLOR_PALETTE.blue },
      { percentage: 10 + Math.random() * 15, color: COLOR_PALETTE.purple },
      { percentage: 5 + Math.random() * 10, color: COLOR_PALETTE.teal },
      { percentage: 5 + Math.random() * 10, color: COLOR_PALETTE.orange }
    ];
    
    // Normalize to ensure they sum to 100%
    const total = segments.reduce((sum, segment) => sum + segment.percentage, 0);
    segments.forEach(segment => {
      segment.percentage = segment.percentage / total * 100;
    });
    
    // Draw pie segments
    let startAngle = 0;
    segments.forEach((segment, index) => {
      const endAngle = startAngle + (segment.percentage / 100) * 2 * Math.PI;
      
      // Calculate arc points
      const startX = centerX + radius * Math.cos(startAngle);
      const startY = centerY + radius * Math.sin(startAngle);
      const endX = centerX + radius * Math.cos(endAngle);
      const endY = centerY + radius * Math.sin(endAngle);
      
      // Create arc path (large arc flag is 1 if angle > 180 degrees)
      const largeArcFlag = endAngle - startAngle > Math.PI ? 1 : 0;
      
      // Draw the segment
      svgContent += `
      <path d="M ${centerX} ${centerY} L ${startX} ${startY} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${endX} ${endY} Z" 
        fill="${segment.color}" stroke="#333" stroke-width="1"/>`;
      
      // Add a label
      const labelAngle = startAngle + (endAngle - startAngle) / 2;
      const labelRadius = radius * 0.7;
      const labelX = centerX + labelRadius * Math.cos(labelAngle);
      const labelY = centerY + labelRadius * Math.sin(labelAngle);
      
      svgContent += `
      <text x="${labelX}" y="${labelY}" font-family="Arial" font-size="12" fill="white" 
        text-anchor="middle" dominant-baseline="middle">${Math.round(segment.percentage)}%</text>`;
      
      startAngle = endAngle;
    });
    
  } else if (isCandle) {
    // Simple candlestick chart
    const numCandles = 10;
    const candleWidth = (width - 40) / numCandles - 6;
    const maxCandleHeight = height - 80;
    const baseline = height - 40;
    
    // Draw grid lines
    for (let i = 1; i < 5; i++) {
      const y = baseline - (maxCandleHeight / 4) * i;
      svgContent += `
      <line x1="20" y1="${y}" x2="${width - 20}" y2="${y}" stroke="#ddd" stroke-width="1" stroke-dasharray="4"/>`;
    }
    
    // Add candles
    for (let i = 0; i < numCandles; i++) {
      const x = 20 + i * ((width - 40) / numCandles);
      
      // Determine if this candle is up or down
      let isUp;
      if (isBullish) {
        isUp = Math.random() > 0.3; // 70% up candles for bullish
      } else if (isBearish) {
        isUp = Math.random() > 0.7; // 30% up candles for bearish
      } else {
        isUp = Math.random() > 0.5; // Random
      }
      
      // Candle body
      const bodyHeight = Math.max(1, Math.round(Math.random() * maxCandleHeight * 0.3));
      const wickHeight = Math.max(bodyHeight, Math.round(Math.random() * maxCandleHeight * 0.5));
      
      // Calculate positions
      const wickTop = baseline - wickHeight;
      let bodyTop, bodyBottom;
      
      if (isUp) {
        bodyBottom = baseline - (wickHeight - bodyHeight) / 2;
        bodyTop = bodyBottom - bodyHeight;
      } else {
        bodyTop = wickTop + (wickHeight - bodyHeight) / 2;
        bodyBottom = bodyTop + bodyHeight;
      }
      
      // Candle color
      const candleColor = isUp ? COLOR_PALETTE.green : COLOR_PALETTE.red;
      
      // Draw wick
      svgContent += `
      <line x1="${x + candleWidth/2}" y1="${wickTop}" x2="${x + candleWidth/2}" y2="${baseline}" 
        stroke="#333" stroke-width="1"/>`;
      
      // Draw body
      svgContent += `
      <rect x="${x}" y="${bodyTop}" width="${candleWidth}" height="${bodyBottom - bodyTop}" 
        fill="${candleColor}" stroke="#333" stroke-width="1"/>`;
    }
    
    // Add axis
    svgContent += `
    <line x1="20" y1="${baseline}" x2="${width - 20}" y2="${baseline}" stroke="#333" stroke-width="2"/>`;
    
  } else {
    // Default chart - a simple bar+line combination
    const numBars = 5;
    const barWidth = (width - 60) / numBars - 10;
    const maxBarHeight = height - 80;
    
    // Add bars
    const points = [];
    for (let i = 0; i < numBars; i++) {
      const barHeight = maxBarHeight * (0.3 + Math.random() * 0.5);
      const x = 30 + i * (barWidth + 10);
      const y = height - 40 - barHeight;
      
      // Add bar
      svgContent += `
      <rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" 
        fill="${COLOR_PALETTE.sonic}" opacity="0.7" stroke="#333" stroke-width="1" rx="2"/>`;
      
      // Save point for line
      points.push({ x: x + barWidth/2, y: y });
    }
    
    // Create the line path
    let pathData = `M ${points[0].x} ${points[0].y}`;
    for (let i = 1; i < points.length; i++) {
      pathData += ` L ${points[i].x} ${points[i].y}`;
    }
    
    // Add the path
    svgContent += `
    <path d="${pathData}" fill="none" stroke="${COLOR_PALETTE.blue}" stroke-width="3"/>`;
    
    // Add markers at each point
    points.forEach(point => {
      svgContent += `
      <circle cx="${point.x}" cy="${point.y}" r="4" fill="${COLOR_PALETTE.blue}" stroke="#333" stroke-width="1"/>`;
    });
    
    // Add axes
    svgContent += `
    <line x1="20" y1="${height - 40}" x2="${width - 20}" y2="${height - 40}" stroke="#333" stroke-width="2"/>
    <line x1="20" y1="40" x2="20" y2="${height - 40}" stroke="#333" stroke-width="2"/>`;
  }
  
  // Close SVG
  svgContent += `\n</svg>`;
  
  return svgContent;
}

// Escape XML special characters
function escapeXML(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}