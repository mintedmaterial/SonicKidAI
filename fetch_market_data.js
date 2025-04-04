
        require('dotenv').config();
        const { Pool } = require('pg');

        async function fetchMarketData() {
          const pool = new Pool({
            connectionString: process.env.DATABASE_URL
          });
          
          try {
            const client = await pool.connect();
            const result = await client.query(`
              SELECT 
                price::float as price,
                price_change_24h::float as price_change_24h,
                volume::float as volume_24h,
                timestamp as updated_at
              FROM market_data
              WHERE token = 'SONIC'
              ORDER BY timestamp DESC
              LIMIT 1
            `);
            
            client.release();
            await pool.end();
            
            if (result.rows.length > 0) {
              const fs = require('fs');
              fs.writeFileSync('market_data_output.json', JSON.stringify(result.rows[0]));
              console.log('Market data fetched successfully');
              return true;
            } else {
              console.log('No market data found');
              return false;
            }
          } catch (error) {
            console.error('Error:', error.message);
            await pool.end();
            return false;
          }
        }

        fetchMarketData();
        