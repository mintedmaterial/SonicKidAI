#!/usr/bin/env python3
"""Browser automation tasks"""
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent.parent.absolute())
sys.path.insert(0, project_root)

import asyncio
import logging
import json
from typing import Dict, Any
from src.browser_profile_setup import BrowserManager

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class BrowserTasks:
    """Collection of browser automation tasks"""
    _manager = None
    _initialized = False

    @classmethod
    async def initialize(cls):
        """Initialize the browser manager"""
        if not cls._initialized:
            try:
                cls._manager = BrowserManager()
                cls._initialized = True
                logger.info("✅ BrowserManager initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize BrowserManager: {str(e)}")
                raise

    @classmethod
    async def execute_task(cls, task_description: str, timeout: int = 120, save_browser_data=False, wait_for_network_idle=False, override_system_message=None) -> Dict[str, Any]:
        """Execute a browser task"""
        try:
            if not cls._initialized:
                await cls.initialize()

            logger.info(f"Executing browser task...")
            logger.debug(f"Task description: {task_description}")

            result = await cls._manager.execute_task(task_description, timeout=timeout, save_browser_data=save_browser_data, wait_for_network_idle=wait_for_network_idle, override_system_message=override_system_message)
            if not result.get('success'):
                error_msg = result.get('error', 'Unknown error encountered')
                logger.error(f"Task failed: {error_msg}")
                return {"success": False, "error": error_msg}

            logger.info("✅ Task completed successfully")
            return result

        except Exception as e:
            logger.error(f"Error executing browser task: {str(e)}")
            return {"success": False, "error": str(e)}

    @classmethod
    async def shadow_sonic_pools(cls) -> Dict[str, Any]:
        """Get Shadow DEX pools data"""
        task_instructions = (
            "Navigate to https://www.shadow.so/liquidity and follow these steps:\n"
            "1. Wait for the liquidity pools page to load completely\n"
            "2. Look for the available liquidity pools section\n"
            "3. For each pool, collect:\n"
            "   - Pool pair name\n"
            "   - APR percentage\n"
            "   - Total Value Locked (TVL)\n"
            "4. Wait for all pool data to be visible\n"
            "5. Verify the data is loaded and indicate completion"
        )
        return await cls.execute_task(task_instructions, timeout=180)

    @classmethod
    async def metro_sonic_pools(cls) -> Dict[str, Any]:
        """Get Metropolis DEX pools data"""
        task_instructions = (
            "Navigate to https://app.metropolis.exchange/liquidityv3 and follow these steps:\n"
            "1. Wait for the pools page to load completely\n"
            "2. Look for the liquidity pools list\n"
            "3. For each pool, collect:\n"
            "   - Pool pair name\n"
            "   - APR percentage\n"
            "   - Total Value Locked (TVL)\n"
            "4. Wait for all pool data to be visible\n"
            "5. Verify the data is loaded and indicate completion"
        )
        return await cls.execute_task(task_instructions, timeout=180)

    @classmethod
    async def equalizer_sonic_pairs(cls) -> Dict[str, Any]:
        """Get Equalizer DEX pairs data"""
        task_instructions = (
            "Navigate to https://equalizer.exchange/pools and follow these steps:\n"
            "1. Wait for the pools page to load completely\n"
            "2. Look for the trading pairs section\n"
            "3. For each pair, collect:\n"
            "   - Trading pair name\n"
            "   - APR percentage\n"
            "   - Total Value Locked (TVL)\n"
            "4. Wait for all pair data to be visible\n"
            "5. Verify the data is loaded and indicate completion"
        )
        return await cls.execute_task(task_instructions, timeout=180)

    @classmethod
    async def _get_lazybear_prompt(cls) -> str:
        """Generate custom prompt for LazyBear token creation"""
        return """You are a specialized web automation agent for creating tokens on LazyBear.

Key Tasks:
1. Handle wallet connection securely
2. Manage token creation form accurately
3. Monitor transaction confirmation
4. Extract share URL for social media

Critical Elements:
- Wallet connection button/interface
- Form fields for token details
- Transaction confirmation indicators
- Share URL/social sharing elements
- Image upload field and preview

Success Criteria:
1. Token details submitted successfully
2. Transaction confirmed on blockchain
3. Share URL extracted and saved
4. No wallet connection errors
5. Image uploaded and visible

Error Handling:
- Monitor transaction status
- Verify wallet connection
- Validate form submissions
- Confirm image upload success
- Save any error messages

Take deliberate actions and verify completion of each phase."""

    @classmethod
    async def create_token(cls) -> Dict[str, Any]:
        """Create token on Lazy Bear using the provided details"""
        wallet_address = os.getenv('SONIC_WALLET_ADDRESS', '0xCC98d2e64279645D204DD7b25A7c09b6B3ded0d9')
        token_name = os.getenv('LAZYBEAR_TOKEN_NAME', 'BrowserKid')
        token_symbol = os.getenv('LAZYBEAR_TOKEN_SYMBOL', 'KID')
        token_description = os.getenv('LAZYBEAR_TOKEN_DESCRIPTION', 
            'A token launched by Sonic Kid from the SonicLidz Dao project. Testing browser automation capabilities.')
        telegram_url = 'https://t.me/+VcFSmzTH6783MGZh'
        twitter_url = 'https://x.com/BanditKid45'
        initial_buy_amount = os.getenv('LAZYBEAR_INITIAL_BUY', '100')
        image_path = 'attached_assets/SonicLidzRound2.png'

        task_instructions = (
            "Phase 1 - Navigate and Select DEX:\n"
            "1. Navigate to https://lazybear.cc/create\n"
            "2. Wait for page to fully load and network to be idle\n"
            f"3. Connect wallet using address: {wallet_address}\n"
            "4. Select DEX: Shadow from dropdown\n"
            "5. Click 'Next' or continue button\n\n"

            "Phase 2 - Upload Image and Enter Token Details:\n"
            f"6. Upload token image from path: {image_path}\n"
            "7. Wait for upload to complete and verify image preview\n"
            "8. Enter token details:\n"
            f"   - Name: {token_name}\n"
            f"   - Symbol: {token_symbol}\n"
            f"   - Description: {token_description}\n"
            "9. Enter social links:\n"
            f"   - Telegram: {telegram_url}\n"
            f"   - Twitter: {twitter_url}\n"
            f"10. Enter initial buy amount: {initial_buy_amount} $S\n\n"

            "Phase 3 - Verify and Submit:\n"
            "11. Review all entered information\n"
            "12. Check terms and conditions box\n"
            "13. Click 'Create Token!' button\n"
            "14. Wait for transaction to be confirmed on blockchain\n"
            "15. Extract share URL when available\n"
            "16. Save extracted URL for Twitter post\n\n"

            "Phase 4 - Result Validation:\n"
            "17. Verify token creation success:\n"
            "    - Check for token name in success message\n"
            "    - Verify transaction hash is present\n"
            "    - Confirm share URL is valid\n"
            "18. Return task result with share URL"
        )

        return await cls.execute_task(
            task_instructions,
            save_browser_data=True,
            wait_for_network_idle=True,
            timeout=300,  # Extended timeout for blockchain transaction
            override_system_message=cls._get_lazybear_prompt()
        )

    @classmethod
    async def twitter_post_token_launch(cls, share_url: str) -> Dict[str, Any]:
        """Post token launch on Twitter"""
        task_instructions = (
            f"Go to twitter.com/compose/tweet and follow these steps:\n"
            f"1. Wait for the tweet composition page to load\n"
            f"2. Create a new tweet with the following content:\n\n"
            f"🚀 Excited to announce the launch of Sonic Kid ($SONIC)!\n\n"
            f"✨ Fair Launch\n"
            f"💫 Innovative Features\n"
            f"🌟 Strong Community\n\n"
            f"Learn more: {share_url}\n\n"
            f"#SonicKid #DeFi #Crypto\n\n"
            f"3. Verify the tweet content and formatting\n"
            f"4. DO NOT post the tweet - just prepare it\n"
            f"5. Take a screenshot of the prepared tweet\n"
            f"6. Indicate when the tweet is ready for review"
        )
        return await cls.execute_task(task_instructions, timeout=180)

if __name__ == "__main__":
    async def run_tests():
        """Run all browser automation tasks in sequence"""
        try:
            logger.info("\nTesting browser automation...")

            # Test simple navigation
            logger.info("\nTesting basic navigation...")
            await BrowserTasks.initialize()  # Initialize before first use
            test_result = await BrowserTasks.execute_task(
                "Go to google.com, search for Browser Use, and indicate when the search results are visible",
                timeout=120
            )
            logger.info(f"Navigation result: {json.dumps(test_result, indent=2)}")

            if test_result.get('success'):
                # Test token creation
                logger.info("\nTesting token creation...")
                token_result = await BrowserTasks.create_token()
                logger.info(f"Token creation result: {json.dumps(token_result, indent=2)}")

                # Test DEX data collection
                logger.info("\nTesting DEX data collection...")
                shadow_result = await BrowserTasks.shadow_sonic_pools()
                logger.info(f"Shadow DEX result: {json.dumps(shadow_result, indent=2)}")

                metro_result = await BrowserTasks.metro_sonic_pools()
                logger.info(f"Metro DEX result: {json.dumps(metro_result, indent=2)}")

                equalizer_result = await BrowserTasks.equalizer_sonic_pairs()
                logger.info(f"Equalizer result: {json.dumps(equalizer_result, indent=2)}")

                # Test social media post
                logger.info("\nTesting social media post...")
                share_url = "https://example.com/token/sonic-kid"
                post_result = await BrowserTasks.twitter_post_token_launch(share_url)
                logger.info(f"Post result: {json.dumps(post_result, indent=2)}")

            logger.info("\n✅ All tests completed")
            return True

        except Exception as e:
            logger.error(f"❌ Test failed: {str(e)}", exc_info=True)
            return False

    try:
        asyncio.run(run_tests())
    except KeyboardInterrupt:
        logger.info("Test stopped by user")
    except Exception as e:
        logger.error(f"❌ Test runner error: {str(e)}")