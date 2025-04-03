import { Pool, neonConfig } from '@neondatabase/serverless';
import { drizzle } from 'drizzle-orm/neon-serverless';
import ws from "ws";
import * as schema from "@shared/schema";

neonConfig.webSocketConstructor = ws;

// Configure optimal pool settings
const POOL_CONFIG = {
  connectionTimeoutMillis: 30000, // 30 seconds
  idleTimeoutMillis: 60000,      // 1 minute
  max: 20,                       // Maximum pool size
  connectionRetryAttempts: 3     // Number of connection retry attempts
};

if (!process.env.DATABASE_URL) {
  throw new Error(
    "DATABASE_URL must be set. Did you forget to provision a database?",
  );
}

// Create connection pool with optimized settings
export const pool = new Pool({ 
  connectionString: process.env.DATABASE_URL,
  ...POOL_CONFIG
});

// Add error handling for the pool
pool.on('error', (err, client) => {
  console.error('Unexpected error on idle client', err);
});

// Initialize Drizzle with the pool
export const db = drizzle({ client: pool, schema });

// Handle process termination
process.on('SIGTERM', async () => {
  console.log('Closing pool connections...');
  await pool.end();
});