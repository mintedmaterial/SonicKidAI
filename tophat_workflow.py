"""TopHat Knowledge Base Updater Workflow Script"""
import asyncio
import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def run_tophat_updater():
    """Run the TopHat updater in a managed workflow"""
    try:
        # Import here to avoid module loading issues
        from test_tophat_standalone import TopHatUpdater
        
        # Set configuration from environment
        update_interval = int(os.environ.get("UPDATE_INTERVAL", "7200"))  # Default 2 hours in seconds
        test_mode = os.environ.get("TOPHAT_TEST_MODE", "true").lower() == "true"
        
        if test_mode:
            logger.info("🧪 Running in TEST mode")
            update_interval = 300  # 5 minutes in test mode
            
        logger.info(f"⏱️ Update interval: {update_interval} seconds")
        
        # Create and initialize the updater
        updater = TopHatUpdater(test_mode=test_mode)
        updater.update_interval = update_interval
        
        # Initialize services
        await updater.initialize_services()
        
        # Start the update process and run for the specified duration
        await updater.start()
        
        # Use a maximum duration to prevent indefinite running in workflow
        max_duration = 28800  # 8 hours
        if test_mode:
            max_duration = 1800  # 30 minutes in test mode
            
        logger.info(f"⏳ Maximum runtime: {max_duration} seconds")
        
        # Sleep while the updater runs in the background
        start_time = asyncio.get_event_loop().time()
        while updater.running:
            await asyncio.sleep(5)
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time >= max_duration:
                logger.info("⌛ Maximum runtime reached")
                break
        
        # Clean shutdown
        await updater.stop()
        logger.info("✅ TopHat updater workflow completed")
        
    except Exception as e:
        logger.error(f"❌ TopHat workflow error: {str(e)}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(run_tophat_updater())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("⚠️ Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Unhandled exception: {str(e)}", exc_info=True)
        sys.exit(1)