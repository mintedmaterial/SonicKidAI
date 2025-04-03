// Script to add sample agent actions for testing the Agent Monitoring dashboard
const { db } = require('./server/db');
const { agentActions } = require('./shared/schema');

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
  
  // Helper to generate a random date within the last week
  const getRandomDate = () => {
    const now = new Date();
    const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    return new Date(oneWeekAgo.getTime() + Math.random() * (now.getTime() - oneWeekAgo.getTime()));
  };
  
  // Helper to get a random item from an array
  const getRandomItem = (array) => array[Math.floor(Math.random() * array.length)];
  
  // Generate 50 sample agent actions
  const sampleActions = [];
  
  for (let i = 0; i < 50; i++) {
    const agentType = getRandomItem(agentTypes);
    const actionType = getRandomItem(actionTypes);
    const status = getRandomItem(statuses);
    const createdAt = getRandomDate();
    
    // Generate duration between 50-2000ms for successful actions
    const duration = status === 'success' ? 50 + Math.random() * 1950 : null;
    
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
        confidence: (Math.random() * 30 + 70).toFixed(2)
      };
    } else if (actionType === 'execute_trade') {
      metadata = {
        pair: getRandomItem(['SONIC/USDC', 'ETH/USDC', 'BTC/USDC', 'SOL/USDC']),
        amount: (Math.random() * 1000 + 100).toFixed(2),
        type: getRandomItem(['swap', 'limit', 'market']),
        slippage: (Math.random() * 2).toFixed(2)
      };
    }
    
    sampleActions.push({
      agentId: `agent-${Math.floor(Math.random() * 1000)}`,
      agentType,
      actionType,
      status,
      errorMessage,
      duration,
      metadata,
      createdAt
    });
  }
  
  // Batch insert all actions
  try {
    const result = await db.insert(agentActions).values(sampleActions);
    console.log(`✅ Successfully added ${sampleActions.length} sample agent actions`);
    return result;
  } catch (error) {
    console.error('❌ Error seeding agent actions:', error);
    throw error;
  }
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