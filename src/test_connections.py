"""
Test connections for various services to ensure proper configuration

This script provides a minimal test of API connectivity by attempting to connect to
the main server and check its status.
"""
import os
import sys
import logging
import requests
import asyncio
import time
from pathlib import Path
try:
    from dotenv import load_dotenv
except ImportError:
    # Fallback if dotenv is not available
    def load_dotenv():
        """Fallback dummy load_dotenv function"""
        return True

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import API client config
try:
    # Try to access the API client config
    from api_client_config import get_api_base_url, make_api_url, get_headers
except ImportError:
    # Fallback definitions if the module is not available
    def get_api_base_url() -> str:
        """Get the base URL for API requests based on environment variables"""
        api_base_url = os.environ.get("API_BASE_URL")
        if api_base_url:
            return api_base_url

        # Check environment variables in order of precedence
        frontend_port = os.environ.get("FRONTEND_PORT", "3000")

        # Default to the frontend port (for the main application)
        return f"http://0.0.0.0:{frontend_port}" # Updated to 0.0.0.0

    def make_api_url(endpoint: str) -> str:
        """Create a full API URL by combining the base URL with the endpoint"""
        base = get_api_base_url()
        return f"{base}/{endpoint.lstrip('/')}"

    def get_headers() -> dict:
        """Get default headers for API requests"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

async def test_api_connection():
    """Test API connection by checking server status"""
    try:
        # Ensure environment variables are loaded
        load_dotenv()

        # Configure connection parameters
        frontend_port = os.environ.get("FRONTEND_PORT", "3000")
        backend_port = os.environ.get("BACKEND_PORT", "5000")

        # Log configuration
        logger.info(f"Testing API connection with:")
        logger.info(f"- FRONTEND_PORT: {frontend_port}")
        logger.info(f"- BACKEND_PORT: {backend_port}")
        logger.info(f"- API_BASE_URL: {get_api_base_url()}")

        # Try to connect to the server
        url = make_api_url("/api/market/sonic")
        logger.info(f"Attempting to connect to: {url}")

        response = requests.get(url, headers=get_headers(), timeout=10)

        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ API connection successful!")
            logger.info(f"Server responded with data: {data.get('message', 'No message')}")

            # If "sonic" data is available, print price info
            if "data" in data and isinstance(data["data"], dict):
                price = data["data"].get("priceUsd", "N/A")
                chain = data["data"].get("chain", "N/A")
                logger.info(f"Current SONIC price: ${price} on {chain}")

            return True
        else:
            logger.error(f"❌ API connection failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False

    except requests.RequestException as e:
        logger.error(f"❌ API connection failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error during API connection test: {str(e)}")
        return False

async def main():
    """Main function to run connection tests"""
    try:
        # Test API connection
        logger.info("🔄 Starting API connection test...")
        api_success = await test_api_connection()

        if api_success:
            logger.info("✅ All connection tests passed!")
        else:
            logger.error("❌ Some connection tests failed")

    except Exception as e:
        logger.error(f"❌ Error in main: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting connection tests...")

    # Get the root directory
    root_dir = Path(__file__).parent.parent.absolute()

    # Add the root directory to sys.path if not already there
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))

    # Run the main function
    asyncio.run(main())

    # Keep the script running for a while to simulate an active service
    logger.info("Connection tests completed. Keeping service alive for monitoring...")
    try:
        time.sleep(600)  # Run for 10 minutes
    except KeyboardInterrupt:
        logger.info("Service stopped by user")

    logger.info("Connection test service complete")