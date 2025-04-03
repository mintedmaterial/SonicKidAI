```python
import logging
import asyncio
from typing import Optional, Dict, Any
from web3 import Web3
from web3.middleware import geth_poa_middleware

from ..constants.chain_config import ChainConfig
from ..constants.contract_abis import TRANSFER_ABI

logger = logging.getLogger(__name__)

class TransferService:
    """Handler for cross-chain transfer operations"""
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

    async def transfer_tokens(
        self,
        from_chain: str,
        to_chain: str,
        token_address: str,
        amount: str,
        recipient: str,
        private_key: str
    ) -> Optional[str]:
        """Execute cross-chain token transfer"""
        try:
            # Validate chains
            if not ChainConfig.validate_chain_id(from_chain):
                raise ValueError(f"Invalid source chain ID: {from_chain}")
            if not ChainConfig.validate_chain_id(to_chain):
                raise ValueError(f"Invalid destination chain ID: {to_chain}")

            # Initialize Web3 for source chain
            if from_chain not in self.web3_instances:
                if not await self.initialize_chain(from_chain):
                    raise ConnectionError(f"Failed to initialize source chain {from_chain}")

            web3 = self.web3_instances[from_chain]
            account = web3.eth.account.from_key(private_key)
            account_address = Web3.to_checksum_address(account.address)

            # Build transfer transaction
            contract = web3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=TRANSFER_ABI
            )

            nonce = await asyncio.to_thread(
                web3.eth.get_transaction_count,
                account_address
            )

            # Get gas price and estimate gas
            gas_price = await asyncio.to_thread(web3.eth.gas_price)
            
            func = contract.functions.transferToChain(
                to_chain,
                Web3.to_checksum_address(recipient),
                Web3.to_wei(amount, 'ether')
            )

            gas_estimate = await asyncio.to_thread(
                func.estimate_gas,
                {'from': account_address}
            )

            txn = func.build_transaction({
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
                raise Exception("Transaction failed")

            logger.info(f"Transfer successful: {web3.to_hex(txn_hash)}")
            return web3.to_hex(txn_hash)

        except Exception as e:
            logger.error(f"Transfer failed: {str(e)}")
            raise

    async def verify_transfer(self, chain_id: str, tx_hash: str) -> bool:
        """Verify transfer transaction status"""
        try:
            if chain_id not in self.web3_instances:
                if not await self.initialize_chain(chain_id):
                    raise ConnectionError(f"Failed to initialize chain {chain_id}")

            web3 = self.web3_instances[chain_id]
            tx_receipt = await asyncio.to_thread(
                web3.eth.get_transaction_receipt,
                tx_hash
            )

            if not tx_receipt:
                logger.warning(f"No receipt found for transaction {tx_hash}")
                return False

            return tx_receipt['status'] == 1

        except Exception as e:
            logger.error(f"Failed to verify transfer: {str(e)}")
            return False

    async def close(self):
        """Close all Web3 connections"""
        self.web3_instances.clear()
```
