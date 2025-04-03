"""SonicKid API Client"""
import requests
import os
from typing import Optional, List, Dict, Any, Union

# Try to import from the api_client_config module, if available
try:
    from src.api_client_config import get_api_base_url
except ImportError:
    # Fallback method if the module isn't available
    def get_api_base_url() -> str:
        """Get the base URL for API requests based on environment variables"""
        api_base_url = os.environ.get("API_BASE_URL")
        if api_base_url:
            return api_base_url
        
        # Check environment variables in order of precedence
        frontend_port = os.environ.get("FRONTEND_PORT", "3000")
        backend_port = os.environ.get("BACKEND_PORT", "5000")
        
        # Default to the frontend port (for the main application)
        server_port = frontend_port
        
        return f"http://localhost:{server_port}"

class SonicKidClient:
    def __init__(self, base_url: Optional[str] = None):
        if base_url is None:
            base_url = get_api_base_url()
        self.base_url = base_url.rstrip('/')

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")

    def get_status(self) -> Dict[str, Any]:
        """Get server status"""
        return self._make_request("GET", "/")

    def list_agents(self) -> List[str]:
        """List available agents"""
        response = self._make_request("GET", "/agents")
        return response.get("agents", [])

    def load_agent(self, agent_name: str) -> Dict[str, Any]:
        """Load a specific agent"""
        return self._make_request("POST", f"/agents/{agent_name}/load")

    def list_connections(self) -> Dict[str, Any]:
        """List available connections"""
        return self._make_request("GET", "/connections")

    def perform_action(self, connection: str, action: str, params: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute an agent action"""
        data = {
            "connection": connection,
            "action": action,
            "params": params or []
        }
        return self._make_request("POST", "/agent/action", json=data)

    def get_market_info(self, query: str) -> Dict[str, Any]:
        """Get market information using natural language query"""
        data = {"query": query}
        return self._make_request("POST", "/api/market/info", json=data)

    def analyze_market(self, query: str) -> Dict[str, Any]:
        """Analyze market conditions using natural language query"""
        data = {"query": query}
        return self._make_request("POST", "/api/market/analyze", json=data)

    def configure_connection(self, connection_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Configure a specific connection"""
        data = {
            "connection": connection_name,
            "params": params
        }
        return self._make_request("POST", f"/connections/{connection_name}/configure", json=data)

    def get_connection_status(self, connection_name: str) -> Dict[str, Any]:
        """Get status of a specific connection"""
        return self._make_request("GET", f"/connections/{connection_name}/status")

    def start_agent(self) -> Dict[str, Any]:
        """Start the agent loop"""
        return self._make_request("POST", "/agent/start")

    def stop_agent(self) -> Dict[str, Any]:
        """Stop the agent loop"""
        return self._make_request("POST", "/agent/stop")

# Keep ZerePyClient as an alias for backward compatibility
ZerePyClient = SonicKidClient