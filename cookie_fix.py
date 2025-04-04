"""
Cookie Fix Utility

This script helps parse and fix Twitter cookies from environment variables.
"""

import os
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def parse_cookie_string(cookie_str: str) -> List[Dict[str, Any]]:
    """
    Parse cookie string from environment variable
    
    The cookie string is expected to be in a JSON array format like:
    '[{"name":"auth_token","value":"xxx","domain":".twitter.com","path":"/","expires":-1,"httpOnly":true,"secure":true}]'
    
    Args:
        cookie_str: String containing cookie data
        
    Returns:
        List of cookie dictionaries
    """
    try:
        # Clean the string by removing extra quotes that might be causing issues
        cleaned_str = cookie_str.strip()
        
        # If string is surrounded by single quotes, remove them
        if cleaned_str.startswith("'") and cleaned_str.endswith("'"):
            cleaned_str = cleaned_str[1:-1]
            
        # Parse the JSON array
        cookies = json.loads(cleaned_str)
        
        # Return parsed cookies as a list
        if isinstance(cookies, list):
            return cookies
        else:
            logger.error(f"Parsed cookies are not a list: {type(cookies)}")
            return []
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing cookie string: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error parsing cookie string: {e}")
        return []

def get_twitter_cookies() -> List[Dict[str, Any]]:
    """
    Get Twitter cookies from environment variable
    
    Returns:
        List of cookie dictionaries
    """
    # Try to get cookies from environment variable
    cookie_str = os.getenv("TWITTER_COOKIES")
    
    if not cookie_str:
        logger.warning("TWITTER_COOKIES environment variable not found")
        return []
        
    # Parse cookie string
    cookies = parse_cookie_string(cookie_str)
    
    if not cookies:
        # If cookies couldn't be parsed, try to create one from auth token
        auth_token = os.getenv("TWITTER_AUTH_TOKEN")
        if auth_token:
            logger.info("Creating cookie from TWITTER_AUTH_TOKEN")
            return [{
                "name": "auth_token",
                "value": auth_token,
                "domain": ".twitter.com",
                "path": "/",
                "expires": -1,
                "httpOnly": True,
                "secure": True
            }]
        else:
            logger.warning("TWITTER_AUTH_TOKEN environment variable not found")
            return []
            
    return cookies

def save_cookies_to_file(cookies: List[Dict[str, Any]], filename: str = "twitter_cookies.json") -> bool:
    """
    Save cookies to file
    
    Args:
        cookies: List of cookie dictionaries
        filename: Filename to save cookies to
        
    Returns:
        True if cookies were saved successfully, False otherwise
    """
    try:
        with open(filename, "w") as f:
            json.dump(cookies, f, indent=2)
        logger.info(f"Saved {len(cookies)} cookies to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error saving cookies to {filename}: {e}")
        return False

def load_cookies_from_file(filename: str = "twitter_cookies.json") -> List[Dict[str, Any]]:
    """
    Load cookies from file
    
    Args:
        filename: Filename to load cookies from
        
    Returns:
        List of cookie dictionaries
    """
    try:
        if not os.path.exists(filename):
            logger.warning(f"Cookie file {filename} not found")
            return []
            
        with open(filename, "r") as f:
            cookies = json.load(f)
            
        if isinstance(cookies, list):
            logger.info(f"Loaded {len(cookies)} cookies from {filename}")
            return cookies
        else:
            logger.error(f"Loaded cookies are not a list: {type(cookies)}")
            return []
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing cookie file {filename}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error loading cookies from {filename}: {e}")
        return []

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get and print Twitter cookies
    cookies = get_twitter_cookies()
    if cookies:
        print(f"Found {len(cookies)} Twitter cookies:")
        for cookie in cookies:
            print(f"  - {cookie.get('name')}: {cookie.get('value')[:5]}...")
            
        # Save cookies to file
        save_cookies_to_file(cookies)
    else:
        print("No Twitter cookies found")