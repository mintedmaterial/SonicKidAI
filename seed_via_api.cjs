// Simple script to seed the agent actions table via API
const axios = require('axios');

async function seedAgentActions() {
  console.log('Seeding agent actions table with sample data...');
  
  // Define some sample agent types
  const agentTypes = [
    'trading_bot',
    'market_analyzer',
    'sentiment_analyzer',
    'nft_tracker',
    'price_updater'
  ];
  
  // Define some sample action types
  const actionTypes = [
    'fetch_price',
    'analyze_sentiment',
    'generate_alert',
    'execute_trade',
    'update_database',
    'fetch_social_data',
    'generate_report',
    'process_transaction'
  ];
  
  // Define possible statuses
  const statuses = ['success', 'failure', 'pending'];
  
  // Generate some sample error messages
  const errorMessages = [
    'API rate limit exceeded',
    'Network connection timeout',
    'Invalid authentication token',
    'Server returned 500 error',
    'Missing required parameter',
    'Database connection failed',
    'Invalid response format'
  ];
  
  // Helper to get a random item from an array
  const getRandomItem = (array) => array[Math.floor(Math.random() * array.length)];
  
  // Generate and post 50 sample agent actions
  const totalActions = 50;
  let successCount = 0;
  
  for (let i = 0; i < totalActions; i++) {
    const agentType = getRandomItem(agentTypes);
    const actionType = getRandomItem(actionTypes);
    const status = getRandomItem(statuses);
    
    // Generate duration between 50-2000ms for successful actions
    const duration = status === 'success' ? Math.floor(50 + Math.random() * 1950) : null;
    
    // Only add error message for failed actions
    const errorMessage = status === 'failure' ? getRandomItem(errorMessages) : null;
    
    // Generate some sample metadata based on action type
    let metadata = {};
    
    if (actionType === 'fetch_price') {
      metadata = {
        symbol: getRandomItem(['SONIC', 'ETH', 'BTC', 'USDC', 'SOL']),
        source: getRandomItem(['dexscreener', 'coingecko', 'binance', 'coinmarketcap']),
        attempt: Math.floor(Math.random() * 3) + 1
      };
    } else if (actionType === 'analyze_sentiment') {
      metadata = {
        source: getRandomItem(['twitter', 'reddit', 'telegram', 'discord']),
        sample_size: Math.floor(Math.random() * 1000) + 100,
        confidence: parseFloat((Math.random() * 30 + 70).toFixed(2))
      };
    } else if (actionType === 'execute_trade') {
      metadata = {
        pair: getRandomItem(['SONIC/USDC', 'ETH/USDC', 'BTC/USDC', 'SOL/USDC']),
        amount: parseFloat((Math.random() * 1000 + 100).toFixed(2)),
        type: getRandomItem(['swap', 'limit', 'market']),
        slippage: parseFloat((Math.random() * 2).toFixed(2))
      };
    }
    
    const action = {
      agentId: `agent-${Math.floor(Math.random() * 1000)}`,
      agentType,
      actionType,
      status,
      errorMessage,
      duration,
      metadata
    };
    
    try {
      // Post to the agent actions API endpoint
      await axios.post('http://localhost:3000/api/agent/actions', action);
      successCount++;
      process.stdout.write('.');
      
      // Add small delay to avoid overwhelming the server
      await new Promise(resolve => setTimeout(resolve, 100));
    } catch (error) {
      console.error(`Error posting action ${i+1}:`, error.message);
    }
  }
  
  console.log(`\n✅ Successfully added ${successCount}/${totalActions} sample agent actions`);
}

// Run the seed function
seedAgentActions()
  .then(() => {
    console.log('Seed script completed successfully');
    process.exit(0);
  })
  .catch((error) => {
    console.error('Seed script failed:', error);
    process.exit(1);
  });