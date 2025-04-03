"""TopHat Knowledge Base Updater runner"""
import sys
import os
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set environment variables
os.environ["OPENROUTER_API_KEY"] = os.environ.get("OPENROUTER_API_KEY", "")
os.environ["TOPHAT_TEST_MODE"] = "true"

async def main():
    """Run the TopHat updater directly"""
    logger.info("Starting TopHat Knowledge Base Updater...")
    
    # Get environment variables for configuration
    update_interval_env = os.environ.get("UPDATE_INTERVAL")
    test_mode = os.environ.get("TOPHAT_TEST_MODE", "true").lower() == "true"
    
    # Parse update interval if provided
    update_interval = None
    if update_interval_env:
        try:
            update_interval = int(update_interval_env)
            logger.info(f"Using custom update interval from environment: {update_interval} seconds")
        except ValueError:
            logger.error(f"Invalid UPDATE_INTERVAL value: {update_interval_env}, using defaults")
    
    # Run the updater script
    try:
        # Import the standalone version that doesn't have import issues
        from test_tophat_standalone import TopHatUpdater, UPDATE_INTERVAL, TEST_INTERVAL
        
        # Log the default intervals
        logger.info(f"Default intervals - Production: {UPDATE_INTERVAL}s, Test: {TEST_INTERVAL}s")
        
        # Create and run the updater with the specified configuration
        updater = TopHatUpdater(test_mode=test_mode, update_interval=update_interval)
        await updater.start()
        
        # Keep the script running for a set duration
        max_duration = 3600  # 1 hour
        start_time = asyncio.get_event_loop().time()
        
        # Wait until max duration or until the updater stops
        while updater.running:
            await asyncio.sleep(1)
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time >= max_duration:
                logger.info("Maximum run duration reached")
                break
                
        # Ensure clean shutdown
        await updater.stop()
        logger.info("TopHat updater completed successfully")
        
    except Exception as e:
        logger.error(f"Error running TopHat updater: {str(e)}")
        return 1
        
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        sys.exit(1)