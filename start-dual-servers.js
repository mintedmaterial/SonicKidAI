/**
 * Dual Server Launcher Script
 * 
 * This script launches both the main application server on port 8888
 * and a secondary proxy server on port 5000 that forwards to the main server.
 * 
 * This is necessary for Replit workflows that expect the server to be on port 5000.
 */

import { spawn } from 'child_process';
import path from 'path';

// Configuration
const HOST = '0.0.0.0';
const MAIN_PORT = process.env.PORT || 8888;
const SECONDARY_PORT = process.env.SECONDARY_PORT || 5000;

// Enable secondary server by default for this script
process.env.ENABLE_SECONDARY_SERVER = "true";

console.log('╔════════════════════════════════════════════════════╗');
console.log('║     Starting Dual Server Configuration...          ║');
console.log('╚════════════════════════════════════════════════════╝');

// Start the main server
console.log(`\n[1/2] Starting main server on port ${MAIN_PORT}...`);
const mainServer = spawn('tsx', ['server/index.ts'], {
  env: { 
    ...process.env,
    PORT: MAIN_PORT.toString(),
    HOST
  },
  stdio: 'inherit'
});

// Give the main server a moment to start
setTimeout(() => {
  // Start the secondary server
  console.log(`\n[2/2] Starting secondary server on port ${SECONDARY_PORT}...`);
  const secondaryServer = spawn('node', ['start-secondary-server.js'], {
    env: {
      ...process.env,
      SECONDARY_PORT: SECONDARY_PORT.toString(),
      PORT: MAIN_PORT.toString(),
      HOST
    },
    stdio: 'inherit'
  });

  // Handle secondary server exit
  secondaryServer.on('exit', (code, signal) => {
    console.log(`Secondary server exited with code ${code} and signal ${signal}`);
    if (mainServer && !mainServer.killed) {
      console.log('Shutting down main server...');
      mainServer.kill();
    }
    process.exit(code || 0);
  });
}, 5000); // Wait 5 seconds before starting secondary server

// Handle main server exit
mainServer.on('exit', (code, signal) => {
  console.log(`Main server exited with code ${code} and signal ${signal}`);
  process.exit(code || 0);
});

// Handle process signals
process.on('SIGINT', () => {
  console.log('Received SIGINT. Shutting down servers...');
  if (mainServer && !mainServer.killed) mainServer.kill();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('Received SIGTERM. Shutting down servers...');
  if (mainServer && !mainServer.killed) mainServer.kill();
  process.exit(0);
});