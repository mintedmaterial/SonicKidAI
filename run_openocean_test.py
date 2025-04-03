#!/usr/bin/env python3
"""
Run OpenOcean test with clean output
"""
import os
import sys
import asyncio
import logging

# Configure logging to prevent token list and other verbose output from cluttering the console

# Import dotenv with error handling
try:
    from dotenv import load_dotenv
except ImportError:
    # If dotenv is not available, provide a placeholder function
    def load_dotenv():
        print("Warning: python-dotenv not installed, relying on pre-set environment variables.")

from src.connections.openocean_connection import OpenOceanConnection

# Setup console logging
console = logging.StreamHandler()
console.setLevel(logging.WARNING)  # Only show warning and above in console
console.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))

# Setup file logging
file_handler = logging.FileHandler('openocean_test.log', mode='w')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(console)
root_logger.addHandler(file_handler)

# Load environment variables
load_dotenv()

# Store OpenOcean API key in environment variable if not already set
if not os.getenv('OPENOCEAN_API_KEY'):
    os.environ['OPENOCEAN_API_KEY'] = 'mNhHD7nFNkCHGevafz40BQc1dX9AzxkH'

# Test parameters for swap
TEST_PARAMS = {
    'fromToken': '0x039e2fb66102314ce7b64ce5ce3e5183bc94ad38',  # wS token (Wrapped Sonic)
    'toToken': '0x6fb9897896fe5d05025eb43306675727887d0b7c',    # HEDGY token
    'fromAmount': '5'  # 5 wS
}

async def test_openocean_connection():
    """Test OpenOcean API connection with Sonic chain"""
    
    print("\n🔍 RUNNING OPENOCEAN CONNECTION TEST FOR SONIC CHAIN")
    print("======================================================")
    
    # Initialize OpenOcean connection with Sonic chain ID and Pro API settings
    config = {
        'chain_id': '146',  # Sonic chain ID
        'slippage': 1,      # 1% slippage
        'use_pro_api': True,
        'api_key': os.getenv('OPENOCEAN_API_KEY')
    }
    
    # Initialize connection
    openocean = OpenOceanConnection(config)
    chain_name = openocean.chain_name
    
    print("\n📋 TEST CONFIGURATION:")
    
    print(f"  ✓ Chain ID: {openocean.chain_id} (Sonic)")
    print(f"  ✓ Chain name: {chain_name}")
    print(f"  ✓ Base URL: {openocean.base_url}")
    
    # Safely print API key if available
    api_key = openocean.api_key
    if api_key:
        print(f"  ✓ API Key: Using key {api_key[:4]}...{api_key[-4:]}")
    else:
        print("  ⚠ Warning: No API key provided")
    
    print("\n🔄 EXECUTING API TESTS:")
    
    try:
        # Connect to OpenOcean API with verbosity disabled
        print("  ⏳ Testing API connection...", end="", flush=True)
        connected = await openocean.connect(verbose=False)
        
        if not connected:
            print(" ❌ FAILED")
            print("     Error: Failed to connect to OpenOcean API")
            return False
        
        print(" ✅ SUCCESS")
        
        # Test getting token list
        print("  ⏳ Fetching token list...", end="", flush=True)
        
        # Get token list with verbosity disabled
        tokens = await openocean.get_token_list(verbose=False)
        
        if not tokens:
            print(" ❌ FAILED")
            print("     Error: Failed to get token list")
            return False
        
        print(f" ✅ SUCCESS ({len(tokens)} tokens)")
        
        # Find tokens in the list
        print("  ⏳ Finding specified tokens...", end="", flush=True)
        ws_token = next((t for t in tokens if t['address'].lower() == TEST_PARAMS['fromToken'].lower()), None)
        hedgy_token = next((t for t in tokens if t['address'].lower() == TEST_PARAMS['toToken'].lower()), None)
        
        if not ws_token:
            print(" ❌ FAILED")
            print(f"     Error: Source token not found: {TEST_PARAMS['fromToken']}")
            return False
        
        if not hedgy_token:
            print(" ❌ FAILED")
            print(f"     Error: Target token not found: {TEST_PARAMS['toToken']}")
            return False
        
        print(" ✅ SUCCESS")
        print(f"     From: {ws_token['symbol']} ({ws_token['name']})")
        print(f"     To: {hedgy_token['symbol']} ({hedgy_token['name']})")
        
        # Get quote
        print(f"  ⏳ Getting swap quote for {TEST_PARAMS['fromAmount']} {ws_token['symbol']} to {hedgy_token['symbol']}...", end="", flush=True)
        
        quote = await openocean.get_quote(
            in_token_address=TEST_PARAMS['fromToken'],
            out_token_address=TEST_PARAMS['toToken'],
            amount=TEST_PARAMS['fromAmount']
        )
        
        if quote is None:
            print(" ❌ FAILED")
            print("     Error: Failed to get swap quote (API error)")
            return False
        elif quote == {}:
            print(" ⚠️ NO ROUTE")
            print("     Note: No swap route available for this pair (empty response)")
            print("\n✅ TEST COMPLETED SUCCESSFULLY (no swap route available for this pair)")
            return True
        
        # Quote exists, print details
        print(" ✅ SUCCESS")
        print(f"     Input: {quote.get('inAmount')} {quote.get('inToken', {}).get('symbol')}")
        print(f"     Output: {quote.get('outAmount')} {quote.get('outToken', {}).get('symbol')}")
        
        # Get transaction data
        wallet_address = "0xCC98d2e64279645D204DD7b25A7c09b6B3ded0d9"  # Agent wallet from SONIC_PRIVATE_KEY
        
        print("  ⏳ Getting swap transaction data...", end="", flush=True)
        tx_data = await openocean.get_swap_transaction(
            in_token_address=TEST_PARAMS['fromToken'],
            out_token_address=TEST_PARAMS['toToken'],
            amount=TEST_PARAMS['fromAmount'],
            account=wallet_address
        )
        
        if tx_data is None:
            print(" ❌ FAILED")
            print("     Error: Failed to get swap transaction data")
            return False
        elif tx_data == {}:
            print(" ⚠️ NO TRANSACTION")
            print("     Note: No transaction data available (empty response)")
            print("\n✅ TEST COMPLETED SUCCESSFULLY (no transaction data available)")
            return True
        
        print(" ✅ SUCCESS")
        print(f"     To: {tx_data.get('to')}")
        print(f"     Value: {tx_data.get('value')}")
        print(f"     Estimated gas: {tx_data.get('estimatedGas')}")
        
        print("\n✅ ALL TESTS PASSED SUCCESSFULLY!")
        
        return True
        
    except Exception as e:
        print("\n❌ TEST FAILED with error:")
        print(f"  Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Close the connection
        if hasattr(openocean, '_session') and openocean._session:
            await openocean.close()
            print("\n🔄 Closed OpenOcean API connection")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("📊 OPENOCEAN CONNECTION TEST FOR SONIC CHAIN")
    print("="*60)
    print("Testing OpenOcean API connection and swap functionality for Sonic chain")
    print(f"  From token: {TEST_PARAMS['fromToken']} (wS)")
    print(f"  To token: {TEST_PARAMS['toToken']} (HEDGY)")
    print(f"  Amount: {TEST_PARAMS['fromAmount']} wS")
    print("-"*60)
    
    success = asyncio.run(test_openocean_connection())
    
    if success:
        print("\n✨ TEST SUMMARY: All tests completed successfully")
    else:
        print("\n❌ TEST SUMMARY: Some tests failed, see logs for details")
    
    print("="*60 + "\n")
    sys.exit(0 if success else 1)