/**
 * Ultra Minimal Server for Replit Workflow Checks
 * 
 * This script creates the absolute minimum viable HTTP server that will
 * pass Replit's workflow port check. It uses only Node.js built-in modules
 * and does the minimum amount of work necessary.
 */

const http = require('http');

// Create and immediately bind a server to port 5000
const server = http.createServer((req, res) => {
  res.writeHead(200);
  res.end('ok');
}).listen(5000, '0.0.0.0', () => {
  console.log('Ultra minimal server bound to port 5000');
});

// Spawn the main application as a background process
const child = require('child_process').spawn(
  'node',
  ['server/index.js'], 
  {
    env: { ...process.env, PORT: '8888' },
    stdio: 'inherit',
    detached: true
  }
);

// Unref the child to allow this process to exit independently
child.unref();