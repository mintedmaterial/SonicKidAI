from typing import Dict, List, Any, Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class TradeProcessor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_confidence = 0.5
        self.max_confidence = 0.9
        self.max_slippage = Decimal('2.0')

    async def analyze_signals(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze trading signals and identify valid opportunities"""
        opportunities = []

        for signal in signals:
            if self.validate_signal(signal):
                processed = await self.process_signal(signal)
                if processed:
                    opportunities.append(processed)

        return opportunities

    def validate_signal(self, signal: Dict[str, Any]) -> bool:
        """Validate trading signal meets minimum requirements"""
        try:
            # Check confidence threshold
            if signal.get('confidence', 0) < self.min_confidence:
                return False

            # Validate slippage
            if Decimal(str(signal.get('slippage', '0'))) > self.max_slippage:
                return False

            # Check required fields
            required = ['action', 'source_chain', 'token_in', 'amount']
            if not all(signal.get(field) for field in required):
                return False

            return True

        except Exception as e:
            logger.error(f"Signal validation error: {str(e)}")
            return False

    async def process_signal(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process raw signal into executable trade"""
        try:
            formatted_signal = {
                'source_chain': signal['source_chain'],
                'target_chain': signal.get('target_chain', signal['source_chain']),
                'token_in': signal['token_in'],
                'token_out': signal.get('token_out', ''),
                'amount': str(signal['amount']),
                'slippage': str(signal.get('slippage', '0.5')),
                'action': signal['action'],
                'type': signal.get('type', 'standard')
            }

            if self.validate_trade(formatted_signal):
                return formatted_signal
            return None

        except Exception as e:
            logger.error(f"Signal processing error: {str(e)}")
            return None

    def validate_trade(self, trade: Dict[str, Any]) -> bool:
        """Validate trade parameters before execution"""
        try:
            # Validate chains
            if trade['source_chain'] not in self.config['networks']:
                return False

            if trade['target_chain'] not in self.config['networks']:
                return False

            # Validate amounts
            try:
                amount = Decimal(str(trade['amount']))
                # Change threshold to allow trades of 1.0 or greater
                if amount < Decimal("0.0001") or amount > Decimal("1000000000000000000"):
                    return False
            except (ValueError, TypeError):
                return False

            return True

        except Exception as e:
            logger.error(f"Trade validation error: {str(e)}")
            return False

    def format_trade_tweet(self, result: Dict[str, Any]) -> str:
        """Format trade result for Twitter update"""
        try:
            if result['type'] == 'single_chain':
                return (
                    f"🤖 Trade executed on {result['chain']}\n"
                    f"📥 {result['amount_in']} {result['token_in']}\n"
                    f"📤 {result['amount_out']} {result['token_out']}\n"
                    f"🔗 Transaction: {result['tx_hash']}"
                )
            else:
                return (
                    f"🤖 Cross-chain trade completed\n"
                    f"📤 {result['amount_in']} {result['token_in']} on {result['source_chain']}\n"
                    f"📥 {result['amount_out']} {result['token_out']} on {result['target_chain']}\n"
                    f"🔗 Source TX: {result['source_tx']}\n"
                    f"🔗 Target TX: {result['target_tx']}"
                )
        except Exception as e:
            logger.error(f"Tweet formatting error: {str(e)}")
            return "Trade completed successfully"