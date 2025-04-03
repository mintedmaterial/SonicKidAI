"""
Initializers package for automatically starting services when imported
"""
# Import initializers to auto-start them when the package is imported
try:
    # Import price updater
    from .price_updater import start_background_updater, stop_background_updater
    
    # Import cache service initializer
    from .cache_service_initializer import initialize as initialize_cache, shutdown as shutdown_cache
    
    # Note: Cache service will be initialized when needed
    # We don't initialize it here to avoid "no running event loop" errors
    
    # These functions are exported for manual control if needed
    __all__ = [
        'start_background_updater', 
        'stop_background_updater',
        'initialize_cache',
        'shutdown_cache'
    ]
except ImportError as e:
    print(f"Failed to import initializers: {str(e)}")