import logging
import os
from dotenv import load_dotenv
from src.action_handler import register_action
from typing import Dict, Any, Optional

logger = logging.getLogger("actions.sonic_actions")

@register_action("get-token-list")
def get_token_list(agent, **kwargs):
    """Get list of supported tokens on specified chain
    """
    try:
        chain = kwargs.get("chain")
        if not chain:
            logger.error("No chain specified")
            return None
            
        return agent.connection_manager.connections["sonic"].get_token_list(chain)

    except Exception as e:
        logger.error(f"Failed to get token list: {str(e)}")
        return None

@register_action("get-gas-price")
def get_gas_price(agent, **kwargs):
    """Get current gas price on specified chain
    """
    try:
        chain = kwargs.get("chain")
        if not chain:
            logger.error("No chain specified")
            return None
            
        return agent.connection_manager.connections["sonic"].get_gas_price(chain)

    except Exception as e:
        logger.error(f"Failed to get gas price: {str(e)}")
        return None

@register_action("get-token-info")
def get_token_info(agent, **kwargs):
    """Get detailed token information
    """
    try:
        chain = kwargs.get("chain")
        token_address = kwargs.get("token_address")
        if not chain or not token_address:
            logger.error("Chain or token address not specified")
            return None
            
        return agent.connection_manager.connections["sonic"].get_token_info(
            chain=chain,
            token_address=token_address
        )

    except Exception as e:
        logger.error(f"Failed to get token info: {str(e)}")
        return None

@register_action("get-quote")
def get_quote(agent, **kwargs):
    """Get swap quote for tokens
    """
    try:
        chain = kwargs.get("chain")
        token_in = kwargs.get("token_in")
        token_out = kwargs.get("token_out")
        amount = float(kwargs.get("amount"))
        
        if not all([chain, token_in, token_out, amount]):
            logger.error("Missing required parameters for quote")
            return None
            
        return agent.connection_manager.connections["sonic"].get_quote(
            chain=chain,
            token_in=token_in,
            token_out=token_out,
            amount=amount
        )

    except Exception as e:
        logger.error(f"Failed to get quote: {str(e)}")
        return None

@register_action("execute-swap")
def execute_swap(agent, **kwargs):
    """Execute token swap
    """
    try:
        chain = kwargs.get("chain")
        token_in = kwargs.get("token_in")
        token_out = kwargs.get("token_out")
        amount = float(kwargs.get("amount"))
        slippage = float(kwargs.get("slippage", 0.5))
        
        if not all([chain, token_in, token_out, amount]):
            logger.error("Missing required parameters for swap")
            return None
            
        return agent.connection_manager.connections["sonic"].execute_swap(
            chain=chain,
            token_in=token_in,
            token_out=token_out,
            amount=amount,
            slippage=slippage
        )

    except Exception as e:
        logger.error(f"Failed to execute swap: {str(e)}")
        return None

@register_action("get-cross-chain-quote")
def get_cross_chain_quote(agent, **kwargs):
    """Get cross-chain swap quote
    """
    try:
        source_chain = kwargs.get("source_chain")
        target_chain = kwargs.get("target_chain")
        token_in = kwargs.get("token_in")
        token_out = kwargs.get("token_out")
        amount = float(kwargs.get("amount"))
        
        if not all([source_chain, target_chain, token_in, token_out, amount]):
            logger.error("Missing required parameters for cross-chain quote")
            return None
            
        return agent.connection_manager.connections["sonic"].get_cross_chain_quote(
            source_chain=source_chain,
            target_chain=target_chain,
            token_in=token_in,
            token_out=token_out,
            amount=amount
        )

    except Exception as e:
        logger.error(f"Failed to get cross-chain quote: {str(e)}")
        return None

@register_action("execute-cross-chain-swap")
def execute_cross_chain_swap(agent, **kwargs):
    """Execute cross-chain token swap
    """
    try:
        source_chain = kwargs.get("source_chain")
        target_chain = kwargs.get("target_chain")
        token_in = kwargs.get("token_in")
        token_out = kwargs.get("token_out")
        amount = float(kwargs.get("amount"))
        slippage = float(kwargs.get("slippage", 0.5))
        
        if not all([source_chain, target_chain, token_in, token_out, amount]):
            logger.error("Missing required parameters for cross-chain swap")
            return None
            
        return agent.connection_manager.connections["sonic"].execute_cross_chain_swap(
            source_chain=source_chain,
            target_chain=target_chain,
            token_in=token_in,
            token_out=token_out,
            amount=amount,
            slippage=slippage
        )

    except Exception as e:
        logger.error(f"Failed to execute cross-chain swap: {str(e)}")
        return None

@register_action("get-limit-orders")
def get_limit_orders(agent, **kwargs):
    """Get limit orders for an address
    """
    try:
        chain = kwargs.get("chain")
        address = kwargs.get("address")
        
        if not chain or not address:
            logger.error("Chain or address not specified")
            return None
            
        return agent.connection_manager.connections["sonic"].get_limit_orders(
            chain=chain,
            address=address
        )

    except Exception as e:
        logger.error(f"Failed to get limit orders: {str(e)}")
        return None

@register_action("get-gmx-quote")
def get_gmx_quote(agent, **kwargs):
    """Get GMX swap quote
    """
    try:
        chain = kwargs.get("chain")
        token_in = kwargs.get("token_in")
        token_out = kwargs.get("token_out")
        amount = float(kwargs.get("amount"))
        
        if not all([chain, token_in, token_out, amount]):
            logger.error("Missing required parameters for GMX quote")
            return None
            
        return agent.connection_manager.connections["sonic"].get_gmx_quote(
            chain=chain,
            token_in=token_in,
            token_out=token_out,
            amount=amount
        )

    except Exception as e:
        logger.error(f"Failed to get GMX quote: {str(e)}")
        return None

@register_action("create-dca-order")
def create_dca_order(agent, **kwargs):
    """Create a DCA (Dollar Cost Average) swap order
    """
    try:
        chain = kwargs.get("chain")
        token_in = kwargs.get("token_in")
        token_out = kwargs.get("token_out")
        amount = float(kwargs.get("amount"))
        interval = kwargs.get("interval")
        total_orders = int(kwargs.get("total_orders"))
        
        if not all([chain, token_in, token_out, amount, interval, total_orders]):
            logger.error("Missing required parameters for DCA order")
            return None
            
        return agent.connection_manager.connections["sonic"].create_dca_order(
            chain=chain,
            token_in=token_in,
            token_out=token_out,
            amount=amount,
            interval=interval,
            total_orders=total_orders
        )

    except Exception as e:
        logger.error(f"Failed to create DCA order: {str(e)}")
        return None

@register_action("get-dca-orders")
def get_dca_orders(agent, **kwargs):
    """Get DCA orders for an address
    """
    try:
        chain = kwargs.get("chain")
        address = kwargs.get("address")
        
        if not chain or not address:
            logger.error("Chain or address not specified")
            return None
            
        return agent.connection_manager.connections["sonic"].get_dca_orders(
            chain=chain,
            address=address
        )

    except Exception as e:
        logger.error(f"Failed to get DCA orders: {str(e)}")
        return None
