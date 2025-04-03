
"""Web Browser Connection module

This module provides browser automation using an external browser API service.
"""

import os
import logging
from typing import Dict, Any, Optional
import requests

from .base_connection import BaseConnection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebBrowserConnection(BaseConnection):
    """Web browser automation using external browser API"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key') or os.getenv('BROWSER_API_KEY')
        self.base_url = config.get('base_url') or "https://api.anchorbrowser.io/api"
        
        if not self.api_key:
            logger.warning("BROWSER_API_KEY not set. Browser automation will be limited.")
        
        self.headers = {
            "anchor-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
    def list_profiles(self):
        """List all available browser profiles"""
        try:
            response = requests.get(
                f"{self.base_url}/profiles",
                headers=self.headers
            )

            if response.status_code == 200:
                profiles = response.json().get('data', [])
                logger.info(f"Found {len(profiles)} profiles")
                return profiles
            else:
                logger.error(f"Failed to list profiles. Status: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error listing profiles: {str(e)}")
            return []

    def create_session(self, profile_name: str):
        """Create a new browser session with a specific profile"""
        session_config = {
            "browser": {
                "name": "chrome",
                "headless": True
            },
            "profile": profile_name
        }

        try:
            response = requests.post(
                f"{self.base_url}/sessions",
                headers=self.headers,
                json=session_config
            )

            if response.status_code == 200:
                logger.info("✅ Session created successfully")
                return response.json()
            else:
                logger.error(f"Failed to create session. Status: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            return None
    
    def navigate(self, session_id: str, url: str):
        """Navigate to a URL in a browser session"""
        try:
            payload = {"url": url}
            response = requests.post(
                f"{self.base_url}/sessions/{session_id}/navigate",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Successfully navigated to {url}")
                return True
            else:
                logger.error(f"Failed to navigate. Status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error navigating: {str(e)}")
            return False
            
    def execute_script(self, session_id: str, script: str):
        """Execute JavaScript in a browser session"""
        try:
            payload = {"script": script}
            response = requests.post(
                f"{self.base_url}/sessions/{session_id}/execute",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                logger.info("✅ Script executed successfully")
                return response.json().get('result')
            else:
                logger.error(f"Failed to execute script. Status: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error executing script: {str(e)}")
            return None
