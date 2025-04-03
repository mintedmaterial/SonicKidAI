/**
 * File upload routes for SonicKid AI
 * Handles uploading and retrieving images for chart analysis
 */

import { Router } from 'express';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import { v4 as uuidv4 } from 'uuid';
import { sanitizeFilename } from '../utils/helpers';

const router = Router();

// Define upload directory
const UPLOAD_DIR = path.join(process.cwd(), 'public', 'uploads');

// Ensure directory exists
if (!fs.existsSync(UPLOAD_DIR)) {
  fs.mkdirSync(UPLOAD_DIR, { recursive: true });
}

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, UPLOAD_DIR);
  },
  filename: (req, file, cb) => {
    // Generate a safe filename
    const originalName = file.originalname;
    const fileExtension = path.extname(originalName);
    const sanitizedName = sanitizeFilename(path.basename(originalName, fileExtension));
    const uniqueFilename = `${sanitizedName}-${uuidv4().substring(0, 8)}${fileExtension}`;
    cb(null, uniqueFilename);
  }
});

// Limit upload size to 5MB and only allow images
const upload = multer({
  storage: storage,
  limits: {
    fileSize: 5 * 1024 * 1024, // 5MB
  },
  fileFilter: (req, file, cb) => {
    // Accept only image files
    if (file.mimetype.startsWith('image/')) {
      cb(null, true);
    } else {
      cb(new Error('Only image files are allowed'));
    }
  }
});

// Route to upload a file
router.post('/image', upload.single('image'), (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ success: false, error: 'No file uploaded' });
    }

    // Return the file information
    return res.json({
      success: true,
      data: {
        filename: req.file.filename,
        originalname: req.file.originalname,
        mimetype: req.file.mimetype,
        size: req.file.size,
        path: `/uploads/${req.file.filename}`,
      }
    });
  } catch (error) {
    console.error('Error uploading file:', error);
    return res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Route to get list of uploaded images
router.get('/images', (req, res) => {
  try {
    // Read all files in the upload directory
    const files = fs.readdirSync(UPLOAD_DIR);
    
    // Get file information
    const fileList = files.map(filename => {
      const filePath = path.join(UPLOAD_DIR, filename);
      const stats = fs.statSync(filePath);
      
      return {
        filename,
        path: `/uploads/${filename}`,
        size: stats.size,
        created: stats.birthtime
      };
    });
    
    // Sort by newest first
    fileList.sort((a, b) => b.created.getTime() - a.created.getTime());
    
    return res.json({
      success: true,
      data: fileList
    });
  } catch (error) {
    console.error('Error listing files:', error);
    return res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Import the AnthropicService for chart analysis
import { AnthropicService } from '../services/anthropic_service';

// Import the HuggingFaceService for BERT-based analysis
import { HuggingFaceService } from '../services/huggingface_service';

// Get reference to chatHistory
import { chatHistory } from '../utils/storage';

// Handle chart analysis
router.post('/analyze-chart', upload.single('chart'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({
        success: false,
        error: 'No chart image uploaded'
      });
    }

    // Generate a unique ID for this chart analysis
    const analysisId = uuidv4();
    
    // Get the uploaded file path
    const filePath = req.file.path;
    const fileBuffer = fs.readFileSync(filePath);
    
    // Get additional context from request
    const { context = {}, useHuggingFace = true } = req.body;
    
    let analysis = '';
    
    // Start with HuggingFace BERT model for technical pattern recognition if enabled
    if (useHuggingFace) {
      try {
        // Try to get the HuggingFace API key from our API keys service
        let huggingfaceApiKey = process.env.HUGGINGFACE_API_KEY || '';
        
        try {
          // Get API key from our API keys endpoint (internal only)
          const keyResponse = await fetch('http://localhost:3000/api/keys/huggingface/key');
          if (keyResponse.ok) {
            const keyData = await keyResponse.json();
            huggingfaceApiKey = keyData.apiKey;
            console.log('Retrieved HuggingFace API key from database');
          }
        } catch (keyError) {
          console.warn('Could not retrieve HuggingFace API key from database:', keyError);
        }
        
        if (!huggingfaceApiKey) {
          console.warn('No HuggingFace API key available. Skipping BERT analysis.');
        } else {
          // Initialize HuggingFace service with the API key
          const huggingFaceService = new HuggingFaceService(huggingfaceApiKey);
          
          // Get technical analysis from HuggingFace
          const technicalAnalysis = await huggingFaceService.getTechnicalAnalysis(fileBuffer);
          
          // Add a heading for the HuggingFace analysis
          analysis += `## BERT MODEL TECHNICAL PATTERN DETECTION\n${technicalAnalysis}\n\n`;
          
          console.log('Successfully added HuggingFace BERT analysis');
        }
      } catch (hfError) {
        console.error('Error with HuggingFace analysis:', hfError);
        // Continue with Anthropic analysis even if HuggingFace fails
      }
    }
    
    // Build the analysis prompt - simplified and focused
    const prompt = `
      Analyze this specific cryptocurrency chart image. Provide a concise analysis focusing on:
      1. Price action and pattern recognition
      2. Key support/resistance levels visible in this chart
      3. Technical indicators and what they suggest
      4. Potential short-term directional bias based on this chart only
      
      ${analysis ? 'Consider and incorporate the BERT analysis above in your assessment.' : ''}
      
      Keep your analysis brief and directly focused on what's visible in this chart only.
      Don't add references to external data sources or discuss market conditions not shown in the chart.
      Don't make specific price predictions or investment recommendations.
    `;
    
    // Get the AI service
    const aiService = new AnthropicService();
    
    // Generate analysis with Anthropic
    const anthropicAnalysis = await aiService.generateChatCompletion(
      prompt,
      true, // Use instructor mode for more comprehensive analysis
      [] // No previous messages
    );
    
    // Combine analyses if we have both, otherwise just use the Anthropic analysis
    const finalAnalysis = analysis ? `${analysis}## COMBINED ANALYSIS\n${anthropicAnalysis}` : anthropicAnalysis;
    
    // Store the analysis in memory
    const timestamp = Date.now();
    
    // Add this analysis to global chat history with source='chart-analysis'
    // This allows it to be retrieved separately from regular chat
    if (!chatHistory['default']) {
      chatHistory['default'] = [];
    }
    
    // Add as assistant message
    chatHistory['default'].push({
      role: 'assistant',
      content: finalAnalysis,
      timestamp,
      source: 'chart-analysis'
    });
    
    // Return the analysis
    res.json({
      success: true,
      data: {
        id: analysisId,
        analysis: finalAnalysis,
        timestamp,
        path: `/uploads/${req.file.filename}`,
        models: analysis.includes('BERT MODEL') ? ['anthropic', 'huggingface'] : ['anthropic']
      }
    });
    
  } catch (error) {
    console.error('Error analyzing chart:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Failed to analyze chart'
    });
  }
});

export default router;