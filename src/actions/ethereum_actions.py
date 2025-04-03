import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the src directory to the Python path to enable proper imports
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Use local action_handler
from action_handler import register_action

logger = logging.getLogger("actions.ethereum_actions")

@register_action("get-token-by-ticker")
async def get_token_by_ticker(agent, **kwargs):
    """Get token address by ticker symbol"""
    try:
        ticker = kwargs.get("ticker")
        if not ticker:
            logger.error("No ticker provided")
            return None

        token_address = await agent.connection_manager.connections["ethereum"].get_token_by_ticker(ticker)

        if token_address:
            logger.info(f"Found token address for {ticker}: {token_address}")
        else:
            logger.info(f"No token found for ticker {ticker}")

        return token_address

    except Exception as e:
        logger.error(f"Failed to get token by ticker: {str(e)}")
        return None

@register_action("get-eth-balance")
async def get_eth_balance(agent, **kwargs):
    """Get native or token balance"""
    try:
        token_address = kwargs.get("token_address")

        load_dotenv()
        private_key = os.getenv('ETH_PRIVATE_KEY')
        web3 = agent.connection_manager.connections["ethereum"]._web3
        account = web3.eth.account.from_key(private_key)
        address = account.address

        balance = await agent.connection_manager.connections["ethereum"].get_balance(
            address=address,
            token_address=token_address
        )

        if token_address:
            logger.info(f"Token Balance: {balance}")
        else:
            logger.info(f"Native Token Balance: {balance}")

        return balance

    except Exception as e:
        logger.error(f"Failed to get balance: {str(e)}")
        return None

@register_action("send-eth")
async def send_eth(agent, **kwargs):
    """Send native tokens to an address"""
    try:
        to_address = kwargs.get("to_address")
        amount = float(kwargs.get("amount", 0))

        tx_url = await agent.connection_manager.connections["ethereum"].transfer(
            to_address=to_address,
            amount=amount
        )

        logger.info(f"Transferred {amount} native ETH tokens to {to_address}")
        logger.info(f"Transaction URL: {tx_url}")
        return tx_url

    except Exception as e:
        logger.error(f"Failed to send native tokens: {str(e)}")
        return None

@register_action("send-eth-token")
async def send_eth_token(agent, **kwargs):
    """Send ERC20 tokens"""
    try:
        to_address = kwargs.get("to_address")
        token_address = kwargs.get("token_address")
        amount = float(kwargs.get("amount", 0))

        tx_url = await agent.connection_manager.connections["ethereum"].transfer(
            to_address=to_address,
            amount=amount,
            token_address=token_address
        )

        logger.info(f"Transferred {amount} tokens to {to_address}")
        logger.info(f"Transaction URL: {tx_url}")
        return tx_url

    except Exception as e:
        logger.error(f"Failed to send tokens: {str(e)}")
        return None

@register_action("get-address")
async def get_address(agent, **kwargs):
    """Get configured Ethereum wallet address"""
    try:
        return await agent.connection_manager.connections["ethereum"].get_address()
    except Exception as e:
        logger.error(f"Failed to get address: {str(e)}")
        return None