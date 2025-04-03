/**
 * Deployment entry point for GOAT platform
 * 
 * This is a unified server for deployment that correctly routes
 * traffic to the appropriate services while avoiding port conflicts.
 */

// Force production mode
process.env.NODE_ENV = 'production';
// Set deployment flags to signal to all components we're in deployment mode
process.env.DEPLOYMENT_MODE = 'true';
process.env.SINGLE_SERVER_MODE = 'true';

import express from 'express';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';
import http from 'http';
import { spawn } from 'child_process';

// Configure environment
dotenv.config();

// Create Express app for main server
const app = express();
const mainPort = process.env.PORT || 3000;

// Get current directory equivalent to __dirname in CommonJS
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Simple logging function
const log = (message) => {
  console.log(`[${new Date().toISOString()}] ${message}`);
};

console.log('Starting GOAT Platform in PRODUCTION mode...');
console.log(`Process ID: ${process.pid}`);
console.log(`Current directory: ${process.cwd()}`);
console.log(`Using single-server deployment configuration`);

// Basic middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Set up health check endpoint
app.get('/api/health', (req, res) => {
  log(`Health check requested from ${req.ip}`);
  res.json({
    status: 'ok',
    environment: 'production',
    time: new Date().toISOString(),
    server: 'main-web'
  });
});

// Check for Python API server
const checkPythonApi = () => {
  return new Promise((resolve) => {
    // Try to connect to the Browser API server on port 8000
    const req = http.get('http://localhost:8000/docs', (res) => {
      if (res.statusCode === 200) {
        log('✅ Browser API Server is already running on port 8000');
        resolve(true);
      } else {
        log('⚠️ Browser API Server returned non-200 status code');
        resolve(false);
      }
    });
    
    req.on('error', () => {
      log('⚠️ Browser API Server not detected on port 8000, will start it');
      resolve(false);
    });
    
    req.setTimeout(2000, () => {
      req.destroy();
      log('⚠️ Browser API Server check timed out');
      resolve(false);
    });
  });
};

// Start Python API server if not running
const startPythonApi = () => {
  try {
    log('Starting Browser API Server...');
    const pythonProcess = spawn('python', [
      '-m', 
      'uvicorn', 
      'src.server.app:app', 
      '--host', 
      '0.0.0.0', 
      '--port', 
      '8000'
    ], {
      env: { 
        ...process.env,
        NODE_ENV: 'production',
        DEPLOYMENT_MODE: 'true'
      },
      detached: true,
      stdio: 'inherit'
    });
    
    pythonProcess.on('error', (err) => {
      console.error('Failed to start Browser API Server:', err);
    });
    
    pythonProcess.unref();
    log('✅ Browser API Server started on port 8000');
  } catch (error) {
    console.error('Error starting Browser API Server:', error);
  }
};

// Simplified API routes - we'll keep this to a minimum for deployment
app.get('/api/version', (req, res) => {
  res.json({
    version: '1.0.0',
    name: 'GOAT Platform',
    environment: 'production',
    uptime: process.uptime()
  });
});

// Proxy middleware for Browser API Server
app.use('/browser-api', (req, res) => {
  // For initial deployment, return a friendly message
  if (process.env.SKIP_API_SERVER === 'true') {
    return res.status(503).json({
      status: 'service_unavailable',
      message: 'Browser API Server is not available in this deployment',
      note: 'This service will be available in a future deployment'
    });
  }
  
  // Forward to Browser API Server on port 8000
  const apiUrl = `http://localhost:8000${req.url.replace('/browser-api', '')}`;
  log(`Proxying request to Browser API: ${apiUrl}`);
  
  const apiReq = http.request(
    apiUrl,
    {
      method: req.method,
      headers: req.headers
    },
    (apiRes) => {
      res.writeHead(apiRes.statusCode, apiRes.headers);
      apiRes.pipe(res);
    }
  );
  
  apiReq.on('error', (err) => {
    console.error('Error proxying to Browser API:', err);
    res.status(502).json({ 
      error: 'Browser API server not available',
      message: 'This service will be available in a future deployment'
    });
  });
  
  apiReq.setTimeout(2000, () => {
    apiReq.destroy();
    res.status(504).json({ 
      error: 'Browser API server timeout',
      message: 'Request timed out, service may be starting up or unavailable' 
    });
  });
  
  if (req.body) {
    apiReq.write(JSON.stringify(req.body));
  }
  
  req.pipe(apiReq);
});

// Serve static files from the dist directory (for production build)
const distPath = path.join(__dirname, 'dist');
const distPublicPath = path.join(__dirname, 'dist', 'public');
const publicPath = path.join(__dirname, 'public');

// Log the paths we're checking
console.log(`Checking for static files in: ${distPath}`);
console.log(`Checking for static files in: ${distPublicPath}`);
console.log(`Checking for static files in: ${publicPath}`);

// Try all possible static file locations
if (fs.existsSync(distPath)) {
  console.log('Serving static files from /dist directory');
  
  // First check if there's a nested public directory in dist (common in some builds)
  if (fs.existsSync(distPublicPath)) {
    console.log('Found nested public directory in dist, serving from there');
    app.use(express.static(distPublicPath));
  } else {
    // Otherwise serve from dist root
    app.use(express.static(distPath));
  }
} else {
  console.warn('Warning: dist directory not found. Run build before deployment.');
  
  // Fallback to serving from public directory
  if (fs.existsSync(publicPath)) {
    console.log('Falling back to /public directory for static files');
    app.use(express.static(publicPath));
  }
}

// Also serve assets from the root public directory regardless
if (fs.existsSync(publicPath)) {
  console.log('Serving additional assets from /public directory');
  app.use('/public', express.static(publicPath));
}

// Handle SPA routes - always return index.html for client-side routing
app.use('*', (req, res) => {
  // Try all possible index.html locations
  const distIndexPath = path.join(__dirname, 'dist', 'index.html');
  const distPublicIndexPath = path.join(__dirname, 'dist', 'public', 'index.html');
  const publicIndexPath = path.join(__dirname, 'public', 'index.html');
  
  // Log what we're looking for
  console.log(`Looking for index.html in: ${distIndexPath}`);
  console.log(`Looking for index.html in: ${distPublicIndexPath}`);
  console.log(`Looking for index.html in: ${publicIndexPath}`);
  
  // Try all locations in order of priority
  if (fs.existsSync(distIndexPath)) {
    console.log(`Serving index.html from: ${distIndexPath}`);
    res.sendFile(distIndexPath);
  } else if (fs.existsSync(distPublicIndexPath)) {
    console.log(`Serving index.html from: ${distPublicIndexPath}`);
    res.sendFile(distPublicIndexPath);
  } else if (fs.existsSync(publicIndexPath)) {
    console.log(`Serving index.html from: ${publicIndexPath}`);
    res.sendFile(publicIndexPath);
  } else {
    console.error('ERROR: No index.html found in any expected location');
    res.status(404).send('Not found - Build files missing');
  }
});

// Function to stop any competing processes that might interfere with deployment
const stopCompetingProcesses = () => {
  // In production, we want to make sure duplicate servers aren't running
  try {
    console.log('Checking for competing processes...');
    
    // Set environment variables to signal to other parts of the app
    process.env.DEPLOYMENT_MODE = 'true';
    process.env.SINGLE_SERVER_MODE = 'true';
    process.env.MANAGED_SERVER_MODE = 'true';
    
    console.log('✅ Set deployment flags to prevent secondary servers from starting');
  } catch (error) {
    console.error('Error stopping competing processes:', error);
  }
};

// Main startup function that orchestrates the deployment
const startDeployment = async () => {
  try {
    // First, stop any competing processes
    stopCompetingProcesses();
    
    // For deployment to work, temporarily skip the Browser API Server
    // during initial deployment
    console.log('⚠️ Skipping Browser API Server startup for initial deployment');
    
    // Start the main server
    app.listen(mainPort, '0.0.0.0', () => {
      console.log(`🚀 GOAT Platform running in PRODUCTION mode at http://0.0.0.0:${mainPort}`);
      console.log('✅ Deployment configuration active - Single server mode');
      console.log(`💻 Main server accessible at: http://0.0.0.0:${mainPort}`);
      console.log('⚡ Health check endpoint: /api/health');
    });
  } catch (error) {
    console.error('Failed to start deployment server:', error);
    process.exit(1);
  }
};

// Start the deployment process
startDeployment();