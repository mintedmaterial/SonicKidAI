"""
Minimal test for Dune Analytics API using direct requests
"""
import os
import asyncio
import logging
import aiohttp
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def test_dune_api():
    """Test Dune API connectivity with direct requests"""
    # Get API key from environment
    api_key = os.getenv("DUNE_API_KEY")
    
    if not api_key:
        logger.error("❌ No Dune API key found in environment. Set DUNE_API_KEY")
        return False
    
    # Display masked API key for debugging
    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "****"
    logger.info(f"✓ Using Dune API key: {masked_key}")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Try to execute a Dune query - using Shadow DEX query ID
            query_id = 4659701  # Shadow exchange query ID
            url = f"https://api.dune.com/api/v1/query/{query_id}/execute"
            headers = {"x-dune-api-key": api_key}
            
            logger.info(f"📊 Starting query execution for ID: {query_id}...")
            async with session.post(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✓ Query execution started: {result}")
                    
                    # Get execution ID
                    if 'execution_id' in result:
                        execution_id = result['execution_id']
                        logger.info(f"✓ Got execution ID: {execution_id}")
                        
                        # Check execution status
                        status_url = f"https://api.dune.com/api/v1/execution/{execution_id}/status"
                        async with session.get(status_url, headers=headers) as status_response:
                            if status_response.status == 200:
                                status_data = await status_response.json()
                                logger.info(f"✓ Execution status: {status_data}")
                                logger.info("✓ API connection and authentication successful!")
                                return True
                            else:
                                error_text = await status_response.text()
                                logger.error(f"❌ Status API error {status_response.status}: {error_text}")
                    else:
                        logger.error("❌ No execution ID in response")
                else:
                    error_text = await response.text()
                    logger.error(f"❌ API error {response.status}: {error_text}")
    except Exception as e:
        logger.error(f"❌ Error in Dune API test: {str(e)}")
    
    return False

async def main():
    """Run the test"""
    result = await test_dune_api()
    logger.info(f"Test completed with result: {result}")

if __name__ == "__main__":
    asyncio.run(main())