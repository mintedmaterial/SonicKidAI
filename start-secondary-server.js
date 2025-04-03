/**
 * Secondary Server Script
 * 
 * This script creates a simple Express server that listens on port 5000 
 * and forwards requests to the main server on port 8888.
 * 
 * This is necessary because Replit workflows are configured to check port 5000,
 * but our main server is running on port 8888.
 */

import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
const app = express();

// Configuration
const HOST = '0.0.0.0';
const PORT = process.env.SECONDARY_PORT || 5001; // Default to 5001 for the secondary server
const MAIN_SERVER_PORT = process.env.PORT || 8888;
const TARGET = `http://${HOST}:${MAIN_SERVER_PORT}`;

console.log(`Starting secondary server on port ${PORT}...`);
console.log(`Forwarding requests to main server at ${TARGET}`);

// Add a special /ready endpoint for Replit workflows
app.get('/ready', (req, res) => {
  console.log('Ready check received');
  res.status(200).send('Server is ready');
});

// Proxy all requests to the main server
app.use('/', createProxyMiddleware({
  target: TARGET,
  changeOrigin: true,
  ws: true, // Enable WebSocket proxying
  logLevel: 'info',
  pathRewrite: {
    '^/': '/', // No path rewriting needed
  },
  onProxyReq: (proxyReq, req, res) => {
    // Only log non-static requests to reduce noise
    if (!req.url.includes('.') && !req.url.includes('/sockjs-node/')) {
      console.log(`Proxying ${req.method} ${req.url} to ${TARGET}`);
    }
  }
}));

// Start the server
app.listen(PORT, HOST, () => {
  console.log(`Secondary server running at http://${HOST}:${PORT}`);
  console.log(`Forwarding all requests to main server at ${TARGET}`);
});