"""
Network definitions for blockchain connections
"""
from typing import Dict, Any, List, Optional

# Sonic network definitions
SONIC_NETWORKS = {
    'sonic': {
        'name': 'Sonic',
        'chain_id': 146,  # Updated from 115 to 146 based on test_sonic_transfer.py
        'rpc_url': 'https://sonic-rpc.publicnode.com',  # Primary RPC URL
        'rpc_urls': [
            'https://sonic-rpc.publicnode.com',
            'wss://sonic.callstaticrpc.com',
            'https://rpc.soniclabs.com'
        ],
        'explorer_url': 'https://sonicscan.org',
        'scanner_url': 'https://sonicscan.org',  # Added scanner_url
        'native_token': 'SONIC',
        'native_token_decimals': 18
    }
}

# Ethereum network definitions
ETH_NETWORKS = {
    'mainnet': {
        'name': 'Ethereum Mainnet',
        'chain_id': 1,
        'rpc_url': 'https://eth-mainnet.g.alchemy.com/v2/',
        'explorer_url': 'https://etherscan.io',
        'native_token': 'ETH',
        'native_token_decimals': 18
    },
    'sepolia': {
        'name': 'Sepolia Testnet',
        'chain_id': 11155111,
        'rpc_url': 'https://eth-sepolia.g.alchemy.com/v2/',
        'explorer_url': 'https://sepolia.etherscan.io',
        'native_token': 'ETH',
        'native_token_decimals': 18
    }
}

# Base network definitions
BASE_NETWORKS = {
    'base': {
        'name': 'Base',
        'chain_id': 8453,
        'rpc_url': 'https://mainnet.base.org',
        'explorer_url': 'https://basescan.org',
        'native_token': 'ETH',
        'native_token_decimals': 18
    }
}

# Arbitrum network definitions
ARBITRUM_NETWORKS = {
    'arbitrum': {
        'name': 'Arbitrum One',
        'chain_id': 42161,
        'rpc_url': 'https://arb1.arbitrum.io/rpc',
        'explorer_url': 'https://arbiscan.io',
        'native_token': 'ETH',
        'native_token_decimals': 18
    }
}

# Optimism network definitions
OPTIMISM_NETWORKS = {
    'optimism': {
        'name': 'Optimism',
        'chain_id': 10,
        'rpc_url': 'https://mainnet.optimism.io',
        'explorer_url': 'https://optimistic.etherscan.io',
        'native_token': 'ETH',
        'native_token_decimals': 18
    }
}

# Combined EVM networks
EVM_NETWORKS = {
    **ETH_NETWORKS,
    **BASE_NETWORKS,
    **ARBITRUM_NETWORKS,
    **OPTIMISM_NETWORKS,
    **SONIC_NETWORKS
}

# List of all supported networks
ALL_NETWORKS = {
    **EVM_NETWORKS
}

def get_network_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get network configuration by network name"""
    return ALL_NETWORKS.get(name.lower())

def get_network_by_chain_id(chain_id: int) -> Optional[Dict[str, Any]]:
    """Get network configuration by chain ID"""
    for network in ALL_NETWORKS.values():
        if network['chain_id'] == chain_id:
            return network
    return None

def is_valid_network(name: str) -> bool:
    """Check if a network name is valid"""
    return name.lower() in ALL_NETWORKS

def get_explorer_url(network_name: str, tx_hash: Optional[str] = None) -> str:
    """Get explorer URL for a network, optionally with transaction hash"""
    network = get_network_by_name(network_name)
    if not network:
        return ''
    
    base_url = network['explorer_url']
    if tx_hash:
        return f"{base_url}/tx/{tx_hash}"
    
    return base_url

def get_address_url(network_name: str, address: str) -> str:
    """Get explorer URL for an address on a specific network"""
    network = get_network_by_name(network_name)
    if not network:
        return ''
    
    return f"{network['explorer_url']}/address/{address}"