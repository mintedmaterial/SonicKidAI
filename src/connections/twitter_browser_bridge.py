"""Bridge between Anthropic Agent and Browser for Twitter actions"""
import logging
import re
from typing import Dict, Any, Optional, List
from .browser_api_connection import BrowserAPIConnection

logger = logging.getLogger(__name__)

class TwitterBrowserBridge:
    """Bridge to forward Twitter actions from AI agent to browser automation"""
    MAX_RETRIES = 3
    MAX_TWEET_LENGTH = 280

    def __init__(self, browser_connection: BrowserAPIConnection):
        self.browser = browser_connection

    def _validate_tweet_text(self, text: str) -> bool:
        """Validate tweet text length and content"""
        if not text or len(text) > self.MAX_TWEET_LENGTH:
            return False
        # Basic URL validation
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
        for url in urls:
            if len(url) > 23:  # Twitter's t.co wrapping
                text = text.replace(url, "x" * 23)
        return len(text) <= self.MAX_TWEET_LENGTH

    async def post_tweet(self, text: str, media_urls: Optional[list] = None) -> Dict[str, Any]:
        """Create a browser task to post a tweet with retry logic"""
        if not self._validate_tweet_text(text):
            return {'success': False, 'message': 'Invalid tweet text length or format'}

        for attempt in range(self.MAX_RETRIES):
            try:
                task_instructions = [
                    "1. Verify already logged into Twitter",
                    "2. Click 'Post' or 'Tweet' button to open compose dialog",
                    "3. Wait for tweet composer to fully load",
                    f"4. Enter the following text: {text}"
                ]

                if media_urls:
                    task_instructions.extend([
                        "5. Click media upload button",
                        f"6. Upload the following media files: {', '.join(media_urls)}",
                        "7. Wait for all media to finish uploading",
                        "8. Verify media preview is visible"
                    ])

                task_instructions.extend([
                    "9. Click the 'Post' or 'Tweet' button",
                    "10. Wait for confirmation that tweet was posted",
                    "11. Verify tweet appears in timeline"
                ])

                result = await self.browser.perform_action(
                    "run_task",
                    {
                        "task": "\n".join(task_instructions),
                        "save_browser_data": True,
                        "wait_for_network_idle": True,
                        "timeout": 120
                    }
                )

                if result and result.get('status') == 'finished':
                    logger.info("Successfully posted tweet")
                    return {'success': True, 'message': 'Tweet posted successfully'}

                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"Tweet posting attempt {attempt + 1} failed, retrying...")
                    continue

            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    logger.error(f"Error posting tweet (attempt {attempt + 1}): {e}")
                    continue
                return {'success': False, 'message': f'Error posting tweet: {str(e)}'}

        error_msg = result.get('message') if result else 'Unknown error'
        logger.error(f"Failed to post tweet after {self.MAX_RETRIES} attempts: {error_msg}")
        return {'success': False, 'message': f'Failed to post tweet: {error_msg}'}

    async def retweet(self, tweet_url: str) -> Dict[str, Any]:
        """Create a browser task to retweet with retry logic"""
        for attempt in range(self.MAX_RETRIES):
            try:
                task_instructions = [
                    f"1. Navigate to tweet URL: {tweet_url}",
                    "2. Wait for tweet to load",
                    "3. Look for retweet button (usually has aria-label='Retweet')",
                    "4. Click retweet button",
                    "5. Click 'Retweet' in the confirmation dialog",
                    "6. Verify retweet confirmation"
                ]

                result = await self.browser.perform_action(
                    "run_task",
                    {
                        "task": "\n".join(task_instructions),
                        "save_browser_data": True,
                        "wait_for_network_idle": True,
                        "timeout": 60
                    }
                )

                if result and result.get('status') == 'finished':
                    logger.info("Successfully retweeted")
                    return {'success': True, 'message': 'Retweeted successfully'}

                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"Retweet attempt {attempt + 1} failed, retrying...")
                    continue

            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    logger.error(f"Error retweeting (attempt {attempt + 1}): {e}")
                    continue
                return {'success': False, 'message': f'Error retweeting: {str(e)}'}

        error_msg = result.get('message') if result else 'Unknown error'
        logger.error(f"Failed to retweet after {self.MAX_RETRIES} attempts: {error_msg}")
        return {'success': False, 'message': f'Failed to retweet: {error_msg}'}

    async def verify_logged_in(self) -> bool:
        """Verify Twitter login status with retry logic"""
        for attempt in range(self.MAX_RETRIES):
            try:
                task_instructions = [
                    "1. Navigate to Twitter home page",
                    "2. Wait for page to load",
                    "3. Look for elements that indicate logged-in state:",
                    "   - Tweet compose button",
                    "   - Profile menu",
                    "   - Home timeline",
                    "4. Return verification result"
                ]

                result = await self.browser.perform_action(
                    "run_task",
                    {
                        "task": "\n".join(task_instructions),
                        "save_browser_data": True,
                        "wait_for_network_idle": True,
                        "timeout": 60
                    }
                )

                if result and result.get('status') == 'finished':
                    return True

                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"Login verification attempt {attempt + 1} failed, retrying...")
                    continue

            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    logger.error(f"Error verifying login (attempt {attempt + 1}): {e}")
                    continue
                logger.error(f"Failed to verify login status: {e}")
                return False

        return False

    async def like_tweet(self, tweet_url: str) -> Dict[str, Any]:
        """Create a browser task to like a tweet with retry logic"""
        for attempt in range(self.MAX_RETRIES):
            try:
                task_instructions = [
                    f"1. Navigate to tweet URL: {tweet_url}",
                    "2. Wait for tweet to load",
                    "3. Look for like button (usually has aria-label='Like')",
                    "4. Click like button",
                    "5. Verify like action was successful"
                ]

                result = await self.browser.perform_action(
                    "run_task",
                    {
                        "task": "\n".join(task_instructions),
                        "save_browser_data": True,
                        "wait_for_network_idle": True,
                        "timeout": 60
                    }
                )

                if result and result.get('status') == 'finished':
                    logger.info("Successfully liked tweet")
                    return {'success': True, 'message': 'Tweet liked successfully'}

                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"Like attempt {attempt + 1} failed, retrying...")
                    continue

            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    logger.error(f"Error liking tweet (attempt {attempt + 1}): {e}")
                    continue
                return {'success': False, 'message': f'Error liking tweet: {str(e)}'}

        error_msg = result.get('message') if result else 'Unknown error'
        logger.error(f"Failed to like tweet after {self.MAX_RETRIES} attempts: {error_msg}")
        return {'success': False, 'message': f'Failed to like tweet: {error_msg}'}