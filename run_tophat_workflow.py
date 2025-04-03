"""TopHat Updater Workflow Entry Point"""
import asyncio
import logging
import os
import sys
from datetime import datetime

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
    """Run the TopHat updater with proper error handling"""
    try:
        logger.info("🚀 Starting TopHat Knowledge Base Updater...")
        logger.info(f"Current time: {datetime.now().isoformat()}")
        
        # Import the standalone updater to avoid import issues
        from test_tophat_standalone import TopHatUpdater
        
        # Configure update interval
        update_interval = int(os.environ.get("UPDATE_INTERVAL", "7200"))  # Default 2 hours
        test_mode = os.environ.get("TOPHAT_TEST_MODE", "true").lower() == "true"
        
        if test_mode and "UPDATE_INTERVAL" not in os.environ:
            # Use shorter interval in test mode (5 minutes) if not explicitly set
            update_interval = 300
            
        logger.info(f"Running in {'TEST' if test_mode else 'PRODUCTION'} mode with update interval: {update_interval}s")
            
        # Create updater with configured update interval
        updater = TopHatUpdater(test_mode=test_mode, update_interval=update_interval)
        
        # Initialize services
        await updater.initialize_services()
        logger.info("✅ TopHat services initialized")
        
        # Perform initial update immediately
        logger.info("Performing initial knowledge base update...")
        await updater._perform_update()
        logger.info("✅ Initial update completed")
        
        # Keep script running for test demonstration
        max_duration = 3600  # 1 hour maximum runtime
        if test_mode:
            max_duration = 600  # 10 minutes in test mode
            
        logger.info(f"TopHat updater will run for up to {max_duration} seconds")
        
        # Start the update loop but don't wait for it to complete
        asyncio.create_task(updater._update_loop())
        
        # Wait for a maximum duration
        await asyncio.sleep(max_duration)
        
        # Clean shutdown
        logger.info("Maximum runtime reached, shutting down...")
        await updater.stop()
        logger.info("✅ TopHat updater completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error in TopHat updater: {str(e)}", exc_info=True)
        return 1
        
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(run_tophat_updater())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        sys.exit(1)