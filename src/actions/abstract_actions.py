"""Actions for interacting with Abstract Protocol"""
import logging
import os
from typing import Optional, Union, Dict, Any
from dotenv import load_dotenv
from src.action_handler import register_action

logger = logging.getLogger("actions.abstract_actions")
load_dotenv()

@register_action("get-abstract-balance")
async def get_balance(agent, **kwargs) -> Dict[str, Any]:
    """Get token balance for Abstract wallet"""
    try:
        token_address = kwargs.get("token_address")

        balance = None
        abstract_wallet = agent.connection_manager.connections["abstract"].abstract_wallet

        if not abstract_wallet:
            logger.error("Abstract wallet not initialized")
            return {
                'success': False,
                'error': 'Wallet not initialized',
                'balance': None
            }

        balance = await abstract_wallet.get_balance(token_address)

        if balance is not None:
            logger.info(f"{'Token' if token_address else 'Native'} Balance: {balance}")
            return {
                'success': True,
                'balance': balance,
                'token_address': token_address
            }
        else:
            logger.error("Failed to get balance")
            return {
                'success': False,
                'error': 'Failed to get balance',
                'balance': None
            }

    except Exception as e:
        logger.error(f"Failed to get balance: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'balance': None
        }

@register_action("transfer-abstract")
async def transfer(agent, **kwargs) -> Dict[str, Any]:
    """Transfer tokens using Abstract wallet"""
    try:
        to_address = kwargs.get("to_address")
        amount = float(kwargs.get("amount", 0))
        token_address = kwargs.get("token_address")

        if not to_address:
            raise ValueError("Recipient address is required")
        if amount <= 0:
            raise ValueError("Amount must be greater than 0")

        abstract_wallet = agent.connection_manager.connections["abstract"].abstract_wallet

        if not abstract_wallet:
            raise ValueError("Abstract wallet not initialized")

        tx_hash = await abstract_wallet.send_transaction(
            to_address=to_address,
            amount=amount,
            token_address=token_address
        )

        if tx_hash:
            logger.info(f"Transferred {amount} {'tokens' if token_address else 'native tokens'} to {to_address}")
            logger.info(f"Transaction hash: {tx_hash}")
            return {
                'success': True,
                'tx_hash': tx_hash,
                'amount': amount,
                'recipient': to_address,
                'token_address': token_address
            }
        else:
            return {
                'success': False,
                'error': 'Transaction failed',
                'tx_hash': None
            }

    except Exception as e:
        logger.error(f"Failed to send tokens: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'tx_hash': None
        }

@register_action("deploy-abstract-token")
async def deploy_token(agent, **kwargs) -> Dict[str, Any]:
    """Deploy a new token on Abstract Protocol"""
    try:
        name = kwargs.get("name")
        symbol = kwargs.get("symbol")
        initial_supply = kwargs.get("initial_supply")
        decimals = kwargs.get("decimals", 18)
        use_agw = kwargs.get("use_agw", False)

        # Validate parameters
        if not name or len(name.strip()) == 0:
            raise ValueError("Token name cannot be empty")
        if not symbol or len(symbol.strip()) == 0:
            raise ValueError("Token symbol cannot be empty")
        if len(symbol) > 5:
            raise ValueError("Token symbol cannot be longer than 5 characters")
        if not initial_supply or float(initial_supply) <= 0:
            raise ValueError("Initial supply must be greater than 0")

        abstract_wallet = agent.connection_manager.connections["abstract"].abstract_wallet

        if not abstract_wallet:
            raise ValueError("Abstract wallet not initialized")

        try:
            initial_supply_wei = float(initial_supply) * (10 ** decimals)
        except ValueError:
            raise ValueError("Invalid initial supply value")

        deployment_args = [name, symbol, int(initial_supply_wei)]

        if use_agw:
            # AGW deployment logic would go here
            # This would integrate with Abstract Gateway for deployment
            tx_hash = "0x"  # Placeholder for AGW deployment
            token_address = "0x"  # Placeholder for AGW deployment
        else:
            # Direct deployment logic
            tx_hash = await abstract_wallet.deploy_token(
                name=name,
                symbol=symbol,
                initial_supply=int(initial_supply_wei),
                decimals=decimals
            )
            # Wait for deployment receipt to get token address
            token_address = await abstract_wallet.get_deployment_address(tx_hash)

        if tx_hash and token_address:
            logger.info(f"Deployed token {symbol} at address {token_address}")
            return {
                'success': True,
                'tx_hash': tx_hash,
                'token_address': token_address,
                'name': name,
                'symbol': symbol,
                'initial_supply': initial_supply,
                'decimals': decimals
            }
        else:
            return {
                'success': False,
                'error': 'Token deployment failed',
                'tx_hash': None,
                'token_address': None
            }

    except Exception as e:
        logger.error(f"Failed to deploy token: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'tx_hash': None,
            'token_address': None
        }