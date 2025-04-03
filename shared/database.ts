/**
 * Database connection utilities for the application
 */

import pg from 'pg';
const { Pool } = pg;

// Create a singleton database pool that can be reused across the application
let pool: pg.Pool | null = null;

/**
 * Get a database pool instance
 * @returns PostgreSQL connection pool
 */
export function getPool(): pg.Pool {
  if (!pool) {
    // Create a new pool if one doesn't exist
    pool = new Pool({
      connectionString: process.env.DATABASE_URL,
      // Only use SSL in production environments
      ssl: process.env.NODE_ENV === 'production' ? 
        { rejectUnauthorized: false } : undefined
    });

    // Log pool creation
    console.log('Created new database connection pool');

    // Set up error handling for the pool
    pool.on('error', (err) => {
      console.error('Unexpected error on idle database client', err);
    });
  }
  
  return pool;
}

/**
 * Run a database query using the connection pool
 * @param text SQL query text
 * @param params Query parameters
 * @returns Query result
 */
export async function query(text: string, params: any[] = []): Promise<pg.QueryResult> {
  const pool = getPool();
  try {
    const result = await pool.query(text, params);
    return result;
  } catch (error) {
    console.error('Database query error:', error);
    throw error;
  }
}

/**
 * Close the database pool
 * Should be called when shutting down the application
 */
export async function closePool(): Promise<void> {
  if (pool) {
    await pool.end();
    pool = null;
    console.log('Database connection pool closed');
  }
}

/**
 * Get the latest SONIC price from the database
 * @returns Price data with source and timestamp
 */
export async function getLatestSonicPrice(): Promise<{ price: number, timestamp: number, source: string } | null> {
  try {
    // Try from sonic_price_feed first (newest table)
    let queryText = `
      SELECT price, timestamp, 'dexscreener' as source
      FROM sonic_price_feed
      WHERE 
        base_token = 'SONIC' OR 
        base_token = 'wSONIC' OR 
        quote_token = 'SONIC' OR 
        quote_token = 'wSONIC' OR 
        pair_symbol LIKE '%SONIC%'
      ORDER BY timestamp DESC
      LIMIT 1
    `;
    
    let result = await query(queryText);
    
    // If no results, try from crypto_data table (older table)
    if (!result.rows || result.rows.length === 0) {
      console.log('No SONIC price found in sonic_price_feed, trying crypto_data table...');
      
      queryText = `
        SELECT price, timestamp, 'dexscreener' as source
        FROM crypto_data
        WHERE token_symbol = 'SONIC' OR token_symbol = 'wSONIC'
        ORDER BY timestamp DESC
        LIMIT 1
      `;
      
      result = await query(queryText);
    }
    
    if (result.rows && result.rows.length > 0) {
      const row = result.rows[0];
      console.log(`✅ Found SONIC price in database: $${row.price}`);
      
      return {
        price: parseFloat(row.price),
        timestamp: new Date(row.timestamp).getTime(),
        source: row.source || 'database'
      };
    }
    
    console.log('⚠️ No SONIC price found in database');
    return null;
  } catch (error) {
    console.error('Error fetching SONIC price from database:', error);
    return null;
  }
}