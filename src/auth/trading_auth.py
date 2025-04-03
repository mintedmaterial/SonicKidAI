"""Trading authentication module

This module handles authentication and authorization for trading operations,
ensuring only approved wallets can execute trades.
"""
import os
import logging
from typing import List

logger = logging.getLogger(__name__)

class TradingAuthManager:
    """Manager class for trading authentication and authorization"""
    
    def __init__(self):
        """Initialize the trading auth manager"""
        self.authorized_accounts = []
        self._load_authorized_accounts()
        
    def _load_authorized_accounts(self) -> None:
        """Load authorized accounts from environment variables"""
        # Authorization from environment variable: comma-separated list of wallet addresses
        auth_accounts_str = os.getenv("AUTHORIZED_TRADING_ACCOUNTS", "")
        if auth_accounts_str:
            self.authorized_accounts = [addr.strip().lower() for addr in auth_accounts_str.split(",")]
            logger.info(f"Loaded {len(self.authorized_accounts)} authorized trading accounts")
        else:
            logger.warning("No authorized trading accounts configured")
            
    def is_account_authorized(self, account_address: str) -> bool:
        """Check if an account is authorized for trading
        
        Args:
            account_address: Ethereum address to check
            
        Returns:
            True if authorized, False otherwise
        """
        if not account_address:
            return False
            
        # Normalize address (lowercase)
        normalized_address = account_address.strip().lower()
        
        # Reload accounts in case they were updated
        if not self.authorized_accounts:
            self._load_authorized_accounts()
            
        # Check if account is in authorized list
        is_authorized = normalized_address in self.authorized_accounts
        
        if not is_authorized:
            logger.warning(f"Unauthorized trading attempt from {normalized_address}")
        
        return is_authorized
        
    def get_authorized_accounts(self) -> List[str]:
        """Get list of authorized accounts
        
        Returns:
            List of authorized account addresses
        """
        if not self.authorized_accounts:
            self._load_authorized_accounts()
            
        return self.authorized_accounts
        
    def has_authorized_accounts(self) -> bool:
        """Check if any authorized accounts are configured
        
        Returns:
            True if at least one authorized account exists
        """
        if not self.authorized_accounts:
            self._load_authorized_accounts()
            
        return len(self.authorized_accounts) > 0

# Create a singleton instance
trading_auth = TradingAuthManager()