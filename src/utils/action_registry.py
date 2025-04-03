"""Action registry implementation"""
import logging
from typing import Callable, Dict

logger = logging.getLogger(__name__)

# Store registered actions
registered_actions: Dict[str, Callable] = {}

def register_action(action_name: str):
    """Decorator to register agent actions"""
    def decorator(func: Callable):
        registered_actions[action_name] = func
        logger.info(f"\n🔄 Registered action: {action_name}")
        return func
    return decorator

def get_registered_actions() -> Dict[str, Callable]:
    """Get all registered actions"""
    return registered_actions
