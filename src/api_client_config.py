"""
API Client Configuration Module

This module provides consistent configuration for API clients connecting to the main application backend.
"""
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def get_api_base_url() -> str:
    """
    Get the base URL for the API based on environment variables
    
    Returns:
        str: The base URL for API requests
    """
    # Check environment variables in order of precedence
    backend_port = os.environ.get("BACKEND_PORT", "5000")
    frontend_port = os.environ.get("FRONTEND_PORT", "3000")
    
    # Determine which port to use - 3000 is the default for the main server
    server_port = frontend_port
    
    # Check if a specific API endpoint is defined
    api_endpoint = os.environ.get("API_BASE_URL")
    if api_endpoint:
        return api_endpoint
    
    # Default to localhost with the server port
    return f"http://localhost:{server_port}"

def get_headers() -> Dict[str, str]:
    """
    Get the default headers for API requests
    
    Returns:
        Dict[str, str]: The default headers
    """
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

def make_api_url(endpoint: str) -> str:
    """
    Create a full API URL by combining the base URL with the endpoint
    
    Args:
        endpoint: The API endpoint path
        
    Returns:
        str: The full API URL
    """
    base_url = get_api_base_url()
    
    # Ensure endpoint starts with / and base_url doesn't end with /
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"
    
    if base_url.endswith("/"):
        base_url = base_url[:-1]
    
    return f"{base_url}{endpoint}"