/**
 * Server Startup Script
 * 
 * This script sets the proper environment variables before starting the server,
 * to ensure consistent port configuration in all environments.
 */

const { spawn } = require('child_process');
const path = require('path');

// Port configuration
const FRONTEND_PORT = process.env.FRONTEND_PORT || 3000;
const BACKEND_PORT = process.env.BACKEND_PORT || 5000;
const BROWSER_API_PORT = process.env.BROWSER_API_PORT || 8000;

// Set environment variables
process.env.FRONTEND_PORT = FRONTEND_PORT.toString();
process.env.BACKEND_PORT = BACKEND_PORT.toString();
process.env.BROWSER_API_PORT = BROWSER_API_PORT.toString();

// Skip secondary server in development mode
process.env.ENABLE_SECONDARY_SERVER = 'false';

console.log('Starting server with the following configuration:');
console.log(`- FRONTEND_PORT: ${process.env.FRONTEND_PORT}`);
console.log(`- BACKEND_PORT: ${process.env.BACKEND_PORT}`);
console.log(`- BROWSER_API_PORT: ${process.env.BROWSER_API_PORT}`);
console.log(`- ENABLE_SECONDARY_SERVER: ${process.env.ENABLE_SECONDARY_SERVER}`);

// Start the npm dev script
const npmProcess = spawn('npm', ['run', 'dev'], {
  env: process.env,
  stdio: 'inherit'
});

// Handle process errors
npmProcess.on('error', (err) => {
  console.error('Failed to start server:', err);
  process.exit(1);
});

// Handle process exit
npmProcess.on('exit', (code) => {
  console.log(`Server process exited with code ${code}`);
  process.exit(code);
});

// Handle signals
process.on('SIGINT', () => {
  console.log('Received SIGINT, shutting down...');
  npmProcess.kill('SIGINT');
});

process.on('SIGTERM', () => {
  console.log('Received SIGTERM, shutting down...');
  npmProcess.kill('SIGTERM');
});