"""
Base connection class and action types for all connections
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ActionParameter:
    """Parameter definition for an action"""
    name: str
    required: bool
    type: type
    description: str

# Alias for backward compatibility
Parameter = ActionParameter

class Action:
    """Defines an available action and its parameters"""
    def __init__(self, name: str, parameters: List[ActionParameter], description: str):
        self.name = name
        self.parameters = parameters
        self.description = description

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        """Validate provided parameters against defined schema"""
        errors = []

        # Check required parameters
        for param in self.parameters:
            if param.required and param.name not in params:
                errors.append(f"Missing required parameter: {param.name}")
                continue

            if param.name in params:
                value = params[param.name]
                if not isinstance(value, param.type):
                    errors.append(
                        f"Parameter {param.name} has wrong type. Expected {param.type.__name__}, got {type(value).__name__}"
                    )

        # Check for unknown parameters
        param_names = {param.name for param in self.parameters}
        unknown = set(params.keys()) - param_names
        if unknown:
            errors.append(f"Unknown parameters: {', '.join(unknown)}")

        return errors

class BaseConnection:
    """Base class for all connections"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize connection with config"""
        self.config = self.validate_config(config)
        self.actions: Dict[str, Action] = {}
        self.register_actions()

    async def connect(self) -> bool:
        """Initialize the connection"""
        try:
            return True
        except Exception as e:
            logger.error(f"Error connecting: {str(e)}")
            return False

    async def close(self) -> None:
        """Close the connection"""
        pass

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate connection configuration"""
        return config

    def register_actions(self) -> None:
        """Register available actions"""
        pass

    @property
    def is_llm_provider(self) -> bool:
        """Whether this connection provides LLM capabilities"""
        return False

    async def configure(self) -> bool:
        """Configure the connection (e.g. get API keys)"""
        return True

    async def is_configured(self, verbose: bool = False) -> bool:
        """Check if connection is properly configured"""
        return True

    async def perform_action(self, action_name: str, params: Dict[str, Any], **kwargs) -> Any:
        """Execute an action with the given parameters"""
        if action_name not in self.actions:
            raise ValueError(f"Unknown action: {action_name}")

        action = self.actions[action_name]
        errors = action.validate_params(params)
        if errors:
            raise ValueError(f"Invalid parameters: {', '.join(errors)}")

        if not hasattr(self, action_name):
            raise NotImplementedError(f"Action {action_name} not implemented")

        method = getattr(self, action_name)
        return await method(**params)