
#!/usr/bin/env python3
"""Test Web Browser Connection module"""

import os
import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import logging
from connections.webbrowser_connection import WebBrowserConnection

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_browser_connection():
    """Test browser connection functionality"""
    # Check for API key
    api_key = os.getenv('BROWSER_API_KEY')
    if not api_key:
        logger.warning("BROWSER_API_KEY not set. Using sample API key for test.")
        api_key = "sk-7a642a03d4bd69a9b2a541b2102c3c92"  # Sample key from browser_profile_setup.py
    
    # Initialize connection
    config = {
        'api_key': api_key
    }
    browser_conn = WebBrowserConnection(config)
    
    # List profiles
    profiles = browser_conn.list_profiles()
    logger.info(f"Found {len(profiles)} browser profiles")
    
    # Check if SonicKid profile exists
    sonic_profile = None
    for profile in profiles:
        if profile.get('name') == 'SonicKid':
            sonic_profile = profile
            logger.info(f"Found SonicKid profile: {profile}")
            break
    
    if sonic_profile:
        # Create a session
        session = browser_conn.create_session('SonicKid')
        if session:
            session_id = session.get('id')
            logger.info(f"Created session with ID: {session_id}")
            
            # Navigate to a URL
            browser_conn.navigate(session_id, "https://example.com")
            
            # Execute script
            result = browser_conn.execute_script(session_id, "return document.title")
            logger.info(f"Page title: {result}")
            
            logger.info("Browser automation test completed successfully")
            return True
    
    logger.info("Browser automation basic connection test completed")
    return True

if __name__ == "__main__":
    test_browser_connection()
