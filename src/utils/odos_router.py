"""Odos Smart Order Router integration module"""
import logging
import requests
import time
from typing import Dict, Any, Optional, List, Union
from eth_account.messages import encode_structured_data
from web3 import Web3

logger = logging.getLogger(__name__)

ODOS_API_BASE = 'https://api.odos.xyz'
PERMIT2_ADDRESS = '0x000000000022D473030F116dDEE9F6B43aC78BA3'  # Permit2 contract 

class OdosRouter:
    """Odos aggregator router implementation"""

    # MetaAggregationRouterV2 contract address
    ODOS_ROUTER = '0xB9CBD870916e9Ffc52076Caa714f85a022B7f330'  # Sonic chain router

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'ZerePy/1.0'
        })

    async def get_quote(self, chain_id: int, quote_payload: Dict[str, Any]) -> Optional[Dict]:
        """Get quote for token swap using Odos V2 API"""
        try:
            logger.info(f"Getting quote for chain {chain_id}")

            # Extract input/output token data
            input_token = quote_payload['inputTokens'][0]
            output_token = quote_payload['outputTokens'][0]

            # Create V2 compatible payload for limit order
            v2_payload = {
                "chainId": chain_id,
                "inputTokens": [{
                    "tokenAddress": input_token['tokenAddress'].lower(),
                    "amount": str(input_token['amount'])
                }],
                "outputTokens": [{
                    "tokenAddress": output_token['tokenAddress'].lower(),
                    "proportion": 1
                }],
                "userAddr": quote_payload['userAddr'],
                "slippageLimitPercent": quote_payload.get('slippageLimitPercent', 1.0),
                "disableRFQs": True,
                "compact": True
            }

            logger.debug(f"Quote request data: {v2_payload}")
            response = self.session.post(f"{ODOS_API_BASE}/sor/quote/v2", json=v2_payload)
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response data: {response.text}")

            if response.status_code == 200:
                quote_data = response.json()
                logger.debug(f"Quote response: {quote_data}")

                # Add metadata
                quote_data['provider'] = 'odos'
                quote_data['router'] = self.ODOS_ROUTER
                quote_data['chainId'] = chain_id

                logger.info(f"Odos quote received: {quote_data.get('pathId')} for block {quote_data.get('blockNumber')}")
                return quote_data

            logger.error(f"Failed to get quote: {response.status_code} - {response.text}")
            return None

        except Exception as e:
            logger.error(f"Error getting quote: {str(e)}")
            return None

    def generate_permit(self, token_address: str, spender: str, amount: int, deadline: int, 
                       private_key: str, chain_id: int) -> Optional[Dict[str, Any]]:
        """Generate Permit2 signature for token approval"""
        try:
            # Convert amount to uint160
            amount_uint160 = int(amount)  # Should already be valid uint160
            if amount_uint160 < 0:
                raise ValueError("Amount cannot be negative")

            logger.debug(f"Using amount for permit: {amount_uint160}")

            # Create PermitDetails structure
            permit_details = {
                "token": Web3.to_checksum_address(token_address),
                "amount": amount_uint160,
                "expiration": deadline,
                "nonce": 0  # Start with nonce 0
            }

            # Create EIP-712 typed data structure for Permit2
            typed_data = {
                "types": {
                    "PermitSingle": [
                        {"name": "details", "type": "PermitDetails"},
                        {"name": "spender", "type": "address"},
                        {"name": "sigDeadline", "type": "uint256"}
                    ],
                    "PermitDetails": [
                        {"name": "token", "type": "address"},
                        {"name": "amount", "type": "uint160"},
                        {"name": "expiration", "type": "uint48"},
                        {"name": "nonce", "type": "uint48"}
                    ],
                    "EIP712Domain": [
                        {"name": "name", "type": "string"},
                        {"name": "chainId", "type": "uint256"},
                        {"name": "verifyingContract", "type": "address"}
                    ]
                },
                "domain": {
                    "name": "Permit2",
                    "chainId": chain_id,
                    "verifyingContract": PERMIT2_ADDRESS
                },
                "primaryType": "PermitSingle",
                "message": {
                    "details": permit_details,
                    "spender": Web3.to_checksum_address(spender),
                    "sigDeadline": deadline
                }
            }

            logger.debug(f"Permit data: {typed_data}")

            # Create structured message and sign
            structured_msg = encode_structured_data(typed_data)
            logger.debug(f"Structured message: {structured_msg}")

            w3 = Web3()
            account = w3.eth.account.from_key(private_key)
            signed = account.sign_message(structured_msg)
            logger.debug(f"Generated signature: {signed.signature.hex()}")

            # Format permit data for Odos assembly
            return {
                "details": permit_details,
                "spender": Web3.to_checksum_address(spender),
                "signature": signed.signature.hex(),
                "sigDeadline": deadline
            }

        except Exception as e:
            logger.error(f"Error generating permit: {str(e)}")
            return None

    async def assemble_limit_order(self, chain_id: int, assembly_payload: Dict[str, Any]) -> Optional[Dict]:
        """Assemble limit order transaction using Odos V2 API"""
        try:
            logger.info(f"Assembling limit order for chain {chain_id}")
            url = f"{ODOS_API_BASE}/sor/assemble"

            # Format the permit data for assembly
            permit_data = assembly_payload.get('permitData')
            if permit_data:
                logger.debug(f"Using permit data: {permit_data}")

            # Create assembly payload with permit data
            v2_assembly = {
                "userAddr": assembly_payload['userAddr'],
                "pathId": assembly_payload['pathId'],
                "deadline": assembly_payload.get('deadline', int(time.time() + 1200)),
                "simulate": True,  # Request simulation
                "permitSingle": permit_data  # Use permitSingle key
            }

            logger.debug(f"Assembly request data: {v2_assembly}")
            response = self.session.post(url, json=v2_assembly)
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response data: {response.text}")

            if response.status_code == 200:
                tx_data = response.json()
                logger.debug(f"Assembly response: {tx_data}")

                # Check simulation results
                simulation = tx_data.get('simulation', {})
                if not simulation.get('isSuccess'):
                    logger.error(f"Transaction simulation failed: {simulation.get('simulationError')}")
                    if simulation.get('simulationError'):
                        logger.error(f"Error type: {simulation['simulationError'].get('type')}")
                        logger.error(f"Error message: {simulation['simulationError'].get('errorMessage')}")
                    return None

                # Format response
                formatted_tx = {
                    "transaction": {
                        "data": tx_data.get('transaction', {}).get('data', '0x'),
                        "to": self.ODOS_ROUTER,
                        "value": tx_data.get('transaction', {}).get('value', '0'),
                        "gas": simulation.get('gasEstimate', tx_data.get('gasEstimate', 300000))
                    },
                    "router_address": self.ODOS_ROUTER,
                    "chain_id": chain_id,
                    "quote": assembly_payload.get('quote', {}),
                    "provider": "odos"
                }

                return formatted_tx

            logger.error(f"Failed to assemble tx: {response.status_code} - {response.text}")
            return None

        except Exception as e:
            logger.error(f"Error assembling transaction: {str(e)}")
            return None

    async def assemble_transaction(self, chain_id: int, assembly_payload: Dict[str, Any]) -> Optional[Dict]:
        """Assemble standard transaction using Odos V2 API"""
        try:
            logger.info(f"Assembling transaction for chain {chain_id}")
            url = f"{ODOS_API_BASE}/sor/assemble"

            # Create assembly payload with standard fields
            v2_assembly = {
                "userAddr": assembly_payload['userAddr'],
                "pathId": assembly_payload['pathId'],
                "deadline": assembly_payload.get('deadline', int(time.time() + 1200)),
                "simulate": True  # Request simulation
            }

            logger.debug(f"Assembly request data: {v2_assembly}")
            response = self.session.post(url, json=v2_assembly)
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response data: {response.text}")

            if response.status_code == 200:
                tx_data = response.json()
                logger.debug(f"Assembly response: {tx_data}")

                # Check simulation results
                simulation = tx_data.get('simulation', {})
                if not simulation.get('isSuccess'):
                    logger.error(f"Transaction simulation failed: {simulation.get('simulationError')}")
                    if simulation.get('simulationError'):
                        logger.error(f"Error type: {simulation['simulationError'].get('type')}")
                        logger.error(f"Error message: {simulation['simulationError'].get('errorMessage')}")
                    return None

                # Format response
                formatted_tx = {
                    "transaction": {
                        "data": tx_data.get('transaction', {}).get('data', '0x'),
                        "to": self.ODOS_ROUTER,
                        "value": tx_data.get('transaction', {}).get('value', '0'),
                        "gas": simulation.get('gasEstimate', tx_data.get('gasEstimate', 300000))
                    },
                    "router_address": self.ODOS_ROUTER,
                    "chain_id": chain_id,
                    "quote": assembly_payload.get('quote', {}),
                    "provider": "odos"
                }

                return formatted_tx

            logger.error(f"Failed to assemble tx: {response.status_code} - {response.text}")
            return None

        except Exception as e:
            logger.error(f"Error assembling transaction: {str(e)}")
            return None

    def format_swap_stats(self, tx_data: Dict) -> str:
        """Format swap transaction data into readable string"""
        try:
            # Extract core data
            quote = tx_data.get('quote', {})

            try:
                # Convert wei amounts to base units
                amount_in = float(quote.get('inAmounts', ['0'])[0]) / 1e18
                amount_out = float(quote.get('outAmounts', ['0'])[0]) / 1e18
                amount_in_usd = float(quote.get('inValues', [0])[0])
                amount_out_usd = float(quote.get('outValues', [0])[0])

                # Get additional values with defaults
                net_out_value = float(quote.get('netOutValue', 0))
                gas_estimate = float(quote.get('gasEstimate', 0))
                gas_price = float(quote.get('gweiPerGas', 0))
                price_impact = float(quote.get('priceImpact', 0))

                # Calculate gas cost
                gas_cost_eth = (gas_estimate * gas_price * 1e-9) if gas_price else 0
                gas_cost_usd = float(quote.get('gasEstimateValue', 0))

            except (IndexError, ValueError, TypeError) as e:
                logger.warning(f"Error parsing values: {str(e)}")
                return "Error parsing swap details"

            return (
                f"💱 Odos Router Swap Details:\n"
                f"Input Amount: {amount_in:.6f} (${amount_in_usd:.2f})\n"
                f"Output Amount: {amount_out:.6f} (${amount_out_usd:.2f})\n"
                f"Net Output Value: {net_out_value:.2f} USD\n"
                f"Price Impact: {price_impact:.4f}%\n"
                f"Gas Cost: {gas_cost_eth:.6f} ETH (${gas_cost_usd:.2f})\n"
                f"Gas Estimate: {int(gas_estimate)} units @ {int(gas_price)} gwei\n"
                f"Router: {self.ODOS_ROUTER}"
            )

        except Exception as e:
            logger.error(f"Error formatting swap stats: {str(e)}")
            return "Error formatting swap details"

    def is_chain_supported(self, chain_id: int) -> bool:
        """Check if chain is supported by Odos"""
        # Currently only supporting Sonic chain
        return chain_id == 146