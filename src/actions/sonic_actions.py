"""SONIC token and trading actions"""
import logging
import time
from web3 import Web3
from typing import Dict, Any, Optional
from src.utils.action_registry import register_action
from src.connections.errors import SonicConnectionError

logger = logging.getLogger("actions.sonic_actions")

class SonicActions:
    """Handles Sonic network token transfers and trading actions"""

    def __init__(self, sonic_connection, odos_router, kyber_router=None, magpie_router=None, openocean_router=None):
        """Initialize actions with connection and router instances"""
        self.connection = sonic_connection
        self.web3 = sonic_connection.get_web3()
        self.odos = odos_router
        self.kyber = kyber_router
        self.magpie = magpie_router
        self.openocean = openocean_router  # Add OpenOcean router

    async def _validate_address(self, address: str) -> str:
        """Validate and return checksum address"""
        if not Web3.is_address(address):
            raise ValueError(f"Invalid address: {address}")
        return Web3.to_checksum_address(address)

    async def _get_token_contract(self, token_address: str):
        """Get token contract instance with decimals"""
        try:
            address = await self._validate_address(token_address)
            contract = self.connection.get_contract(address, ERC20_ABI)
            decimals = contract.functions.decimals().call()
            return contract, decimals
        except Exception as e:
            logger.error(f"Failed to get token contract: {str(e)}")
            raise SonicConnectionError(f"Contract initialization failed: {str(e)}")

    async def _ensure_approval(self, token_address: str, spender: str, amount: int, account):
        """Ensure the spender has approval to spend the token amount"""
        try:
            token_contract, decimals = await self._get_token_contract(token_address)
            allowance = token_contract.functions.allowance(account.address, spender).call()

            if allowance < amount:
                # Generate Permit2 data for gasless approval
                permit_data = self.odos.generate_permit(
                    token_address=token_address,
                    spender=spender,
                    amount=amount,
                    deadline=int(time.time()) + 1200,  # 20 minutes
                    private_key=self.connection.get_private_key(),
                    chain_id=self.connection.chain_id
                )

                return permit_data
            return None

        except Exception as e:
            logger.error(f"Approval check failed: {str(e)}")
            raise SonicConnectionError(f"Failed to check/set approval: {str(e)}")

    async def send_sonic(self, to_address: str, amount: float) -> str:
        """Send native $S tokens"""
        try:
            # Validate address
            to_address = await self._validate_address(to_address)

            # Get account
            account = self.connection.get_account()

            # Prepare transaction
            tx = {
                'nonce': self.web3.eth.get_transaction_count(account.address),
                'to': to_address,
                'value': self.web3.to_wei(amount, 'ether'),
                'gas': 21000,  # Standard gas for native transfers
                'gasPrice': self.web3.eth.gas_price,
                'chainId': self.connection.chain_id
            }

            # Sign and send
            signed = account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)

            logger.info(f"Native SONIC transfer successful: {amount} S to {to_address}")
            return f"https://explorer.sonic.ooo/tx/{tx_hash.hex()}"

        except Exception as e:
            logger.error(f"Failed to send SONIC: {str(e)}")
            raise SonicConnectionError(f"Transfer failed: {str(e)}")

    async def send_token(self, token_address: str, to_address: str, amount: float) -> str:
        """Send ERC20 tokens with dynamic decimals"""
        try:
            # Validate addresses
            to_address = await self._validate_address(to_address)
            token_contract, decimals = await self._get_token_contract(token_address)

            # Calculate raw amount
            amount_raw = int(amount * (10 ** decimals))

            # Get account
            account = self.connection.get_account()

            # Build transfer transaction
            tx = token_contract.functions.transfer(
                to_address,
                amount_raw
            ).build_transaction({
                'from': account.address,
                'nonce': self.web3.eth.get_transaction_count(account.address),
                'gas': 100000,  # Estimated gas for ERC20 transfers
                'gasPrice': self.web3.eth.gas_price,
                'chainId': self.connection.chain_id
            })

            # Sign and send
            signed = account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)

            logger.info(f"Token transfer successful: {amount} tokens to {to_address}")
            return f"https://explorer.sonic.ooo/tx/{tx_hash.hex()}"

        except Exception as e:
            logger.error(f"Failed to send tokens: {str(e)}")
            raise SonicConnectionError(f"Token transfer failed: {str(e)}")

    async def execute_swap(self, **kwargs):
        """Execute token swap using available routers"""
        try:
            token_in = kwargs.get("token_in")
            token_out = kwargs.get("token_out")
            amount = float(kwargs.get("amount", 0))
            user_address = kwargs.get("user_address")
            slippage = float(kwargs.get("slippage", 0.5))
            router = kwargs.get("router", "auto")
            swap_data = kwargs.get("swap_data")  # Optional pre-built swap data

            if not all([token_in, token_out, amount > 0, user_address]):
                logger.error("Missing required parameters for swap")
                return None

            # Get account for transaction signing
            account = self.connection.get_account()
            chain_id = self.connection.chain_id

            logger.info(f"Executing swap with parameters:")
            logger.info(f"Token In: {token_in}")
            logger.info(f"Token Out: {token_out}")
            logger.info(f"Amount: {amount}")
            logger.info(f"User Address: {user_address}")
            logger.info(f"Slippage: {slippage}%")
            logger.info(f"Router: {router}")
            logger.info(f"Chain ID: {chain_id}")

            # Try OpenOcean if selected or in auto mode (primary router)
            if router in ["openocean", "auto"] and self.openocean:
                logger.info("Attempting swap via OpenOcean (primary router)")
                try:
                    # Build quote parameters
                    quote_params = {
                        "inTokenAddress": token_in,
                        "outTokenAddress": token_out,
                        "amount": str(Web3.to_wei(amount, 'ether')),
                        "slippage": slippage,
                        "userAddr": user_address
                    }
                    
                    logger.info(f"Building OpenOcean swap with params: {quote_params}")
                    
                    # Get quote from OpenOcean
                    quote = await self.openocean.get_quote(
                        chain_id=chain_id, 
                        in_token_address=token_in,
                        out_token_address=token_out,
                        amount=str(Web3.to_wei(amount, 'ether')),
                        user_address=user_address
                    )
                    
                    if not quote:
                        raise Exception("Failed to get OpenOcean quote")
                    
                    logger.info(f"OpenOcean quote received: {quote}")
                    
                    # Execute swap using the OpenOcean router
                    tx_hash = await self.openocean.execute_swap(
                        chain_id=chain_id,
                        in_token_address=token_in,
                        out_token_address=token_out,
                        amount=str(Web3.to_wei(amount, 'ether')),
                        slippage=slippage,
                        user_address=user_address
                    )
                    
                    if not tx_hash:
                        raise Exception("Failed to execute OpenOcean swap")
                    
                    logger.info(f"✅ OpenOcean transaction successful: {tx_hash}")
                    return f"https://explorer.sonic.ooo/tx/{tx_hash}"
                    
                except Exception as e:
                    logger.error(f"OpenOcean swap failed: {str(e)}")
                    if router == "openocean":  # Only raise if OpenOcean was specifically requested
                        raise
                    # Fall through to next router if in auto mode
            
            # Try KyberSwap if selected or in auto mode (second priority router)
            if router in ["kyber", "auto"] and self.kyber:
                logger.info("Attempting swap via KyberSwap (second priority router)")
                try:
                    # Use provided swap data or build new
                    if not swap_data:
                        logger.debug("Building new swap data...")
                        # Get current nonce
                        nonce = self.web3.eth.get_transaction_count(account.address)
                        logger.info(f"Current nonce: {nonce}")

                        # Convert amount to raw value
                        amount_raw = Web3.to_wei(amount, 'ether')
                        logger.info(f"Amount in wei: {amount_raw}")

                        # Build quote parameters
                        quote_params = {
                            'tokenIn': token_in,
                            'tokenOut': token_out,
                            'amountIn': str(amount_raw),
                            'to': user_address,
                            'slippageTolerance': str(int(slippage * 100))
                        }

                        logger.info(f"Building swap with params: {quote_params}")
                        swap_data = await self.kyber.build_swap_data(
                            chain_id=chain_id,
                            quote_data=quote_params,
                            sender=user_address
                        )

                        if not swap_data:
                            raise Exception("Failed to build swap data")

                        logger.info(f"Swap data built successfully: {swap_data}")

                    # Validate swap data structure
                    if not isinstance(swap_data, dict) or not all(k in swap_data for k in ['router_address', 'transaction']):
                        raise ValueError(f"Invalid swap data structure: {swap_data}")

                    # Extract transaction parameters
                    tx_data = swap_data.get('transaction', {})
                    router_address = swap_data.get('router_address')
                    value = int(swap_data.get('value', '0'))

                    logger.info(f"Router address: {router_address}")
                    logger.info(f"Transaction data length: {len(tx_data.get('data', ''))}")
                    logger.info(f"Value to send: {value} wei")

                    # Build transaction
                    tx = {
                        "from": account.address,
                        "to": Web3.to_checksum_address(router_address),
                        "data": tx_data.get('data'),
                        "value": value,
                        "nonce": self.web3.eth.get_transaction_count(account.address),
                        "chainId": chain_id
                    }

                    # Estimate gas and set proper limits
                    try:
                        estimated_gas = self.web3.eth.estimate_gas(tx)
                        gas_limit = int(estimated_gas * 1.2)  # Add 20% buffer
                        gas_price = self.web3.eth.gas_price

                        logger.info(f"Gas estimation successful:")
                        logger.info(f"Estimated gas: {estimated_gas}")
                        logger.info(f"Gas limit: {gas_limit}")
                        logger.info(f"Gas price: {gas_price} wei")

                        tx['gas'] = gas_limit
                        tx['gasPrice'] = gas_price

                    except Exception as e:
                        # Check for revert reason
                        if "execution reverted" in str(e):
                            revert_msg = str(e).split("execution reverted:")[-1].strip()
                            logger.error(f"Transaction would revert: {revert_msg}")
                            if router == "kyber":
                                raise
                            return None
                        else:
                            logger.warning(f"Gas estimation failed: {e}, using default values")
                            tx['gas'] = 500000
                            tx['gasPrice'] = self.web3.eth.gas_price

                    # Log complete transaction before signing
                    logger.info("Final transaction parameters:")
                    for key, value in tx.items():
                        if key == 'data':
                            logger.info(f"{key}: <truncated> (length: {len(value)})")
                        else:
                            logger.info(f"{key}: {value}")

                    # Sign and send transaction
                    logger.info("Signing transaction...")
                    signed_tx = account.sign_transaction(tx)

                    logger.info("Sending transaction...")
                    tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
                    logger.info(f"Transaction sent: {tx_hash.hex()}")

                    # Wait for receipt with timeout
                    receipt = self.web3.eth.wait_for_transaction_receipt(
                        tx_hash,
                        timeout=300  # 5 minutes timeout
                    )

                    if receipt["status"] == 1:
                        logger.info("✅ KyberSwap transaction successful")
                        logger.info(f"Gas used: {receipt['gasUsed']}")
                        return f"https://explorer.sonic.ooo/tx/{tx_hash.hex()}"
                    else:
                        logger.error(f"❌ Transaction failed! Status: {receipt['status']}")
                        logger.error(f"Gas used: {receipt['gasUsed']}")
                        raise Exception(f"Transaction failed with status: {receipt['status']}")

                except Exception as e:
                    logger.error(f"KyberSwap failed: {str(e)}", exc_info=True)
                    if router == "kyber":
                        raise
                    # Fall through to next router if in auto mode

            # Try Odos if selected or in auto mode (third priority router)
            if router in ["odos", "auto"] and self.odos:
                logger.info("Attempting swap via Odos router (third priority router)")
                try:
                    # Get quote
                    quote_payload = {
                        "inputTokens": [{"tokenAddress": token_in, "amount": str(Web3.to_wei(amount, 'ether'))}],
                        "outputTokens": [{"tokenAddress": token_out, "proportion": 1}],
                        "userAddr": user_address,
                        "slippageLimitPercent": slippage
                    }
                    quote = await self.odos.get_quote(chain_id, quote_payload)
                    if not quote:
                        raise Exception("Failed to get Odos quote")

                    # Check approval and get permit if needed
                    permit_data = await self._ensure_approval(token_in, self.odos.ODOS_ROUTER, int(Web3.to_wei(amount, 'ether')), account)

                    # Assemble transaction with or without permit
                    assembly_payload = {
                        "userAddr": user_address,
                        "pathId": quote.get("pathId"),
                        "quote": quote,
                        "permitData": permit_data
                    }

                    assembly = await self.odos.assemble_transaction(chain_id, assembly_payload)
                    if not assembly:
                        raise Exception("Failed to assemble Odos transaction")

                    # Build and send transaction
                    tx_data = assembly["transaction"]
                    tx = {
                        "to": tx_data["to"],
                        "data": tx_data["data"],
                        "value": int(tx_data["value"]),
                        "gas": tx_data["gas"],
                        "gasPrice": self.web3.eth.gas_price,
                        "nonce": self.web3.eth.get_transaction_count(account.address),
                        "chainId": chain_id
                    }

                    signed_tx = account.sign_transaction(tx)
                    tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
                    receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

                    if receipt["status"] == 1:
                        logger.info(f"Swap successful via Odos: {tx_hash.hex()}")
                        return f"https://explorer.sonic.ooo/tx/{tx_hash.hex()}"
                    else:
                        raise Exception(f"Swap transaction failed: {tx_hash.hex()}")

                except Exception as e:
                    logger.error(f"Odos swap failed: {str(e)}")
                    if router == "odos":  # Only raise if Odos was specifically requested
                        raise

            # Try Magpie if selected or in auto mode (fourth priority router)
            if router in ["magpie", "auto"] and self.magpie:
                logger.info("Attempting swap via Magpie router (fourth priority router)")
                try:
                    # Get Magpie quote
                    magpie_quote = await self.magpie.get_quote(chain_id, {
                        "inputTokens": [{"tokenAddress": token_in, "amount": str(Web3.to_wei(amount, 'ether'))}],
                        "outputTokens": [{"tokenAddress": token_out, "proportion": 1}],
                        "userAddr": user_address
                    })

                    if magpie_quote:
                        # Handle approval for Magpie
                        await self._ensure_approval(token_in, self.magpie.MAGPIE_ROUTER, int(Web3.to_wei(amount, 'ether')), account)

                        # Assemble and execute Magpie swap
                        magpie_swap = await self.magpie.assemble_swap(chain_id, {
                            "userAddr": user_address,
                            "quoteId": magpie_quote.get("quoteId"),
                            "slippageTolerance": int(slippage * 100),
                            "quote": magpie_quote
                        })

                        if magpie_swap:
                            logger.info(f"Swap successful via Magpie: {magpie_swap}")
                            return magpie_swap

                except Exception as e:
                    logger.error(f"Magpie swap failed: {str(e)}")
                    if router == "magpie":  # Only raise if Magpie was specifically requested
                        raise

            logger.error("All swap attempts failed")
            return None

        except Exception as e:
            logger.error(f"Failed to execute swap: {str(e)}", exc_info=True)
            raise SonicConnectionError(f"Swap failed: {str(e)}")

    async def get_balance(self, address: Optional[str] = None, token_address: Optional[str] = None) -> float:
        """Get native or token balance with proper error handling"""
        try:
            if not address:
                address = self.connection.get_account().address

            address = await self._validate_address(address)

            if token_address:
                token_contract, decimals = await self._get_token_contract(token_address)
                balance = token_contract.functions.balanceOf(address).call()
                return balance / (10 ** decimals)
            else:
                balance = self.web3.eth.get_balance(address)
                return self.web3.from_wei(balance, 'ether')

        except Exception as e:
            logger.error(f"Failed to get balance: {str(e)}")
            raise SonicConnectionError(f"Balance check failed: {str(e)}")

# Action registration remains unchanged