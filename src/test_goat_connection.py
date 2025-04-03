"""
Test script for GOAT connection and plugin functionality
"""
import asyncio
import logging
import os
import sys
from dotenv import load_dotenv
sys.path.insert(0, '.')
from src.connections.goat_connection import GoatConnection
from src.constants.networks import SONIC_NETWORKS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_goat():
    """Test GOAT connection and plugins"""
    try:
        logger.info("\n🔧 TESTING GOAT CONNECTION")

        # Debug: Print Python path
        logger.info("Python path:")
        for path in sys.path:
            logger.info(f"- {path}")

        # Use Sonic RPC URL for testing
        sonic_rpc = SONIC_NETWORKS["mainnet"]["rpc_url"]
        logger.info(f"Using RPC URL: {sonic_rpc}")

        # Test configuration
        config = {
            'rpc_url': sonic_rpc,
            'plugins': [
                {
                    'name': 'erc20',
                    'path': 'goat_sdk_plugin_erc20.ERC20Plugin',
                    'args': {
                        'tokens': ['USDC', 'WETH']
                    }
                },
                {
                    'name': 'dexscreener',
                    'path': 'goat_sdk_plugin_dexscreener.DexScreenerPlugin',
                    'args': {}
                },
                {
                    'name': 'jsonrpc',
                    'path': 'goat_sdk_plugin_jsonrpc.JSONRPCPlugin',
                    'args': {
                        'rpc_url': sonic_rpc
                    }
                }
            ]
        }

        # Initialize connection
        goat = GoatConnection(config)
        logger.info("✅ GOAT connection initialized")

        # Test plugin loading
        logger.info("\nLoaded plugins:")
        for name, plugin in goat.plugins.items():
            logger.info(f"- {name}: {plugin.__class__.__name__}")

        # Test available actions
        logger.info("\nAvailable actions:")
        for name, action in goat.actions.items():
            logger.info(f"- {name}: {action.description}")

        # Test balance check
        balance = await goat.get_balance()
        logger.info(f"\nNative token balance: {balance}")

        # Test token info using DexScreener
        if 'dexscreener' in goat.plugins:
            weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # WETH
            token_info = await goat.get_token_info(weth_address)
            logger.info(f"\nWETH token info from DexScreener: {token_info}")

        logger.info("\n✅ GOAT connection tests completed successfully!")
        return True

    except Exception as e:
        logger.error(f"❌ GOAT connection test failed: {str(e)}")
        return False

if __name__ == "__main__":
    load_dotenv()
    success = asyncio.run(test_goat())
    exit(0 if success else 1)