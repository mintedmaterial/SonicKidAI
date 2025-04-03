// Absolute minimum server to pass Replit workflow check
require('http').createServer((_, res) => { 
  res.end('ok');
}).listen(5000);