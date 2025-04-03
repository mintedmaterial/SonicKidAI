"""
Chain configuration constants for blockchain connections
"""
from typing import Dict, Any, List, Optional

# Chain IDs
ETHEREUM_CHAIN_ID = 1
BASE_CHAIN_ID = 8453
SONIC_CHAIN_ID = 146
ARBITRUM_CHAIN_ID = 42161
OPTIMISM_CHAIN_ID = 10

# String versions of Chain IDs for API compatibility
ETHEREUM_CHAIN_ID_STR = str(ETHEREUM_CHAIN_ID)
BASE_CHAIN_ID_STR = str(BASE_CHAIN_ID)
SONIC_CHAIN_ID_STR = str(SONIC_CHAIN_ID)
ARBITRUM_CHAIN_ID_STR = str(ARBITRUM_CHAIN_ID)
OPTIMISM_CHAIN_ID_STR = str(OPTIMISM_CHAIN_ID)

class ChainConfig:
    """Chain configuration class for blockchain connections"""
    
    def __init__(self, name: str, chain_id: int, rpc_url: str, explorer_url: str, 
                 contracts: Dict[str, str], native_token: str = 'ETH', 
                 native_token_decimals: int = 18):
        """Initialize chain configuration"""
        self.name = name
        self.chain_id = chain_id
        self.rpc_url = rpc_url
        self.explorer_url = explorer_url
        self.contracts = contracts
        self.native_token = native_token
        self.native_token_decimals = native_token_decimals
    
    def get_contract(self, contract_name: str) -> Optional[str]:
        """Get contract address by name"""
        return self.contracts.get(contract_name)
    
    def get_explorer_tx_url(self, tx_hash: str) -> str:
        """Get transaction URL for explorer"""
        return f"{self.explorer_url}/tx/{tx_hash}"
    
    def get_explorer_address_url(self, address: str) -> str:
        """Get address URL for explorer"""
        return f"{self.explorer_url}/address/{address}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'chain_id': self.chain_id,
            'rpc_url': self.rpc_url,
            'explorer_url': self.explorer_url,
            'contracts': self.contracts,
            'native_token': self.native_token,
            'native_token_decimals': self.native_token_decimals
        }

# Base contracts for verification
BASE_CONTRACTS = {
    'USDC': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    'WETH': '0x4200000000000000000000000000000000000006',
    'SONIC_ROUTER': '0x12a76434182c8cAF4c4333F231fa1A7Ad4b9A330',
    'SONIC_FACTORY': '0x111A00868581f3e8bcE9642124aF9fD84369a004'
}

# Ethereum contracts
ETH_CONTRACTS = {
    'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
    'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
    'KYBER_ROUTER': '0x68e90D07Ea5FAe2Bd0e771f278e3a82Cac49FC8a',
    'KYBER_FACTORY': '0x833e4083B7ae46CeA85695c4f7ed25CDAd8886dE'
}

# Sonic (Fantom) contracts
SONIC_CONTRACTS = {
    'USDC': '0xeb466342c20d5cad16bd5221d10f231de6826c6c',
    'USDC_E': '0x04068DA6C83AFCFA0e13ba15A6696662335D5B75',
    'WSONIC': '0x21be370d5312f44cb42ce377bc9b8a0cef1a4c83',
    'MAGPIE_ROUTER': '0x32F09265fc3eea1c22B76CAFc8218F0713c3f848',
    'SWAPMAGIC_ROUTER': '0x3F46F743C60103Df7a2396b87D43fb4666F32862',
    'ODOS_ROUTER': '0x4ABa01FB8E1f6BFE80c56Deb367f19F35Df0f4aE'
}

# Token decimals
TOKEN_DECIMALS = {
    'USDC': 6,
    'USDC_E': 6,
    'USDT': 6,
    'DAI': 18,
    'ETH': 18,
    'WETH': 18,
    'SONIC': 18,
    'WSONIC': 18
}

# Common token addresses across chains
COMMON_TOKENS = {
    'ETH': {
        'ethereum': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
        'base': '0x4200000000000000000000000000000000000006',      # WETH on Base
        'arbitrum': '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1',  # WETH on Arbitrum
        'optimism': '0x4200000000000000000000000000000000000006'   # WETH on Optimism
    },
    'USDC': {
        'ethereum': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
        'base': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
        'arbitrum': '0xaf88d065e77c8cC2239327C5EDb3A432268e5831',
        'optimism': '0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85',
        'sonic': '0xeb466342c20d5cad16bd5221d10f231de6826c6c'
    },
    'USDT': {
        'ethereum': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
        'base': '0xA3A1dB8487A3Da01D55BC8DCC8CBA27324D0fBA9',
        'arbitrum': '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9',
        'optimism': '0x94b008aA00579c1307B0EF2c499aD98a8ce58e58',
        'sonic': '0x049d68029688eAbF473097a2fC38ef61633A3C7A'
    }
}

# Chain-specific configurations
CHAIN_CONFIG = {
    'ethereum': {
        'name': 'Ethereum Mainnet',
        'chain_id': 1,
        'contracts': ETH_CONTRACTS,
        'explorer_url': 'https://etherscan.io',
        'rpc_url': 'https://eth-mainnet.g.alchemy.com/v2/'
    },
    'base': {
        'name': 'Base',
        'chain_id': 8453,
        'contracts': BASE_CONTRACTS,
        'explorer_url': 'https://basescan.org',
        'rpc_url': 'https://mainnet.base.org'
    },
    'sonic': {
        'name': 'Sonic',
        'chain_id': 146,
        'contracts': SONIC_CONTRACTS,
        'explorer_url': 'https://sonicscan.org',
        'rpc_url': 'https://rpc.sonic.exchange'
    }
}

def get_chain_config(chain_name: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific chain"""
    return CHAIN_CONFIG.get(chain_name.lower())

def get_token_address(token_symbol: str, chain_name: str) -> Optional[str]:
    """Get token address for a specific chain"""
    token_symbol = token_symbol.upper()
    chain_name = chain_name.lower()
    
    # Check in common tokens first
    if token_symbol in COMMON_TOKENS and chain_name in COMMON_TOKENS[token_symbol]:
        return COMMON_TOKENS[token_symbol][chain_name]
    
    # Check in chain-specific contracts
    chain_config = get_chain_config(chain_name)
    if chain_config and 'contracts' in chain_config:
        contracts = chain_config['contracts']
        return contracts.get(token_symbol)
    
    return None

def get_token_decimals(token_symbol: str) -> int:
    """Get token decimals"""
    token_symbol = token_symbol.upper()
    return TOKEN_DECIMALS.get(token_symbol, 18)  # Default to 18 decimals for most tokens

def is_valid_chain(chain_name: str) -> bool:
    """Check if chain is supported"""
    return chain_name.lower() in CHAIN_CONFIG

def get_explorer_url(chain_name: str, tx_hash: Optional[str] = None) -> str:
    """Get explorer URL for a transaction"""
    chain_config = get_chain_config(chain_name)
    if not chain_config or 'explorer_url' not in chain_config:
        return ''
    
    base_url = chain_config['explorer_url']
    if tx_hash:
        return f"{base_url}/tx/{tx_hash}"
    
    return base_url