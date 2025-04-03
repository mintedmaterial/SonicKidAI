"""Simple standalone test for trading authorization"""
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
        """Check if an account is authorized for trading"""
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
        
    def get_authorized_accounts(self) -> list:
        """Get list of authorized accounts"""
        if not self.authorized_accounts:
            self._load_authorized_accounts()
            
        return self.authorized_accounts
        
    def has_authorized_accounts(self) -> bool:
        """Check if any authorized accounts are configured"""
        if not self.authorized_accounts:
            self._load_authorized_accounts()
            
        return len(self.authorized_accounts) > 0

def process_trade_command(amount: float, token_address: str, user_address: str = None) -> dict:
    """Simulated process_trade_command with auth check"""
    trading_auth = TradingAuthManager()
    
    # Check authorization if user_address is provided
    if user_address:
        # Verify user is authorized to execute trades
        if not trading_auth.is_account_authorized(user_address):
            logger.warning(f"Unauthorized trade attempt from user: {user_address}")
            return {
                "success": False, 
                "error": "Unauthorized: Your account is not approved for executing trades"
            }
        logger.info(f"Authorization check passed for user: {user_address}")
    else:
        # If no user_address is provided, assume it's an internal call (e.g., automated trading)
        logger.info("No user authentication provided, assuming internal agent execution")
    
    # Proceed with trade (simulated)
    logger.info(f"Processing trade: amount={amount}, token={token_address}")
    return {"success": True, "result": {"tx_hash": "0x123abc", "amount": amount}}

def main():
    """Test the trading auth functionality"""
    # Set up test environment
    agent_wallet = "0xAGENTWALLETADDRESS"
    authorized_wallet = "0xTESTAUTHORIZEDADDRESS"
    unauthorized_wallet = "0xUNAUTHORIZEDADDRESS"
    
    # Configure authorized accounts
    os.environ['AUTHORIZED_TRADING_ACCOUNTS'] = f"{agent_wallet},{authorized_wallet}"
    
    # Create auth manager
    auth_manager = TradingAuthManager()
    
    logger.info(f"Authorized accounts: {auth_manager.get_authorized_accounts()}")
    
    # Test case 1: Authorized user should succeed
    result1 = process_trade_command(
        amount=1.0,
        token_address="0xTESTTOKENADDRESS",
        user_address=authorized_wallet  # Authorized
    )
    logger.info(f"Test 1 (Authorized) result: {result1}")
    
    # Test case 2: Unauthorized user should fail
    result2 = process_trade_command(
        amount=1.0,
        token_address="0xTESTTOKENADDRESS",
        user_address=unauthorized_wallet  # Unauthorized
    )
    logger.info(f"Test 2 (Unauthorized) result: {result2}")
    
    # Test case 3: No user_address (internal agent call) should proceed
    result3 = process_trade_command(
        amount=1.0,
        token_address="0xTESTTOKENADDRESS"
        # No user_address
    )
    logger.info(f"Test 3 (No user) result: {result3}")
    
    # Verify results
    assert result1.get("success") == True, "Authorized user should succeed"
    assert result2.get("success") == False, "Unauthorized user should fail"
    assert result3.get("success") == True, "No user_address (internal) should succeed"
    
    logger.info("✅ All trading authorization tests passed!")

if __name__ == "__main__":
    main()