"""Registry for message handling endpoints"""
import logging
from typing import Dict, Any, Optional, List, Callable, Awaitable
from enum import Enum, auto

logger = logging.getLogger(__name__)

class EndpointType(Enum):
    """Types of endpoints for message routing"""
    COMMAND = auto()
    REGEX = auto()
    PREFIX = auto()
    HANDLER = auto()

class EndpointRegistry:
    """Registry for managing message handling endpoints"""
    
    def __init__(self):
        """Initialize endpoint registry"""
        self._command_handlers: Dict[str, Callable[..., Awaitable[Any]]] = {}
        self._regex_handlers: Dict[str, Callable[..., Awaitable[Any]]] = {}
        self._prefix_handlers: Dict[str, Callable[..., Awaitable[Any]]] = {}
        self._general_handlers: List[Callable[..., Awaitable[Any]]] = []
        
    def register_command(self, command: str, handler: Callable[..., Awaitable[Any]]) -> None:
        """Register a command handler"""
        self._command_handlers[command.lower()] = handler
        logger.debug(f"Registered command handler for /{command}")
        
    def register_regex(self, pattern: str, handler: Callable[..., Awaitable[Any]]) -> None:
        """Register a regex pattern handler"""
        self._regex_handlers[pattern] = handler
        logger.debug(f"Registered regex handler for pattern: {pattern}")
        
    def register_prefix(self, prefix: str, handler: Callable[..., Awaitable[Any]]) -> None:
        """Register a prefix handler"""
        self._prefix_handlers[prefix.lower()] = handler
        logger.debug(f"Registered prefix handler for: {prefix}")
        
    def register_handler(self, handler: Callable[..., Awaitable[Any]]) -> None:
        """Register a general message handler"""
        self._general_handlers.append(handler)
        logger.debug("Registered general message handler")
        
    def get_command_handler(self, command: str) -> Optional[Callable[..., Awaitable[Any]]]:
        """Get handler for a specific command"""
        return self._command_handlers.get(command.lower())
        
    def get_regex_handler(self, pattern: str) -> Optional[Callable[..., Awaitable[Any]]]:
        """Get handler for a specific regex pattern"""
        return self._regex_handlers.get(pattern)
        
    def get_prefix_handler(self, prefix: str) -> Optional[Callable[..., Awaitable[Any]]]:
        """Get handler for a specific prefix"""
        return self._prefix_handlers.get(prefix.lower())
        
    def get_general_handlers(self) -> List[Callable[..., Awaitable[Any]]]:
        """Get all general message handlers"""
        return self._general_handlers
        
    def list_endpoints(self) -> Dict[str, Dict[str, Any]]:
        """List all registered endpoints"""
        return {
            "commands": [{"command": cmd, "handler": handler.__name__} 
                        for cmd, handler in self._command_handlers.items()],
            "regex": [{"pattern": pattern, "handler": handler.__name__} 
                     for pattern, handler in self._regex_handlers.items()],
            "prefix": [{"prefix": prefix, "handler": handler.__name__} 
                      for prefix, handler in self._prefix_handlers.items()],
            "general": [{"handler": handler.__name__} 
                       for handler in self._general_handlers]
        }