import { Router, Request, Response, NextFunction } from 'express';
import express from 'express';
import path from 'path';
import fs from 'fs';
import { log } from '../vite';

export const staticRouter = Router();

// Helper to check file existence and log results
const checkAndLogFile = (filePath: string): boolean => {
  const exists = fs.existsSync(filePath);
  log(`Checking path ${filePath}: ${exists ? 'Found' : 'Not found'}`);
  return exists;
};

// Helper to resolve index path based on environment
const resolveIndexPath = (isDev: boolean): string[] => {
  const basePath = path.resolve(__dirname, '../../');
  return isDev ? [
    path.join(basePath, 'client/index.html'),
    path.join(basePath, 'index.html')
  ] : [
    path.join(basePath, 'dist/public/index.html')
  ];
};

// Serve static files in production
if (process.env.NODE_ENV === 'production') {
  const publicDir = path.resolve(__dirname, '../../dist/public');

  if (!checkAndLogFile(publicDir)) {
    log(`[ERROR] Production static directory not found at ${publicDir}`);
    process.exit(1);
  }

  staticRouter.use(express.static(publicDir, {
    maxAge: '1d',
    etag: true,
    lastModified: true
  }));
}

// SPA fallback handler
staticRouter.use('*', (req: Request, res: Response, next: NextFunction) => {
  // Skip API routes
  if (req.path.startsWith('/api')) {
    return next();
  }

  const isDev = process.env.NODE_ENV === 'development';
  log(`[DEBUG] Handling ${isDev ? 'development' : 'production'} route: ${req.path}`);

  // Try each possible index path
  const possiblePaths = resolveIndexPath(isDev);
  for (const indexPath of possiblePaths) {
    if (checkAndLogFile(indexPath)) {
      log(`[DEBUG] Serving index from: ${indexPath}`);
      return res.sendFile(indexPath);
    }
  }

  // No index file found
  const pathsChecked = possiblePaths.join(', ');
  log(`[ERROR] No index.html found. Checked paths: ${pathsChecked}`);
  res.status(404).send('Application entry point not found');
});

export default staticRouter;