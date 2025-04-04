/**
 * Check Token Prices
 * 
 * This script checks if we have SONIC token price data in the database.
 */

require('dotenv').config();
const { Pool } = require('pg');

async function checkTokenPrices() {
  const pool = new Pool({
    connectionString: process.env.DATABASE_URL
  });
  
  try {
    console.log('Connecting to database...');
    const client = await pool.connect();
    
    // First, let's check if the token_prices table exists
    console.log('Checking if token_prices table exists...');
    const tableCheck = await client.query(`
      SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'token_prices'
      );
    `);
    
    const tableExists = tableCheck.rows[0].exists;
    
    if (!tableExists) {
      console.log('token_prices table does not exist. Checking for other price tables...');
      
      // Check for other tables that might contain price data
      const tableList = await client.query(`
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE '%price%' OR table_name LIKE '%token%' OR table_name LIKE '%pair%';
      `);
      
      console.log('Found tables that might contain price data:');
      tableList.rows.forEach(row => {
        console.log(`- ${row.table_name}`);
      });
      
      // If no token_prices table, exit
      if (tableList.rows.length === 0) {
        console.log('No price-related tables found in the database.');
        await client.release();
        await pool.end();
        return;
      }
    }
    
    // If token_prices exists, check for SONIC data
    if (tableExists) {
      console.log('Looking for SONIC price data...');
      
      // Get table structure
      const tableStructure = await client.query(`
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'token_prices';
      `);
      
      console.log('token_prices table structure:');
      tableStructure.rows.forEach(row => {
        console.log(`- ${row.column_name}: ${row.data_type}`);
      });
      
      // Query for SONIC data
      const result = await client.query(`
        SELECT * FROM token_prices 
        WHERE token_symbol = 'SONIC' 
        ORDER BY updated_at DESC 
        LIMIT 5;
      `);
      
      if (result.rows.length > 0) {
        console.log(`Found ${result.rows.length} SONIC price entries.`);
        console.log('Latest SONIC price data:');
        console.log(result.rows[0]);
      } else {
        console.log('No SONIC price data found in token_prices table.');
        
        // Check what token symbols exist
        const symbols = await client.query(`
          SELECT DISTINCT token_symbol 
          FROM token_prices 
          LIMIT 10;
        `);
        
        if (symbols.rows.length > 0) {
          console.log('Available token symbols:');
          symbols.rows.forEach(row => {
            console.log(`- ${row.token_symbol}`);
          });
        } else {
          console.log('No token symbols found in the table.');
        }
      }
    }
    
    // Check for other price tables
    const otherPriceTables = ['dexscreener_pairs', 'pair_prices', 'market_data'];
    
    for (const table of otherPriceTables) {
      try {
        const exists = await client.query(`
          SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = $1
          );
        `, [table]);
        
        if (exists.rows[0].exists) {
          console.log(`\nFound table: ${table}`);
          
          // Get sample data
          const sampleData = await client.query(`
            SELECT * FROM ${table} 
            LIMIT 1;
          `);
          
          if (sampleData.rows.length > 0) {
            console.log(`Sample data from ${table}:`);
            console.log(sampleData.rows[0]);
          } else {
            console.log(`No data found in ${table}.`);
          }
        }
      } catch (err) {
        console.log(`Error checking table ${table}:`, err.message);
      }
    }
    
    client.release();
    await pool.end();
    
  } catch (error) {
    console.error('Error:', error.message);
    await pool.end();
  }
}

checkTokenPrices();