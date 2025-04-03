"""
Handler for Telegram whale tracking commands
"""
import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# List of tracked whale wallets - starting with the ones from the user request
WHALE_WALLETS = [
    "0xAdDbD648c380E4822e9c934B0fc5C9f607d892c5",
    "0x7e11cd6f2e24ddec67246a35dda4afc62dad6922",
    "0xcdFF6DDc9f095CeDF3b1529e3B961a39iEb75F0",
    "0xc53127AF07fF9a749BA8b70B6BF5f0899E4F33dE",
    "0x3eE607990BfB250B03b9656E0Ed2F9Bb9F64f867",
    "0xeCAD53cDB102Bd84Efb050E7F406b081D9E7E2Ae",
    "0x996f77356278269347aa2310f8a4e1855b7c3c37",
    "0x67A5D82F02724E01F02D0aA9173E4D8E8aE6a78a",
    "0x5b43e0a357B4d6a60b7e757C1F345bE3Bcd1Af6A",
    "0x8aE8be9F23Ff6B397E85Dd9219F934805b76E07d",
    "0x91Ef84244Aa478c39E966B9d18Bd7FD8562576f7",
    "0x5a6d63fF791c3eDcfA6eF3087B3cB9e5052bd332",
    "0x64774Eff5A31C85070F158C6DaC0e12cEB2b1C11",
    "0x8BEa04A94903f97A5c0cFac79F9b24EA25734358",
    "0x7A2AB74416Fb2Bb3D5497918529638702c137841",
    "0x52faCd14353E4F9d16b84A9352A7f6e8e0C12B27",
    "0x98C3e9D7508461B0C3222a3Dd0dA2bA4e9867B2C",
    "0x2C7036574e5a8b3c4cE6d077D2332e50c3Ba5518",
    "0x63A8CE2F72bd30c1Fb8660DF44D22F733e2161e7",
    "0x7F2b28C0Ef0f793d48a41c3407BbdD13b3A39a89",
    "0x3F5a1BFFB1Aa864af7E826Fb8fcf4e7471d97319",
    "0xee97F4229194e3D7829D896DdFF6242Fc298A998",
    "0xc4fc550ca25de0ba3baf9a9dc85bab2c211f0f39",
    # Additional well-known whale wallets can be added here
]

async def handle_whale_command(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle the /whale command to get whale wallet information
    
    Args:
        context: Command context with services and parameters
        
    Returns:
        Response with whale wallet data
    """
    logger.info("Processing whale command")
    
    try:
        # Extract services from context
        whale_service = context.get('whale_service')
        if not whale_service:
            return {"error": "Whale tracking service not available"}
        
        # Extract parameters
        params = context.get('params', {})
        address = params.get('address')
        token = params.get('token')
        
        # If specific address is provided, look up that address
        if address and re.match(r'^0x[a-fA-F0-9]{40}$', address):
            wallet_data = await whale_service.get_wallet_summary(address, token)
            
            if not wallet_data:
                return {"text": f"No data available for wallet {address[:6]}...{address[-4:]}"}
            
            # Format wallet data for display
            formatted_response = f"*Whale Wallet: {address[:6]}...{address[-4:]}*\n\n"
            
            # Add token holdings
            balances = wallet_data.get('balances', [])
            if balances:
                formatted_response += "*Token Holdings:*\n"
                for balance in balances:
                    token_symbol = balance.get('symbol', 'Unknown')
                    amount = balance.get('amount', 0)
                    value_usd = balance.get('value_usd', 0)
                    formatted_response += f"• {token_symbol}: {amount:,.4f} (${value_usd:,.2f})\n"
            
            # Add recent transactions
            transactions = wallet_data.get('recent_transactions', [])
            if transactions:
                formatted_response += "\n*Recent Transactions:*\n"
                for tx in transactions[:5]:  # Show last 5 transactions
                    tx_type = tx.get('type', 'Unknown')
                    token_symbol = tx.get('token', 'Unknown')
                    amount = tx.get('amount', 0)
                    time = tx.get('timestamp', 'Unknown')
                    formatted_response += f"• {tx_type}: {amount:,.4f} {token_symbol} ({time})\n"
            
            return {
                "text": formatted_response,
                "parse_mode": "Markdown"
            }
        
        # Otherwise, get summary of all whale activity
        else:
            # Get summary of whale activity
            summary = await whale_service.get_whale_summary(token)
            
            if not summary or len(summary.get('wallets', [])) == 0:
                return {"text": "No whale activity detected in the monitored period."}
            
            # Format summary for display
            time_period = summary.get('time_period', '24h')
            
            formatted_response = f"*Whale Activity Summary ({time_period})*\n\n"
            
            # Net flow
            net_flow = summary.get('net_flow', 0)
            flow_emoji = "🟢" if net_flow > 0 else "🔴" if net_flow < 0 else "⚪"
            formatted_response += f"{flow_emoji} *Net Flow:* ${abs(net_flow):,.2f} {'inflow' if net_flow > 0 else 'outflow'}\n\n"
            
            # Notable wallets
            wallets = summary.get('wallets', [])
            if wallets:
                formatted_response += "*Notable Whale Activity:*\n"
                for wallet in wallets[:5]:  # Show top 5 wallets
                    address = wallet.get('address', 'Unknown')
                    short_addr = f"{address[:6]}...{address[-4:]}"
                    action = wallet.get('action', 'active')
                    volume = wallet.get('volume', 0)
                    token_symbol = wallet.get('token', 'Unknown')
                    
                    # Add emoji based on action
                    action_emoji = "🔴" if action == 'sell' else "🟢" if action == 'buy' else "⚪"
                    
                    formatted_response += f"{action_emoji} {short_addr}: {action.capitalize()} ${volume:,.2f} of {token_symbol}\n"
            
            return {
                "text": formatted_response,
                "parse_mode": "Markdown"
            }
        
    except Exception as e:
        logger.error(f"Error in whale command: {str(e)}")
        return {"text": f"⚠️ Error retrieving whale data: {str(e)}"}


async def handle_whale_transaction(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle a specific whale transaction query
    
    Args:
        context: Command context with services and parameters
        
    Returns:
        Response with transaction details
    """
    logger.info("Processing whale transaction query")
    
    try:
        # Extract services from context
        whale_service = context.get('whale_service')
        if not whale_service:
            return {"error": "Whale tracking service not available"}
        
        # Extract parameters
        params = context.get('params', {})
        tx_hash = params.get('tx_hash')
        
        if not tx_hash or not re.match(r'^0x[a-fA-F0-9]{64}$', tx_hash):
            return {"text": "Please provide a valid transaction hash."}
        
        # Get transaction details
        tx_details = await whale_service.get_transaction_details(tx_hash)
        
        if not tx_details:
            return {"text": f"No details found for transaction {tx_hash[:6]}...{tx_hash[-4:]}"}
        
        # Format transaction details for display
        formatted_response = f"*Transaction Details*\n\n"
        
        # Basic info
        tx_type = tx_details.get('type', 'Unknown')
        from_addr = tx_details.get('from', 'Unknown')
        to_addr = tx_details.get('to', 'Unknown')
        value = tx_details.get('value', 0)
        token = tx_details.get('token', 'ETH')
        timestamp = tx_details.get('timestamp', 'Unknown')
        gas_used = tx_details.get('gas_used', 0)
        gas_price = tx_details.get('gas_price', 0)
        
        formatted_response += f"📝 *Type:* {tx_type.capitalize()}\n"
        formatted_response += f"⏱️ *Time:* {timestamp}\n"
        formatted_response += f"💸 *Value:* {value:,.6f} {token}\n"
        formatted_response += f"🔄 *From:* `{from_addr[:6]}...{from_addr[-4:]}`\n"
        formatted_response += f"🔄 *To:* `{to_addr[:6]}...{to_addr[-4:]}`\n"
        formatted_response += f"⛽ *Gas:* {gas_used:,} units @ {gas_price:.2f} Gwei\n\n"
        
        # Add block info
        block = tx_details.get('block', 0)
        if block > 0:
            formatted_response += f"🧱 *Block:* {block:,}\n"
        
        # Add TX hash
        formatted_response += f"🔍 *Hash:* `{tx_hash}`\n"
        
        # Add explorer link if available
        chain_id = tx_details.get('chain_id', 'sonic')
        if chain_id == 'sonic':
            explorer_url = f"https://sonicscan.org/tx/{tx_hash}"
            formatted_response += f"\n[View on SonicScan]({explorer_url})"
        
        return {
            "text": formatted_response,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        
    except Exception as e:
        logger.error(f"Error in whale transaction query: {str(e)}")
        return {"text": f"⚠️ Error retrieving transaction details: {str(e)}"}