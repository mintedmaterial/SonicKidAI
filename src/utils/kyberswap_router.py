"""KyberSwap Smart Order Router integration module"""
import logging
import requests
import time
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger(__name__)

KYBER_API_BASE = 'https://aggregator-api.kyberswap.com'

class KyberSwapRouter:
    """KyberSwap aggregator router implementation"""

    # MetaAggregationRouterV2 contract address
    KYBER_ROUTER = '0x6131B5fae19EA4f9D964eAc0408E4408b66337b5'

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'ZerePy/1.0',
            'x-client-id': 'ZerePyBot'
        })

    def _get_chain_path(self, chain_id: int) -> str:
        """Get API path for chain ID"""
        chain_map = {
            1: 'ethereum',
            56: 'bsc',
            137: 'polygon', 
            42161: 'arbitrum',
            10: 'optimism',
            43114: 'avalanche',
            146: 'sonic',
            324: 'zksync',
            8453: 'base',
            59144: 'linea',
            1101: 'polygon-zkevm'
        }
        chain_name = chain_map.get(chain_id)
        if not chain_name:
            raise ValueError(f"Unsupported chain ID: {chain_id}")
        return chain_name

    async def get_quote(self, 
                       chain_id: int,
                       token_in: str,
                       token_out: str,
                       amount_in: str,
                       slippage_bips: int = 50,  # 0.5%
                       save_gas: bool = False) -> Optional[Dict]:
        """Get quote for token swap using KyberSwap aggregator

        Args:
            chain_id: Chain ID
            token_in: Input token address 
            token_out: Output token address
            amount_in: Input amount in wei
            slippage_bips: Slippage tolerance in basis points (1 = 0.01%)
            save_gas: Prioritize gas savings over output amount

        Returns:
            Quote data or None on error
        """
        try:
            chain_path = self._get_chain_path(chain_id)
            logger.info(f"Getting KyberSwap quote on {chain_path}")

            # Handle native token address
            if token_in == '0x0000000000000000000000000000000000000000':
                token_in = '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'
                logger.debug(f"Converted native token address to: {token_in}")

            # Prepare request params
            params = {
                'tokenIn': token_in.lower(),
                'tokenOut': token_out.lower(),
                'amountIn': amount_in,
                'gasInclude': True,
                'slippageTolerance': slippage_bips,
                'saveGas': save_gas,
                'clientData': '{"source":"ZerePyBot"}'
            }

            logger.debug(f"Quote request params: {params}")
            api_url = f"{KYBER_API_BASE}/{chain_path}/api/v1/routes"
            logger.debug(f"Request URL: {api_url}")

            response = self.session.get(api_url, params=params)
            logger.debug(f"Response status: {response.status_code}")

            if response.status_code == 400:
                error_data = response.json()
                error_code = error_data.get('code')
                error_msg = error_data.get('message')
                logger.error(f"KyberSwap API error {error_code}: {error_msg}")

                if error_code == 4011:  # Token not found
                    logger.error(f"Token not found - Please verify token addresses are supported on {chain_path}")
                return None

            if response.status_code != 200:
                logger.error(f"KyberSwap API error {response.status_code}: {response.text}")
                return None

            data = response.json()
            if data.get("code") != 0:
                logger.error(f"KyberSwap API error: {data.get('message')}")
                return None

            quote_data = data.get('data')
            logger.debug(f"Route data: {quote_data}")

            # Add metadata
            quote_data['provider'] = 'kyberswap'
            quote_data['router'] = self.KYBER_ROUTER
            quote_data['chainId'] = chain_id

            return quote_data

        except Exception as e:
            logger.error(f"Error getting quote: {str(e)}")
            return None

    async def build_swap_data(self, 
                            chain_id: int,
                            quote_data: Dict[str, Any],
                            sender: str,
                            recipient: Optional[str] = None,
                            slippage_bips: int = 50) -> Optional[Dict]:
        """Build transaction data for swap execution

        Args:
            chain_id: Chain ID
            quote_data: Quote response data
            sender: Sender wallet address
            recipient: Optional recipient address (defaults to sender)
            slippage_bips: Slippage tolerance in basis points

        Returns:
            Transaction data or None on error
        """
        try:
            chain_path = self._get_chain_path(chain_id)
            logger.info(f"Building swap transaction on {chain_path}")

            # Calculate deadline 20 minutes from now
            deadline = int(time.time() + 1200)

            # Create assembly payload
            assembly_payload = {
                "routeSummary": quote_data.get('routeSummary'),
                "sender": sender,
                "recipient": recipient or sender,
                "slippageTolerance": slippage_bips,
                "deadline": deadline,
                "source": "ZerePyBot",
                "enableGasEstimation": True
            }

            logger.debug(f"Assembly payload: {assembly_payload}")
            api_url = f"{KYBER_API_BASE}/{chain_path}/api/v1/route/build"

            response = self.session.post(api_url, json=assembly_payload)
            logger.debug(f"Response status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"KyberSwap assembly error {response.status_code}: {response.text}")
                return None

            data = response.json()
            if data.get("code") != 0:
                logger.error(f"KyberSwap API error: {data.get('message')}")
                return None

            tx_data = data.get('data')
            logger.debug(f"Transaction data: {tx_data}")

            # Format response
            formatted_tx = {
                "transaction": {
                    "data": tx_data.get('data', '0x'),
                    "to": self.KYBER_ROUTER,
                    "value": tx_data.get('value', '0'),
                    "gasPrice": tx_data.get('gasPrice', '0'),
                    "gas": quote_data.get('routeSummary', {}).get('gas', '0')
                },
                "router_address": self.KYBER_ROUTER,
                "chain_id": chain_id,
                "quote": quote_data,
                "provider": "kyberswap"
            }

            return formatted_tx

        except Exception as e:
            logger.error(f"Error building swap data: {str(e)}")
            return None

    def format_swap_stats(self, tx_data: Dict) -> str:
        """Format swap transaction data into readable string"""
        try:
            # Extract core data
            quote = tx_data.get('quote', {})
            route_summary = quote.get('routeSummary', {})

            # Parse amounts
            amount_in = float(route_summary.get('amountIn', 0)) / 1e18  # Convert from wei
            amount_out = float(route_summary.get('amountOut', 0)) / 1e18
            amount_in_usd = float(route_summary.get('amountInUsd', 0))
            amount_out_usd = float(route_summary.get('amountOutUsd', 0))

            # Get gas estimates
            gas_estimate = int(route_summary.get('gas', 0))
            gas_price_gwei = int(tx_data.get('transaction', {}).get('gasPrice', 0)) / 1e9
            gas_cost_usd = float(route_summary.get('gasUsd', 0))
            gas_cost_eth = (gas_estimate * gas_price_gwei * 1e-9)

            # Calculate impact
            price_impact = float(route_summary.get('priceImpact', 0))

            return (
                f"💱 KyberSwap Swap Details:\n"
                f"Input Amount: {amount_in:.6f} (${amount_in_usd:.2f})\n"
                f"Output Amount: {amount_out:.6f} (${amount_out_usd:.2f})\n"
                f"Price Impact: {price_impact:.4f}%\n"
                f"Gas Cost: {gas_cost_eth:.6f} ETH (${gas_cost_usd:.2f})\n"
                f"Gas Estimate: {gas_estimate} units @ {int(gas_price_gwei)} gwei\n"
                f"Router: {self.KYBER_ROUTER}"
            )

        except Exception as e:
            logger.error(f"Error formatting swap stats: {str(e)}")
            return "Error formatting swap details"

    def is_chain_supported(self, chain_id: int) -> bool:
        """Check if chain is supported by KyberSwap"""
        try:
            self._get_chain_path(chain_id)
            return True
        except ValueError:
            return False