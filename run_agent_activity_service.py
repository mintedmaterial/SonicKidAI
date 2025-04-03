"""
Agent Activity Service Runner

This script runs the Agent Activity Service that posts regular updates to the
dashboard Agent Activity section every 3-4 hours with fresh content.
"""
import os
import asyncio
import signal
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import the Agent Activity Service
from src.services.agent_activity_service import get_agent_activity_service

# Handle graceful shutdown
service = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}. Initiating shutdown...")
    asyncio.create_task(shutdown())

async def shutdown():
    """Perform graceful shutdown"""
    global service
    if service:
        logger.info("Shutting down Agent Activity Service...")
        await service.stop()
        await service.close()
    logger.info("Shutdown complete")

async def run_agent_activity_service():
    """Run the Agent Activity Service"""
    global service
    
    try:
        # Initialize the service
        logger.info("Initializing Agent Activity Service...")
        service = await get_agent_activity_service()
        
        # Start the service
        logger.info("Starting Agent Activity Service...")
        success = await service.start()
        if not success:
            logger.error("Failed to start Agent Activity Service")
            return
        
        # Keep the script running
        logger.info("Agent Activity Service running...")
        while True:
            await asyncio.sleep(60)  # Check every minute for shutdown signals
    except asyncio.CancelledError:
        logger.info("Agent Activity Service cancelled")
    except Exception as e:
        logger.error(f"Error running Agent Activity Service: {str(e)}")
    finally:
        # Cleanup
        if service:
            await service.stop()
            await service.close()
        logger.info("Agent Activity Service stopped")

async def main():
    """Main entry point"""
    try:
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Run the service
        await run_agent_activity_service()
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        await shutdown()

if __name__ == "__main__":
    asyncio.run(main())