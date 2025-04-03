"""
Main application entry point that initializes all services
"""
import logging
import asyncio
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import initializers
from src.initializers.price_updater import start_background_updater
from src.initializers.cache_service_initializer import initialize as initialize_cache

# Import services
from src.services.cached_market_data_service import get_cached_market_data_service

async def initialize_services():
    """Initialize all application services"""
    logger.info("🚀 Initializing application services...")
    
    # Start price updater
    start_background_updater()
    logger.info("✅ Price updater started")
    
    # Initialize cache service
    await initialize_cache()
    logger.info("✅ Cache service initialized")
    
    # Initialize cached market data service
    market_service = await get_cached_market_data_service()
    logger.info("✅ Market data service initialized with caching")
    
    logger.info("✅ All services initialized successfully")
    return True

async def shutdown_services():
    """Shutdown all application services gracefully"""
    from src.initializers.price_updater import stop_background_updater
    from src.initializers.cache_service_initializer import shutdown as shutdown_cache
    from src.services.cached_market_data_service import cached_market_data_service
    
    logger.info("🛑 Shutting down application services...")
    
    # Stop background price updater
    stop_background_updater()
    logger.info("✅ Price updater stopped")
    
    # Shutdown cache service
    await shutdown_cache()
    logger.info("✅ Cache service shutdown")
    
    # Close market data service
    if cached_market_data_service:
        await cached_market_data_service.close()
        logger.info("✅ Market data service closed")
    
    logger.info("✅ All services shutdown successfully")
    return True

async def main():
    """Main application entry point"""
    try:
        # Initialize services
        await initialize_services()
        
        # Keep application running
        logger.info("Application running. Press Ctrl+C to exit.")
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Error in main application: {str(e)}")
    finally:
        # Clean shutdown
        await shutdown_services()
        logger.info("Application shutdown complete.")

if __name__ == "__main__":
    # Entry point when script is run directly
    asyncio.run(main())