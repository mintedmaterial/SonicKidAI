"""Action handler implementation"""
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Callable
from functools import wraps

# Add the src directory to the Python path to enable proper imports
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from utils.action_registry import get_registered_actions
from connections.sonic_connection import SonicConnection
from actions.sonic_actions import SonicActions

logger = logging.getLogger(__name__)

# Store for registered actions
_registered_actions: Dict[str, Callable] = {}

def register_action(action_name: str):
    """Decorator to register an action handler"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        _registered_actions[action_name] = wrapper
        logger.info(f"Registered action handler: {action_name}")
        return wrapper
    return decorator

class ActionHandler:
    """Handles execution of registered actions"""

    def __init__(self):
        """Initialize action handler"""
        self.actions = _registered_actions # Assuming get_registered_actions will return _registered_actions

        # Initialize Sonic connection
        sonic_config = {
            "network": "mainnet",
            "rpc": os.getenv('SONIC_RPC_URL', 'https://mainnet.sonic.ooo/rpc')
        }
        self.connection_manager = {
            "sonic": SonicConnection(sonic_config)
        }

        # Initialize Sonic actions
        self.sonic_actions = SonicActions(self.connection_manager["sonic"])

    async def execute_action(self, action_name: str, **kwargs) -> Any:
        """Execute a registered action"""
        if action_name not in self.actions:
            logger.error(f"Unknown action: {action_name}")
            return None

        try:
            action = self.actions[action_name]
            return await action(self, **kwargs)
        except Exception as e:
            logger.error(f"Action execution failed: {str(e)}")
            return None

# Export the register_action decorator
__all__ = ['register_action', 'ActionHandler']