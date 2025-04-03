"""Base class for all services with LLM-friendly interfaces"""
import logging
import os
from typing import Dict, Any, Optional, List, TypeVar, Generic
from datetime import datetime, timezone
import pytz

T = TypeVar('T')

class AbstractService:
    """Base service class providing standardized interfaces for LLM interaction"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        # Set timezone to US Central Standard Time
        self.timezone = pytz.timezone('America/Chicago')

    def format_response(
        self,
        data: Optional[T],
        success: bool = True,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Format service response in a consistent way for LLM consumption"""
        current_time = datetime.now(self.timezone)
        return {
            'success': success and data is not None,
            'data': data,
            'error': error,
            'service': self.__class__.__name__,
            'timestamp': current_time.isoformat()
        }

    def log_error(self, error: Exception, context: str = "") -> None:
        """Standardized error logging"""
        current_time = datetime.now(self.timezone)
        self.logger.error(f"[{current_time.isoformat()}] {context}: {str(error)}")

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate input parameters"""
        required_params = getattr(self, 'REQUIRED_PARAMS', [])
        for param in required_params:
            if param not in kwargs or kwargs[param] is None:
                return False, f"Missing required parameter: {param}"
        return True, None

    def get_current_timestamp(self) -> float:
        """Get current timestamp in US Central timezone"""
        return datetime.now(self.timezone).timestamp()

    async def execute_query(
        self,
        query_type: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute a query based on type and parameters"""
        valid, error = self.validate_params(**kwargs)
        if not valid:
            return self.format_response(None, False, error)

        try:
            # Map query type to method
            method = getattr(self, f"query_{query_type}", None)
            if not method:
                return self.format_response(
                    None,
                    False,
                    f"Unknown query type: {query_type}"
                )

            result = await method(**kwargs)
            return self.format_response(result)

        except Exception as e:
            self.log_error(e, f"Error executing {query_type}")
            return self.format_response(None, False, str(e))

    async def describe_capabilities(self) -> Dict[str, Any]:
        """Return service capabilities for LLM understanding"""
        return {
            'name': self.__class__.__name__,
            'description': self.__doc__,
            'query_types': [
                method[6:] for method in dir(self)
                if method.startswith('query_')
            ],
            'required_params': getattr(self, 'REQUIRED_PARAMS', []),
            'timezone': str(self.timezone)
        }

import os
import logging
from typing import Dict, Any, Optional
import requests
from src.connections.base_connection import BaseConnection

logger = logging.getLogger("services.abstract")

class AbstractTransactionService(AbstractService):
    """Service for handling Abstract protocol transactions using natural language"""

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("ABSTRACT_API_KEY")
        if not self.api_key:
            raise ValueError("Missing ABSTRACT_API_KEY in environment variables")

        self.base_url = os.getenv("ABSTRACT_BASE_URL", "https://agent.api.eternalai.org/api/agent")
        self.agent_id = None  # Will be set after creating or retrieving agent
        self.abstract_address = os.getenv("ABSTRACT_ADDRESS")
        self.abstract_private_key = os.getenv("ABSTRACT_PRIVATE_KEY")

        if not all([self.abstract_address, self.abstract_private_key]):
            raise ValueError("Missing Abstract wallet configuration")

        # Initialize headers
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Setup connection manager
        class ConnectionManager:
            def __init__(self):
                self.connections = {
                    "abstract": BaseConnection({
                        "address": os.getenv("ABSTRACT_ADDRESS"),
                        "private_key": os.getenv("ABSTRACT_PRIVATE_KEY")
                    })
                }

        self.connection_manager = ConnectionManager()

    async def get_agent_info(self, agent_id: str) -> Dict[str, Any]:
        """Get information about an EternalAI agent"""
        try:
            response = requests.get(
                f"{self.base_url}/{agent_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log_error(e, "Failed to get agent info")
            return self.format_response(None, False, f"Failed to get agent info: {str(e)}")

    async def process_command(self, command: str) -> Dict[str, Any]:
        """Process a natural language transaction command"""
        try:
            # Import locally to avoid circular dependencies
            from src.actions.abstract_nlp import parse_transaction_command, execute_nlp_command
            
            # Parse the natural language command
            parsed = parse_transaction_command(command)

            if not parsed.get("success", True):
                return parsed

            # Execute the transaction
            result = await execute_nlp_command(self, command)
            return result

        except Exception as e:
            self.log_error(e, "Failed to process command")
            return self.format_response(None, False, f"Transaction failed: {str(e)}")

    def validate_address(self, address: str) -> bool:
        """Validate an Ethereum address"""
        try:
            # Basic format validation
            if not address.startswith("0x"):
                return False
            if len(address) != 42:  # 0x + 40 hex chars
                return False
            # Check if it contains only valid hex characters after 0x
            int(address[2:], 16)
            return True
        except ValueError:
            return False

    async def get_token_balance(self, token_symbol: str) -> Dict[str, Any]:
        """Get token balance for the configured wallet"""
        try:
            # Using EternalAI agent API to get balance info
            if self.agent_id:
                response = requests.get(
                    f"{self.base_url}/{self.agent_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                data = response.json()
                return self.format_response(
                    {
                        "balance": data["result"]["wallet_balance"],
                        "symbol": token_symbol
                    }
                )
            return self.format_response({"balance": 0, "symbol": token_symbol})
        except Exception as e:
            self.log_error(e, "Failed to get balance")
            return self.format_response(None, False, f"Balance check failed: {str(e)}")