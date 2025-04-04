/**
 * Debug Market Data Access
 * 
 * This script checks access to market data in the database and compares
 * it with the hardcoded values to confirm we're using real data.
 */

require('dotenv').config();
const { Pool } = require('pg');

async function debugMarketData() {
  // Create database connection pool
  const pool = new Pool({
    connectionString: process.env.DATABASE_URL
  });
  
  try {
    console.log('Connecting to database...');
    const client = await pool.connect();
    
    // Check all available tables
    console.log('\n--- DATABASE TABLES ---');
    const tables = await client.query(`
      SELECT table_name
      FROM information_schema.tables
      WHERE table_schema = 'public'
      ORDER BY table_name;
    `);
    
    tables.rows.forEach(row => {
      console.log(`Table: ${row.table_name}`);
    });
    
    // Check market_data table structure
    console.log('\n--- MARKET_DATA TABLE STRUCTURE ---');
    const columns = await client.query(`
      SELECT column_name, data_type
      FROM information_schema.columns
      WHERE table_schema = 'public'
      AND table_name = 'market_data'
      ORDER BY ordinal_position;
    `);
    
    columns.rows.forEach(row => {
      console.log(`Column: ${row.column_name} (${row.data_type})`);
    });
    
    // Check content of market_data table
    console.log('\n--- SONIC MARKET DATA (LATEST 5 RECORDS) ---');
    const marketData = await client.query(`
      SELECT *
      FROM market_data
      WHERE token = 'SONIC'
      ORDER BY timestamp DESC
      LIMIT 5;
    `);
    
    marketData.rows.forEach(row => {
      console.log(JSON.stringify(row, null, 2));
    });
    
    // Check all tokens in the market_data table
    console.log('\n--- ALL TOKENS IN MARKET_DATA ---');
    const tokens = await client.query(`
      SELECT DISTINCT token
      FROM market_data
      ORDER BY token;
    `);
    
    tokens.rows.forEach(row => {
      console.log(`Token: ${row.token}`);
    });
    
    // Compare with hardcoded values
    console.log('\n--- COMPARISON WITH HARDCODED VALUES ---');
    const hardcodedData = {
      price: 1.25,
      price_change_24h: 4.2,
      volume_24h: 1500000,
      updated_at: new Date()
    };
    
    console.log('Hardcoded fallback data:');
    console.log(JSON.stringify(hardcodedData, null, 2));
    
    if (marketData.rows.length > 0) {
      const latestData = marketData.rows[0];
      console.log('\nLatest data from database:');
      console.log(JSON.stringify({
        price: parseFloat(latestData.price),
        price_change_24h: parseFloat(latestData.price_change_24h),
        volume_24h: parseFloat(latestData.volume),
        updated_at: latestData.timestamp
      }, null, 2));
      
      // Calculate if they match
      const priceMatches = parseFloat(latestData.price) === hardcodedData.price;
      const changeMatches = parseFloat(latestData.price_change_24h) === hardcodedData.price_change_24h;
      const volumeMatches = parseFloat(latestData.volume) === hardcodedData.volume_24h;
      
      console.log('\nDo values match?');
      console.log(`Price: ${priceMatches ? 'YES - MATCH' : 'NO - DIFFERENT'}`);
      console.log(`24h Change: ${changeMatches ? 'YES - MATCH' : 'NO - DIFFERENT'}`);
      console.log(`Volume: ${volumeMatches ? 'YES - MATCH' : 'NO - DIFFERENT'}`);
      
      if (priceMatches && changeMatches && volumeMatches) {
        console.log('\n⚠️ WARNING: Hardcoded values exactly match database values!');
        console.log('This coincidence may have led to confusion about where data was coming from.');
      }
    }
    
    // Check other price-related tables
    console.log('\n--- OTHER PRICE-RELATED TABLES ---');
    const priceTables = ['dexscreener_pairs', 'token_prices', 'pair_prices', 'price_feed_data'];
    
    for (const table of priceTables) {
      const tableExists = await client.query(`
        SELECT EXISTS (
          SELECT FROM information_schema.tables 
          WHERE table_schema = 'public' 
          AND table_name = $1
        );
      `, [table]);
      
      if (tableExists.rows[0].exists) {
        console.log(`\nTable ${table} exists, checking data...`);
        
        // Get sample data
        const sampleData = await client.query(`
          SELECT * FROM ${table} 
          LIMIT 1;
        `);
        
        if (sampleData.rows.length > 0) {
          console.log(`Sample data from ${table}:`);
          console.log(JSON.stringify(sampleData.rows[0], null, 2));
        } else {
          console.log(`No data found in ${table}.`);
        }
      } else {
        console.log(`Table ${table} does not exist.`);
      }
    }
    
    // Release client and close pool
    client.release();
    await pool.end();
    
  } catch (error) {
    console.error('Error:', error.message);
    await pool.end();
  }
}

// Run the function
debugMarketData();