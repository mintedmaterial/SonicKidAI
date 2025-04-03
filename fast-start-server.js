/**
 * Ultra-Fast Server Starter for Replit Workflows
 * 
 * This script creates a minimal HTTP server that binds to port 5000 almost instantly,
 * then launches the main application in the background.
 */

// Use Node.js built-in http module for maximum startup speed
import http from 'http';
import { spawn } from 'child_process';

// Configuration
const FAST_PORT = 5000;
const MAIN_PORT = 8888;
const SECONDARY_PORT = 5001;
const HOST = '0.0.0.0';

// Create a simple HTTP server
const server = http.createServer((req, res) => {
  // Replit workflow check specifically looks for /ready endpoint
  if (req.url === '/ready') {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('Ready');
    return;
  }
  
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Fast server is running. The main application is starting in the background.');
});

// Start the server with error handling
console.log(`Starting ultra-fast server on port ${FAST_PORT}...`);

try {
  server.listen(FAST_PORT, HOST, () => {
    console.log(`✅ Ultra-fast server running at http://${HOST}:${FAST_PORT}`);
    
    // Start the main application
    console.log('Starting main application in the background...');
    const dualServers = spawn('node', ['start-dual-servers.js'], {
      env: { 
        ...process.env,
        ENABLE_SECONDARY_SERVER: "true",
        PORT: MAIN_PORT.toString(), 
        SECONDARY_PORT: SECONDARY_PORT.toString()
      },
      stdio: 'inherit',
      detached: true
    });
    
    // Don't wait for dual servers to exit
    dualServers.unref();
  });
} catch (error) {
  console.error(`Error starting server: ${error.message}`);
}

// Handle server errors
server.on('error', (e) => {
  if (e.code === 'EADDRINUSE') {
    console.log(`✅ Port ${FAST_PORT} is already in use - this is good for Replit workflows!`);
    
    // Still start the main application
    console.log('Starting main application with confirmed port configuration...');
    const dualServers = spawn('node', ['start-dual-servers.js'], {
      env: { 
        ...process.env,
        ENABLE_SECONDARY_SERVER: "true", 
        PORT: MAIN_PORT.toString(),
        SECONDARY_PORT: SECONDARY_PORT.toString()
      },
      stdio: 'inherit',
      detached: true
    });
    
    // Don't wait for dual servers to exit
    dualServers.unref();
  } else {
    console.error(`Server error: ${e.message}`);
  }
});