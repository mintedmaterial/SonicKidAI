```python
import logging
import asyncio
from typing import Optional, Dict, Any
from web3 import Web3
from web3.middleware import geth_poa_middleware
import json

from ..constants.chain_config import ChainConfig
from ..constants.contract_abis import ROUTER_ABI, SWAP_ABI

logger = logging.getLogger(__name__)

class SwapService:
    """Handler for cross-chain token swaps"""
    def __init__(self):
        self.web3_instances: Dict[str, Web3] = {}
        self.timeout = 30

    async def initialize_chain(self, chain_id: str) -> bool:
        """Initialize Web3 connection for a specific chain"""
        try:
            rpc_url = ChainConfig.get_rpc_url(chain_id)
            if not rpc_url:
                raise ValueError(f"No RPC URL configured for chain {chain_id}")

            web3 = Web3(Web3.HTTPProvider(rpc_url))
            web3.middleware_onion.inject(geth_poa_middleware, layer=0)

            if not web3.is_connected():
                raise ConnectionError(f"Failed to connect to RPC: {rpc_url}")

            self.web3_instances[chain_id] = web3
            logger.info(f"Successfully initialized Web3 for chain {chain_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize chain {chain_id}: {str(e)}")
            return False

    async def get_swap_quote(
        self,
        chain_id: str,
        token_in: str,
        token_out: str,
        amount_in: str
    ) -> Optional[Dict[str, Any]]:
        """Get quote for token swap"""
        try:
            if not ChainConfig.validate_chain_id(chain_id):
                raise ValueError(f"Invalid chain ID: {chain_id}")

            if chain_id not in self.web3_instances:
                if not await self.initialize_chain(chain_id):
                    raise ConnectionError(f"Failed to initialize chain {chain_id}")

            web3 = self.web3_instances[chain_id]
            router_contract = web3.eth.contract(
                address=Web3.to_checksum_address(ChainConfig.get_router_address(chain_id)),
                abi=ROUTER_ABI
            )

            quote = await asyncio.to_thread(
                router_contract.functions.getQuote(
                    Web3.to_checksum_address(token_in),
                    Web3.to_checksum_address(token_out),
                    Web3.to_wei(amount_in, 'ether')
                ).call
            )

            return {
                'amountOut': Web3.from_wei(quote[0], 'ether'),
                'path': quote[1],
                'priceImpact': quote[2] / 10000  # Convert basis points to percentage
            }

        except Exception as e:
            logger.error(f"Failed to get swap quote: {str(e)}")
            return None

    async def execute_swap(
        self,
        chain_id: str,
        token_in: str,
        token_out: str,
        amount_in: str,
        min_amount_out: str,
        recipient: str,
        private_key: str
    ) -> Optional[str]:
        """Execute token swap"""
        try:
            if not ChainConfig.validate_chain_id(chain_id):
                raise ValueError(f"Invalid chain ID: {chain_id}")

            if chain_id not in self.web3_instances:
                if not await self.initialize_chain(chain_id):
                    raise ConnectionError(f"Failed to initialize chain {chain_id}")

            web3 = self.web3_instances[chain_id]
            account = web3.eth.account.from_key(private_key)
            account_address = Web3.to_checksum_address(account.address)

            # Get router contract
            router_contract = web3.eth.contract(
                address=Web3.to_checksum_address(ChainConfig.get_router_address(chain_id)),
                abi=ROUTER_ABI
            )

            # Approve token spending if needed
            token_contract = web3.eth.contract(
                address=Web3.to_checksum_address(token_in),
                abi=SWAP_ABI
            )

            amount_in_wei = Web3.to_wei(amount_in, 'ether')
            min_amount_out_wei = Web3.to_wei(min_amount_out, 'ether')

            # Check allowance
            allowance = await asyncio.to_thread(
                token_contract.functions.allowance(
                    account_address,
                    ChainConfig.get_router_address(chain_id)
                ).call
            )

            if allowance < amount_in_wei:
                # Approve token spending
                approve_txn = await self._approve_token(
                    web3,
                    token_contract,
                    ChainConfig.get_router_address(chain_id),
                    amount_in_wei,
                    account_address,
                    private_key
                )
                if not approve_txn:
                    raise Exception("Token approval failed")

            # Build swap transaction
            deadline = web3.eth.get_block('latest')['timestamp'] + 1200  # 20 minutes

            nonce = await asyncio.to_thread(
                web3.eth.get_transaction_count,
                account_address
            )

            gas_price = await asyncio.to_thread(web3.eth.gas_price)

            swap_func = router_contract.functions.swapExactTokensForTokens(
                amount_in_wei,
                min_amount_out_wei,
                [Web3.to_checksum_address(token_in), Web3.to_checksum_address(token_out)],
                Web3.to_checksum_address(recipient),
                deadline
            )

            gas_estimate = await asyncio.to_thread(
                swap_func.estimate_gas,
                {'from': account_address}
            )

            txn = swap_func.build_transaction({
                'from': account_address,
                'nonce': nonce,
                'gas': gas_estimate,
                'gasPrice': gas_price
            })

            # Sign and send transaction
            signed_txn = web3.eth.account.sign_transaction(txn, private_key)
            txn_hash = await asyncio.to_thread(
                web3.eth.send_raw_transaction,
                signed_txn.rawTransaction
            )

            # Wait for receipt
            tx_receipt = await asyncio.to_thread(
                web3.eth.wait_for_transaction_receipt,
                txn_hash
            )

            if tx_receipt['status'] != 1:
                raise Exception("Swap transaction failed")

            logger.info(f"Swap successful: {web3.to_hex(txn_hash)}")
            return web3.to_hex(txn_hash)

        except Exception as e:
            logger.error(f"Swap failed: {str(e)}")
            raise

    async def _approve_token(
        self,
        web3: Web3,
        token_contract: Any,
        spender: str,
        amount: int,
        account_address: str,
        private_key: str
    ) -> bool:
        """Approve token spending"""
        try:
            nonce = await asyncio.to_thread(
                web3.eth.get_transaction_count,
                account_address
            )

            gas_price = await asyncio.to_thread(web3.eth.gas_price)

            approve_func = token_contract.functions.approve(
                Web3.to_checksum_address(spender),
                amount
            )

            gas_estimate = await asyncio.to_thread(
                approve_func.estimate_gas,
                {'from': account_address}
            )

            txn = approve_func.build_transaction({
                'from': account_address,
                'nonce': nonce,
                'gas': gas_estimate,
                'gasPrice': gas_price
            })

            signed_txn = web3.eth.account.sign_transaction(txn, private_key)
            txn_hash = await asyncio.to_thread(
                web3.eth.send_raw_transaction,
                signed_txn.rawTransaction
            )

            tx_receipt = await asyncio.to_thread(
                web3.eth.wait_for_transaction_receipt,
                txn_hash
            )

            return tx_receipt['status'] == 1

        except Exception as e:
            logger.error(f"Token approval failed: {str(e)}")
            return False

    async def close(self):
        """Close all Web3 connections"""
        self.web3_instances.clear()
```
