from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Store registered actions
_registered_actions = {}

def register_action(name):
    """Decorator to register an action handler function
    
    Args:
        name (str): Name of the action to register
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
            
        _registered_actions[name] = wrapper
        logger.debug(f"Registered action handler: {name}")
        return wrapper
        
    return decorator

def get_registered_action(name):
    """Get a registered action handler by name
    
    Args:
        name (str): Name of the action to get
        
    Returns:
        function: The registered action handler function
    """
    return _registered_actions.get(name)

def list_registered_actions():
    """List all registered action names
    
    Returns:
        list: List of registered action names
    """
    return list(_registered_actions.keys())

