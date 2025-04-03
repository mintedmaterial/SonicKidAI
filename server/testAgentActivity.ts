import { getAgentActivityService } from './services/agentActivityService';
import 'dotenv/config';

async function testAgentActivity() {
  console.log('🧪 Testing Agent Activity Service...');
  
  // Get API keys from environment
  const openaiApiKey = process.env.OPENAI_API_KEY;
  const anthropicApiKey = process.env.OPENROUTER_API_KEY;
  
  console.log('Using API keys:');
  console.log('- OpenAI API Key:', openaiApiKey ? 'Set' : 'Not set');
  console.log('- Anthropic API Key (OpenRouter):', anthropicApiKey ? 'Set' : 'Not set');
  
  // Initialize the service with both keys (prioritizing Anthropic/OpenRouter)
  const agentActivityService = getAgentActivityService({
    openaiApiKey,
    anthropicApiKey,
    postIntervalMinutes: 180 // 3 hours
  });
  
  // Create a test post
  console.log('Creating a test post...');
  const result = await agentActivityService.createAndPostActivity();
  
  if (result) {
    console.log('✅ Test post created successfully');
  } else {
    console.log('❌ Failed to create test post');
  }
  
  // Get recent posts
  const recentPosts = await agentActivityService.getRecentPosts(5);
  console.log(`Recent posts (${recentPosts.length}):`);
  recentPosts.forEach(post => {
    console.log(`- ${post.title}: ${post.content.substring(0, 50)}...`);
  });
  
  process.exit(0);
}

// Run the test
testAgentActivity().catch(error => {
  console.error('Error running test:', error);
  process.exit(1);
});